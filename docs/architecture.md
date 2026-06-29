# Architettura — note tecniche e decisioni

> Questo documento raccoglie le **decisioni tecniche significative** del
> progetto, con motivazione e alternative considerate. Non duplica la scheda
> di progetto ([PROJECT.md](../PROJECT.md)) né il riferimento API
> ([api.md](api.md)).

---

## ADR-001 — Persistenza: SQLite per metadata, filesystem per immagini

**Decisione**: per l'MVP usiamo SQLite (`data/closetai.db`) come unico DB
relazionale, e il filesystem locale (`data/items/`) per le immagini, con
filename UUID e path *relativo* salvato nel record.

**Motivazione**:

- Zero setup per i compagni di studio (nessun container Postgres).
- Volume dati per il single-user dell'MVP largamente sotto i limiti SQLite.
- Le immagini grezze non vanno in DB: dump più rapidi, sync facile con
  cloud-storage in futuro.

**Alternative scartate**:

- Postgres + S3 → over-engineering per Fase 1–4.
- Tutto in DB (immagini come BLOB) → DB enorme, backup lenti, niente streaming.

**Conseguenze**:

- In produzione la migrazione a Postgres + object store è puntuale: solo
  cambio di `CLOSETAI_DATABASE_URL` e wrapper storage. Niente lock-in.

---

## ADR-002 — Migrazioni: `create_all` in Fase 1, Alembic da Fase 3

**Decisione**: nell'MVP usiamo `Base.metadata.create_all()` nel lifespan
FastAPI; lo schema può cambiare velocemente con effort minimo. Aggiungiamo
una **migrazione manuale leggera** (ALTER TABLE idempotente) per le nuove
colonne dei record esistenti, evitando di costringere l'utente a cancellare
il DB ad ogni evoluzione di schema.

**Alternative**:

- Alembic da subito → utile, ma il churn di schema in Fase 1–2 lo rende
  costoso. Lo introduciamo quando lo schema è più stabile (Fase 3 / wear log).

---

## ADR-003 — Classificatore: Fashion-CLIP (HuggingFace `patrickjohncyh/fashion-clip`)

**Contesto**: la Fase 2 del PLAN richiede di sostituire il classificatore
mock con un modello pre-trained reale. Le opzioni considerate:

| Opzione                                       | Pro                                                              | Contro                                                              |
| --------------------------------------------- | ---------------------------------------------------------------- | ------------------------------------------------------------------- |
| **Fashion-CLIP** (`patrickjohncyh/fashion-clip`) | CLIP fine-tunato su 700K immagini fashion. Zero-shot su categorie italiane. Embedding 512d riusabili per recommender (Fase 4). | ~600 MB di pesi al primo run.                                       |
| CLIP standard (`openai/clip-vit-base-patch32`) | Più piccolo (~150 MB), interfaccia identica.                     | Meno preciso sui capi (training generalista).                       |
| Classifier diretto (es. ViT su Fashionpedia) | Più piccolo, output diretto (no prompt eng.).                    | Niente embedding. Categoria fissa. Si riaddestra per cambiare lista.|
| Servizio cloud (Replicate / HF Inference API)   | Niente pesi locali.                                              | Privacy: immagini lasciano la macchina. Costo. Latenza variabile.   |

**Decisione**: usiamo **Fashion-CLIP** come default, con il **mock** come
fallback e per i test. La selezione è guidata da `CLOSETAI_CLASSIFIER`:

- `mock` → classificatore di Fase 1, sempre disponibile (default nei test).
- `fashion-clip` → Fashion-CLIP server-side (default in produzione/dev).

**Motivazione**:

- *Zero-shot* — la lista delle categorie (`CATEGORIES` in
  `app/ml/classifier.py`) può cambiare senza riaddestrare nulla.
- *Embedding 512d* — lo stesso passaggio produce un vettore riusabile dal
  recommender e da analisi di similarità, evitando un secondo pass del
  modello in Fase 4.
- *Coerenza interfaccia* — l'API esposta dal classifier resta
  `classify(image) -> ClassificationResult`, indistinguibile per il chiamante.

---

## ADR-004 — Embedding storage: ChromaDB (persistente, locale)

