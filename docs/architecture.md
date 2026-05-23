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

## ADR-007 — Try-on virtuale (diffusion): rimandato

**Contesto**: il PLAN Fase 6 elenca il *try-on virtuale* (es. IDM-VTON,
StreetTryOn) fra le estensioni opzionali. Si tratta di sintetizzare un
ritratto dell'utente che indossa virtualmente un capo del guardaroba,
usando un modello di diffusion image-to-image.

**Decisione**: **rimandato a post-corso**. La Fase 6 non lo include nel
prototipo consegnato.

**Motivazione**:

- I pesi di IDM-VTON sono ~5 GB. Costo di download/storage non
  giustificabile per una demo studentesca.
- L'inferenza richiede una GPU con almeno 12 GB di VRAM per essere
  utilizzabile; su CPU una singola immagine impiega minuti, non secondi.
- La pipeline UX (caricamento ritratto dell'utente, allineamento pose,
  masking) introduce molta complessità extra fuori dal core "wardrobe +
  sostenibilità".
- Privacy: il try-on richiede di salvare immagini del **corpo** dell'utente.
  Confligge con il principio "privacy by design" dell'MVP (ADR
  implicito su [PROJECT.md](../PROJECT.md) §5.3).

**Path di sblocco se servisse**:

1. Aggiungere `services/tryon.py` con interfaccia
   `try_on(garment_path, user_photo) -> generated_image_path`.
2. Esporre `POST /items/{id}/try-on` con upload del ritratto.
3. Mostrare risultato in modale sulla pagina `/items/{id}`.
4. Salvataggio risultati: **out-of-DB**, in `data/tryon/` con TTL breve.

---

## Layout dei moduli ML

```
backend/app/
├── ml/
│   ├── classifier.py       # interfaccia + factory + Mock + FashionClip
│   ├── color.py            # estrazione colore dominante (PIL quantize)
│   └── (futuro: defects.py, recommender.py, ...)
└── services/
    └── embeddings.py       # wrapper ChromaDB (collection "items")
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

| variabile                | default                              | scope     | note                                                       |
| ------------------------ | ------------------------------------ | --------- | ---------------------------------------------------------- |
| `CLOSETAI_CLASSIFIER`    | `fashion-clip`                       | runtime   | `mock` per i test e fallback senza torch.                  |
| `CLOSETAI_DATA_DIR`      | `<repo>/data`                        | runtime   | root storage; ChromaDB sotto `<DATA_DIR>/chroma/`.         |
| `CLOSETAI_DB_PATH`       | `<DATA_DIR>/closetai.db`             | runtime   | SQLite path.                                               |
| `CLOSETAI_DATABASE_URL`  | derivata da `DB_PATH`                | runtime   | DSN SQLAlchemy completo (override totale).                 |
| `HF_HOME`                | `~/.cache/huggingface`               | esterno   | cache pesi HuggingFace; ridirigibile su disco esterno.     |

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