**Contesto**: dobbiamo conservare gli embedding 512d generati da
Fashion-CLIP. Le opzioni:

| Opzione                              | Pro                                                  | Contro                                                       |
| ------------------------------------ | ---------------------------------------------------- | ------------------------------------------------------------ |
| BLOB nella tabella `items` (SQLite)  | Zero deps extra, transazionale.                      | Niente query "k-NN" native: linear scan in app.              |
| File `.npy` in `data/embeddings/`    | Ispezionabili, separati.                             | Sync DB↔FS, niente query.                                    |
| **ChromaDB** persistente in `data/chroma/` | API client semplice (`add`, `query`, `delete`). k-NN nativo. Locale, niente server. | Dep aggiuntiva (~50 MB). Schema separato dal DB principale: serve sync. |

**Decisione**: usiamo **ChromaDB in modalità persistente** per gli embedding.
La verità per i metadata resta in SQLite (tabella `items`); ChromaDB è una
"collection" gemella indicizzata per `item_id`. Le operazioni mutanti
(`POST /items`, `DELETE /items/{id}`, `POST /items/{id}/reclassify`) tengono
allineati i due store con best-effort: SQLite è la fonte di verità, Chroma
è un'indice ricostruibile da un task `reindex` (futuro) in caso di drift.

**Trade-off**:

- Pago oggi (Fase 2) un'infrastruttura che inizierò a sfruttare davvero in
  Fase 4 (recommender) — scelta deliberata di anticipo, su indicazione
  utente.
- Disaster recovery: se `data/chroma/` viene perso, basta richiamare
  `reclassify` su tutti gli item per ricostruire l'indice.

---

## ADR-005 — Inference: server-side per ora, on-device come estensione

**Decisione**: per l'MVP la classificazione gira **server-side**, sulla
stessa macchina del backend FastAPI, con PyTorch CPU.

**Motivazione**:

- I pesi di Fashion-CLIP (~600 MB) sono troppi per essere scaricati nel
  browser ogni volta.
- L'unico utente è in dev locale, quindi "server" = stessa macchina;
  niente trasferimento di immagini in rete.

**Estensione futura** (Fase 5–6):

- **Export ONNX** + runtime browser-side (Transformers.js / ORT-Web) →
  inference nel browser dell'utente, zero immagini sul server.
- **Specchio (RPi5)**: CoreML / TFLite tramite delegato hardware.

In entrambi i casi l'interfaccia `Classifier` resta invariata: cambia solo
l'implementazione del singleton sotto `app/ml/classifier.py`.

---

## ADR-006 — Colore dominante: quantize Pillow con filtro sfondo chiaro

**Decisione**: in Fase 2 sostituiamo la media globale con un'estimazione
basata su **`Image.quantize(N=5, method=MEDIANCUT)`**: riduciamo l'immagine
a 5 colori, scartiamo quello più vicino al bianco se la sua frequenza
relativa supera una soglia (assumendo che lo sfondo sia chiaro nelle foto
da app di catalogazione), e prendiamo il colore con frequenza massima fra
i rimanenti. Mappiamo poi sul nome più vicino della palette
`NAMED_COLORS`.

**Alternative**:

- `scikit-learn` KMeans su pixel → migliore qualitativamente, ma aggiunge
  ~10 MB di dep solo per questo. Da considerare in Fase 6 se gli errori di
  colore disturbano la UX.
- Background removal con `rembg` → costoso, fragile. Eccessivo per MVP.

---

## ADR-007 — Try-on virtuale (diffusion): backend pluggable, default disabled

**Contesto**: il PROJECT.md §4.2 elenca il *try-on virtuale* (es. IDM-VTON,
StreetTryOn) come ruolo di AI generativa. Si tratta di sintetizzare un
ritratto dell'utente che indossa virtualmente un capo del guardaroba,
usando un modello di diffusion image-to-image.

**Decisione**: **implementato con backend pluggable**, default `disabled`.
L'opt-in esplicito (`CLOSETAI_TRYON_BACKEND=diffusers`) scarica al primo
uso ~5 GB di pesi (default `stabilityai/stable-diffusion-2-inpainting`) e
genera in locale.

**Architettura**:

```
backend/app/services/tryon.py
├─ TryOnBackend (ABC)
│   ├─ DisabledBackend  ← default, risponde 503
│   └─ DiffusersLocalBackend  ← Stable Diffusion 2 inpainting via diffusers
│       └─ (futuro) HuggingFaceInferenceBackend, ReplicateBackend, …
```

Pipeline MVP (non IDM-VTON garment-aware):

1. Ricezione ritratto utente via `POST /items/{id}/try-on` multipart.
2. Resize/pad a 512×512 (tarato per SD2 inpainting).
3. Generazione automatica di una maschera "torso" (rettangolo centrale
   euristico, dal 30% al 75% dell'altezza, 15%-85% larghezza).
4. Stable Diffusion **inpainting** con prompt `"a photorealistic portrait
   of a person wearing a {color} {category}…"`.
5. Output salvato in `data/tryon/{uuid}.png` (TTL gestito esternamente).

**Motivazione del compromesso**:

- L'inferenza richiede 30s-3min su CPU, pochi secondi su GPU CUDA. Il
  default `disabled` evita download involontari.
- La maschera del torso *automatica* dà un risultato approssimativo ma è
  sufficiente per la demo. Per qualità garment-aware servirebbe IDM-VTON
  o OutfitAnyone (10+ GB) con segmentazione pose-aware.
- Privacy: i ritratti dell'utente **non** vengono salvati su disco; solo
  l'output generato (che è una sintesi, non il volto originale) viene
  scritto in `data/tryon/`.

**Path di sblocco per IDM-VTON**:

1. Implementare `IdmVtonBackend(TryOnBackend)` che usa il modello vero
   con segmentazione automatica.
2. Cambiare default a `CLOSETAI_TRYON_BACKEND=idm-vton`.
3. Nessuna modifica di interfaccia per il chiamante: `run_tryon()` resta
   identico, l'endpoint resta identico.

---

## ADR-008 — LLM gateway via litellm (cloud + locale pluggable)

**Contesto**: il PROJECT.md §4.2 elenca tre ruoli di AI generativa testuale:

- **Tutorial di riparazione** dinamici.
- **Descrizione narrativa** dei capi.
- **Coach sostenibilità** sulla dashboard.

Avremmo potuto integrare direttamente l'SDK Anthropic, ma questo avrebbe
fatto del "vendor lock-in" su un singolo provider. L'utente può preferire
modelli locali per ragioni di privacy/costo (Ollama su laptop, vLLM su
server interno, llama.cpp).

**Decisione**: usiamo **litellm** come abstraction layer unificato.
Sono compatibili out-of-the-box:

| Modello configurato                  | Provider              | Credenziali           |
| ------------------------------------ | --------------------- | --------------------- |
| `claude-haiku-4-5` (default)         | Anthropic API         | `ANTHROPIC_API_KEY`   |
| `claude-sonnet-4-6`                  | Anthropic API         | `ANTHROPIC_API_KEY`   |
| `openai/gpt-4o-mini`                 | OpenAI API            | `OPENAI_API_KEY`      |
| `ollama/llama3.2:3b`                 | Ollama locale         | nessuna (daemon up)   |
| `huggingface/Qwen/Qwen2.5-7B-Instruct` | HF Inference        | `HF_TOKEN`            |

La scelta è guidata da `CLOSETAI_LLM_MODEL`. Cambiare provider richiede
un solo env var, nessun cambio di codice.

**Servizi che lo usano**:

- `app/services/repair_tutorials.py::enrich_with_llm()` —
  `GET /api/v1/repair-tutorials/enrich?defect=…` produce tutorial JSON
  strutturati. Fallback alla KB hardcoded se l'LLM non risponde.
- `app/services/descriptions.py::generate_item_description()` —
  `POST /api/v1/items/{id}/describe`, salva su `Item.description`.
- `app/services/coach.py::generate_coach_message()` —
  `GET /api/v1/stats/coach`, restituisce consiglio basato su
  `WardrobeStats + ImpactStats + ghosts top 3`.

**Caching**: tabella `llm_cache` con TTL (default 24h, configurabile via
`CLOSETAI_LLM_CACHE_TTL_HOURS`). Lo stesso prompt non viene rigenerato.

**Graceful fallback**: se la chiamata fallisce (no credenziali, network
down, modello locale non servito), `llm.generate()` ritorna `None`. I
chiamanti decidono il fallback caso per caso (canned message, KB
hardcoded, 503 al client).

---

## Layout dei moduli ML

---

## ADR-009 — Diagnosi stato di conservazione: rete addestrata da noi

**Contesto**: la Fase 5 diagnosticava lo stato del capo (nuovo/buono/
usurato/danneggiato) con un'**euristica** su `wear_count` + età. Non guarda
la foto: due capi comprati lo stesso giorno e indossati uguale ricevono lo
stesso giudizio, anche se uno è strappato e l'altro intatto. Il requisito
(corso + utente) è una **rete neurale addestrata da noi** che predica lo
stato **dalla foto**.

**Decisione**: **Approccio A — testa MLP su embedding Fashion-CLIP**.

```
foto ──▶ Fashion-CLIP (frozen) ──▶ embedding 512d ──▶ MLP ──▶ stato (4 classi)
        [pre-addestrato]                              [addestrato DA NOI]
```

La parte addestrata da noi è un MLP `512 → 256 → 128 → 4` (~170k parametri,
dropout 0.3). Fashion-CLIP fa da feature extractor congelato.

**Perché A e non subito un VLM+LoRA**:

- Gira su **CPU** in millisecondi (il VLM richiede GPU anche in inferenza).
- Riusa l'infrastruttura Fashion-CLIP già presente (un solo modello pesante
  caricato in RAM, non due).
- Dataset più semplice da etichettare: serve solo (foto, stato), non testo.
- Stabilisce un **baseline** misurabile prima di investire nel VLM.

**Dataset**: non esiste un dataset pubblico per lo stato di usura. Lo
generiamo con **degradazione sintetica controllata**
(`scripts/build_condition_dataset.py`, vedi
[dataset-datasheet.md](dataset-datasheet.md)).

**Risultati baseline** (dati sintetici, 600 immagini, split 70/15/15):

| Metrica            | Valore   |
| ------------------ | -------- |
| Test accuracy      | ~0.94    |
| Confusione tipica  | usurato ↔ danneggiato (stati adiacenti) |

> ⚠️ L'accuracy alta riflette la **separabilità dei dati sintetici**, non la
> performance su foto reali. Il vero test sarà su un dataset reale; ci si
> aspetta un calo (domain gap). Onestà metodologica documentata nella
> datasheet.

**Integrazione**: `services/condition.py::diagnose()` usa il modello se i
pesi `ml/weights/condition_head.pt` esistono **e** il capo ha un'immagine
leggibile; altrimenti ricade sull'euristica. Il campo `source`
(`vision-model` | `heuristic`) e `confidence` sono esposti in
`GET/POST /diagnose`.

**Evoluzione pianificata** (Fase 7.2): dataset reale → Approccio C
(VLM + LoRA con output `{stato, tutorial}`), usando `vlm_dataset.jsonl` già
prodotto dal builder. L'interfaccia di `diagnose()` resta invariata.

---

## ADR-010 — Diagnosi stato, Approccio C: VLM + LoRA (scheletro)

**Contesto**: l'Approccio A (ADR-009) predice solo lo **stato** con un MLP
su embedding CLIP; il tutorial arriva da un secondo step (LLM). L'idea più
ambiziosa è un **unico modello vision-generativo** che, dalla foto,
produca direttamente stato **e** tutorial in JSON.

**Decisione**: predisporre il **fine-tuning LoRA di un Visual-LLM**
(default `Qwen/Qwen2-VL-2B-Instruct`) sul dataset `vlm_dataset.jsonl` già
generato dal builder. Stato attuale: **scheletro completo e validato**
(non ancora addestrato — richiede la GPU dell'utente).

**Componenti**:

| File | Ruolo |
| ---- | ----- |
| `scripts/train_condition_vlm_lora.py` | training LoRA (PEFT) + `--dry-run` di validazione |
| `app/ml/condition_vlm.py` | inferenza: base + adapter → JSON `{stato, difetto, tutorial}` |
| `ml/datasets/garment_condition/vlm_dataset.jsonl` | dataset instruction-tuning (prodotto dal builder) |

**Configurazione LoRA**: rank 16, alpha 32, dropout 0.05, target
`q/k/v/o_proj` (attention), bf16. Opzione QLoRA 4-bit (`--load-4bit`,
richiede `bitsandbytes`) per ridurre la VRAM.

**Requisiti hardware**: GPU NVIDIA ~10-16 GB (full LoRA) o ~6-8 GB
(QLoRA 4-bit). Su CPU non è praticabile.

**Perché "scheletro" e non già addestrato**:

- Il training scarica ~4 GB di pesi e richiede una GPU; lo lasciamo
  all'ambiente dell'utente.
- Il `--dry-run` valida dipendenze, GPU, dataset, formato e immagini senza
  scaricare nulla — così il setup è verificabile subito.

**Integrazione (production-ready)**: `services/condition.py` implementa un
**routing a cascata** fra i tre backend, guidato da
`CLOSETAI_CONDITION_BACKEND`:

| Valore        | Comportamento                                                |
| ------------- | ------------------------------------------------------------ |
| `auto` (def.) | prova VLM → MLP → euristica, usa il primo disponibile        |
| `vlm-lora`    | forza il VLM (fallback euristica se adapter assente)         |
| `clip-mlp`    | forza l'MLP (fallback euristica se pesi assenti)             |
| `heuristic`   | forza l'euristica                                            |

Garanzie:

- **Fail-safe**: `diagnose()` restituisce *sempre* uno stato valido — se il
  backend scelto non è disponibile o produce output non valido (stato fuori
  dalle 4 classi), ricade automaticamente sull'euristica.
- **Output validato**: l'output del VLM passa per `_normalize_condition()`
  (sinonimi → label canoniche; stato sconosciuto → fallback).
- **Tutorial inline**: quando il backend è il VLM, `DiagnoseResponse`
  include `defect` e `tutorial` (gli altri backend li lasciano `null` e il
  tutorial si ottiene da `/repair-tutorials`).
- **Test**: routing, fallback a cascata, parsing/validazione, forzature —
  coperti con un VLM fittizio (no GPU richiesta in CI).

> ⚠️ Latenza: la generazione VLM richiede secondi (GPU). In `POST /diagnose`
> la chiamata è sincrona; per volumi alti andrà spostata in background
> (task queue) — non necessario per il prototipo.

**Caveat dati**: i tutorial del dataset base provengono dalla KB hardcoded.
Per target più ricchi e personalizzati si usa la **distillazione**
(`scripts/distill_tutorials.py`): un VLM grande (Claude, GPT-4o, o un VLM
locale via Ollama) guarda ogni foto e scrive un tutorial specifico su
colore, posizione ed entità del danno. L'output è
`vlm_dataset_distilled.jsonl`, drop-in per il training LoRA al posto del
jsonl base. La funzione multimodale è `app/services/llm.py::generate_vision()`
(immagine base64 → litellm). Vedi la datasheet per il confronto
hardcoded vs distillato.

---

## ADR-011 — Gap analysis del guardaroba: rete neurale tabellare

**Contesto**: Fashion-CLIP *riconosce* i capi dalle foto, ma non dice nulla
sulla **composizione** del guardaroba nel suo insieme. L'utente vuole
acquisti più consapevoli: serve un modello che capisca se l'armadio è
equilibrato o se ha *vuoti funzionali* (manca una giacca/cappotto, troppe
t-shirt, poche alternative invernali…).

**Decisione**: una **rete neurale multi-label** addestrata da noi che lavora
su **dati tabellari aggregati** (non sulle immagini):

```
guardaroba ──▶ feature aggregate (14) ──▶ MLP ──▶ 6 vuoti funzionali (multi-label)
   (DB)        conteggi, colori,                   sigmoid + soglia
               stagionalità, ghost-ratio
```

- **Feature** (`gap_model.FEATURE_NAMES`): conteggi per macro-ruolo
  (top/bottom/outerwear/shoes/dress/accessory), totale, frazioni
  (t-shirt, giacche/cappotti, invernali, formali), n. colori, presenza neutri,
  ghost-ratio.
- **Label** (`GAP_LABELS`): `manca_capospalla`, `manca_scarpe`,
  `manca_formale`, `manca_invernale`, `troppe_tshirt`, `poca_varieta_colori`.
- **Modello**: MLP `14 → 64 → 32 → 6`, BCEWithLogits, multi-label.

**Dataset**: tabellare **sintetico**, generato da
`scripts/build_wardrobe_dataset.py` campionando profili di guardaroba
realistici (minimal / balanced / tshirt_heavy / summer_only / formal /
random). Le categorie sono **ispirate a DeepFashion**; le etichette sono
prodotte da regole esperte (`rule_based_gaps`) con rumore di
etichettatura (8%), così la rete apprende le soglie invece di memorizzarle.

**Risultati** (5000 righe, split 70/15/15):

| Metrica            | Valore  |
| ------------------ | ------- |
| Micro-F1           | ~0.94   |
| Macro-F1           | ~0.93   |
| Hamming loss       | ~0.04   |
| Subset accuracy    | ~0.78   |

**Integrazione**: `services/gap_analysis.py` aggrega il guardaroba **reale**
(query `Item` + `WearEvent`, esclude i capi ritirati), calcola le stesse
feature e predice con la rete. Endpoint `GET /stats/gap-analysis` →
vuoti + raccomandazioni (con preferenza per il second-hand), mostrati nella
dashboard. **Fallback fail-safe**: se i pesi non esistono, usa le stesse
`rule_based_gaps` (output `source: "rules"` invece di `"neural-net"`).

**Perché "rules" come ground-truth e fallback**: le regole sono la
conoscenza esperta che vogliamo che la rete apprenda; usarle anche come
fallback garantisce che la feature funzioni *sempre*, anche senza pesi
addestrati. Onestà: su dati reali la rete è limitata dalla qualità delle
regole con cui è stata generata; per andare oltre servirebbe feedback reale
degli utenti sui suggerimenti.

---

## Layout dei moduli ML / AI

```
backend/app/
├── ml/
│   ├── classifier.py       # interfaccia + factory + Mock + FashionClip
│   ├── color.py            # estrazione colore dominante (PIL quantize)
│   └── (futuro: defects.py, recommender.py, ...)
└── services/
    ├── embeddings.py       # wrapper ChromaDB (collection "items")
    ├── llm.py              # gateway litellm + DB cache
    ├── descriptions.py     # item description via LLM
    ├── coach.py            # coach sostenibilità via LLM
    ├── repair_tutorials.py # KB hardcoded + enrich_with_llm()
    ├── condition.py        # diagnosi stato: modello vision + fallback euristica
    └── tryon.py            # backend astratto + DiffusersLocalBackend

backend/app/ml/
    ├── classifier.py       # Fashion-CLIP (+ embed_image come feature extractor)
    ├── color.py
    ├── condition_model.py  # Approccio A: MLP addestrato da noi (testa su CLIP)
    ├── condition_vlm.py    # Approccio C: inferenza VLM + LoRA (scheletro)
    └── gap_model.py        # gap analysis: MLP multi-label su feature tabellari

backend/app/services/
    └── gap_analysis.py     # feature dal guardaroba reale + predizione gap

backend/scripts/
    ├── build_condition_dataset.py    # genera il dataset (degradazione sintetica)
    ├── fetch_real_garments.py        # scarica capi reali (FashionMNIST)
    ├── train_condition_model.py      # Approccio A: MLP su embedding CLIP
    ├── train_condition_vlm_lora.py   # Approccio C: LoRA su Qwen2-VL
    ├── build_wardrobe_dataset.py     # genera il dataset tabellare guardaroba
    └── train_gap_model.py            # addestra l'MLP multi-label di gap analysis
```

L'interfaccia condivisa è la dataclass `ClassificationResult`:

```python
@dataclass(frozen=True, slots=True)
class ClassificationResult:
    category: str | None
    color: str | None
    embedding: list[float] | None   # 512d per Fashion-CLIP, None per mock
    confidence: float | None        # softmax sulla top class
```

---

## Variabili d'ambiente rilevanti

| variabile                       | default                              | scope     | note                                                       |
| ------------------------------- | ------------------------------------ | --------- | ---------------------------------------------------------- |
| `CLOSETAI_CLASSIFIER`           | `fashion-clip`                       | runtime   | `mock` per i test e fallback senza torch.                  |
| `CLOSETAI_DATA_DIR`             | `<repo>/data`                        | runtime   | root storage; ChromaDB sotto `<DATA_DIR>/chroma/`.         |
| `CLOSETAI_DB_PATH`              | `<DATA_DIR>/closetai.db`             | runtime   | SQLite path.                                               |
| `CLOSETAI_DATABASE_URL`         | derivata da `DB_PATH`                | runtime   | DSN SQLAlchemy completo (override totale).                 |
| `CLOSETAI_LLM_MODEL`            | `claude-haiku-4-5`                   | runtime   | nome modello litellm (es. `ollama/llama3.2`, `openai/gpt-4o-mini`). |
| `CLOSETAI_LLM_TIMEOUT`          | `20` (sec)                           | runtime   | timeout chiamate LLM.                                      |
| `CLOSETAI_LLM_MAX_TOKENS`       | `800`                                | runtime   | tetto generazione.                                         |
| `CLOSETAI_LLM_CACHE_TTL_HOURS`  | `24`                                 | runtime   | TTL della tabella `llm_cache`.                             |
| `CLOSETAI_CONDITION_BACKEND`    | `auto`                               | runtime   | `auto`/`vlm-lora`/`clip-mlp`/`heuristic` — routing diagnosi stato. |
| `CLOSETAI_CONDITION_WEIGHTS`    | `ml/weights/condition_head.pt`       | runtime   | pesi MLP (Approccio A).                                    |
| `CLOSETAI_CONDITION_VLM_ADAPTER`| `ml/weights/condition_vlm_lora`      | runtime   | adapter LoRA (Approccio C).                                |
| `CLOSETAI_CONDITION_VLM_BASE`   | `Qwen/Qwen2-VL-2B-Instruct`          | runtime   | modello base del VLM.                                      |
| `CLOSETAI_TRYON_BACKEND`        | `disabled`                           | runtime   | `diffusers` per try-on locale.                             |
| `CLOSETAI_TRYON_MODEL`          | `stabilityai/stable-diffusion-2-inpainting` | runtime | HF model id per try-on.                            |
| `CLOSETAI_TRYON_DIR`            | `<DATA_DIR>/tryon`                   | runtime   | output try-on.                                             |
| `ANTHROPIC_API_KEY`             | _(non set)_                          | esterno   | richiesta dai modelli Claude.                              |
| `OPENAI_API_KEY`                | _(non set)_                          | esterno   | richiesta dai modelli OpenAI.                              |
| `OLLAMA_API_BASE`               | `http://localhost:11434`             | esterno   | endpoint Ollama locale.                                    |
| `HF_HOME`                       | `~/.cache/huggingface`               | esterno   | cache pesi HuggingFace; ridirigibile su disco esterno.     |

---

## Benchmark (Fase 2, hardware locale)

Misurato su Windows 11, CPU desktop (no CUDA), torch 2.12 CPU, transformers 5.9,
`patrickjohncyh/fashion-clip`. Comando:

```bash
cd backend && uv run python scripts/benchmark_classifier.py
```

| Classificatore         | Warmup     | Mean (post-warmup) | Stdev    | Embedding | Note                                              |
| ---------------------- | ---------- | ------------------ | -------- | --------- | ------------------------------------------------- |
| `MockClassifier`       | 6 ms       | **4 ms**           | 0.4 ms   | —         | Solo PIL quantize + `random.choice`.              |
| `FashionClipClassifier`| 7.6 s      | **64 ms**          | 1.5 ms   | 512 dim   | Warmup include load + JIT compilation PyTorch.    |

**Letture chiave**:

- 64 ms/inferenza CPU è perfettamente compatibile con un MVP single-user; il
  ritmo di upload realistico (< 1 capo/secondo) non satura mai il classifier.
- Il warmup di 7.6 s lo paghiamo **una volta** alla prima inferenza dopo il
  boot del backend: accettabile.
- Su GPU consumer attendiamo 10–25 ms/inferenza (mai validato — la
  configurazione CUDA dipende dal sistema del compagno).

I numeri precedenti motivano la scelta server-side dell'ADR-005: non ha senso
oggi pagare il costo dell'export ONNX per spostare il modello on-device.
