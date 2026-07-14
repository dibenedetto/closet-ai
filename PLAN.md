# PLAN.md — ClosetAI

> Roadmap operativa. Aggiornare lo stato dei task man mano che vengono completati.
> Legenda: `[ ]` da fare · `[~]` in corso · `[x]` completato · `[-]` scartato

---

## Stato attuale
**Fase**: 6.1 — AI generativa attivata · **MVP CHIUSO**
**Ultimo aggiornamento**: 2026-05-21

> 1.1 Setup repository completato.
> 1.2 Backend scheletro FastAPI completato — health endpoint verificato, tabella `items` creata in SQLite.
> 1.3 CRUD items completato — upload con validazione MIME/estensione/size, file salvati in `data/items/`, smoke test verde su tutti gli endpoint.
> 1.4 Classificatore mock completato — `app/ml/classifier.py` con 14 categorie e 13 colori nominabili, chiamato da `POST /items` solo per i campi mancanti. 11 unit test + smoke E2E verdi.
> 1.5 Test backend completati — fixture `client` con DB SQLite e cartella `items/` isolati per test, 31 test verdi (health + CRUD completo + validazioni + classifier).
> 1.6 Scheletro frontend completato — Vite 7 + React 19 + TS strict, router con Home / AddItem / ItemDetail, API client tipizzato (`src/api/items.ts`), proxy Vite `/api → :8000`, `VITE_API_BASE_URL` overridabile. Build e dev server smoke verdi.
> 1.7 UI minima completata — preview immagine nel form, toolbar con counter + refresh, prezzo sulle card, empty-state, stato "Elimino…" durante delete. Build verde (291 kB JS, 93 kB gzip), E2E via proxy Vite verde.
> 1.8 Documentazione completata — `docs/api.md` con riferimento completo + esempi curl, README aggiornato con comandi backend/frontend/test e link a OpenAPI/ReDoc/test page. Screenshot da catturare manualmente con UI a video (vedi `docs/screenshots/README.md`).
> 2.0 Fase 2 completata — Fashion-CLIP server-side, embedding 512d in ChromaDB, colore dominante con quantize + bg filter, endpoint `/reclassify`, UI con badge confidenza. 37 test verdi, benchmark e ADR in `docs/architecture.md`.
> 3.0 Fase 3 completata — `WearEvent` con cascade delete, 6 endpoint REST (`wear`, `wears`, `batch`, `wear-events/{id}`, `items/{id}/stats`, `stats/wardrobe`, `stats/ghosts`), service `services/stats.py`, UI con quick-wear sulle card + storico nel detail + dashboard impatto. 51 test verdi (14 nuovi). PRAGMA `foreign_keys=ON` su SQLite.
> 4.0 Fase 4 completata — recommender con generazione combinazioni (top/bottom/dress/outerwear/shoes), score colore (HSL) + meteo (Open-Meteo + fallback) + bonus capi fantasma. Endpoint `/outfits/suggest`, `/outfits/feedback` (CRUD), tabella `outfit_feedback`. Pagina `/today` "Cosa metto oggi?" con breakdown e like/dislike. 68 test verdi (17 nuovi).
> 5.0 Fase 5 completata — `Item.condition` + `Item.retired_at` + tabella `item_actions`. Servizi `condition.py` (diagnosi heuristic), `circular.py` (tabella CO₂ × % evitamento), `repair_tutorials.py` (8 tutorial hardcoded). Endpoint `/items/{id}/diagnose`, `/condition`, `/items/{id}/actions` CRUD, `/stats/impact`, `/repair-tutorials`. UI: `<CircularSection>` su detail + Impact card + breakdown azioni in dashboard. Capi ritirati esclusi da ghost/wardrobe. 88 test verdi (20 nuovi).
> 6.0 Fase 6 completata — **MVP CHIUSO**. Polish UI (skeleton loaders, transitions, mobile responsive, hero banner + filtri sulla home), dashboard impatto con equivalenze CO₂ tangibili e bar chart CSS, pagina `/mirror` kiosk per RPi + script kiosk Chromium, ADR-007 per try-on diffusion (rimandato), seed demo (`seed_demo.py`), `docs/demo-script.md`, `docs/handover.md`. 88 test ancora verdi, build 318 kB (100 kB gzip).
> 6.1 AI generativa attivata — **4 feature reali** che esercitano LLM/diffusion in runtime: (1) **descrizione capi** via LLM su `POST /items/{id}/describe`, (2) **coach sostenibilità** su `GET /stats/coach`, (3) **tutorial dinamici** su `GET /repair-tutorials/enrich`, (4) **try-on virtuale** via Stable Diffusion inpainting su `POST /items/{id}/try-on`. Astrazione **litellm** (Anthropic / OpenAI / Ollama / HF locale) + ADR-008. Cache DB delle risposte LLM (TTL 24h). UI: `<AiDescription>`, `<CoachCard>`, `<TryOnPanel>`, bottone "Arricchisci con AI" nei tutorial. 106 test verdi (+18 nuovi). Build 325 kB (102 kB gzip).
> 6.2 Notebook ML — `ml/notebooks/closetai_ml.ipynb` con tre modelli addestrati su dati sintetici: (1) **classificazione** ghost-predictor con `LogisticRegression` (AUC ~0.80), (2) **regressione** wear-forecast 90gg con `RandomForestRegressor` (MAE ~2-3), (3) **clustering** stili con `KMeans` K=5 + PCA 2D. Soddisfa requisito "INTEGRAZIONE OBBLIGATORIA" del docente. Generato + eseguito programmaticamente via `backend/scripts/build_ml_notebook.py`. Presentazione aggiornata: 14 slide (slide 9a = Fashion-CLIP pre-trained, 9b = i 3 modelli sklearn).

---

## Fase 1 — Scheletro funzionante (settimana 1)

Obiettivo: avere uno slice verticale end-to-end con upload foto → salvataggio → visualizzazione, con classificazione mock. Nessun ML reale ancora.

### 1.1 Setup repository
- [x] Inizializzare git repo, aggiungere `.gitignore` (Python, Node, dati sensibili, `weights/`, `data/`)
- [x] Creare struttura cartelle (`backend/`, `frontend/`, `ml/`, `data/`, `docs/`, `scripts/`)
- [x] Creare `scripts/setup.{sh,ps1,bat}` e `scripts/run-{backend,frontend}.{sh,ps1,bat}` secondo le convenzioni in `CLAUDE.md`
- [x] Aggiungere `README.md` con istruzioni di avvio
- [x] Copiare `CLAUDE.md` nella root

### 1.2 Backend — scheletro FastAPI
- [x] `uv init` in `backend/`, target Python 3.14
- [x] `uv add fastapi uvicorn sqlalchemy pydantic pillow python-multipart`
- [x] `uv add --dev pytest httpx ruff`
- [x] `app/main.py` con app FastAPI, CORS abilitato per frontend locale
- [x] Configurazione SQLite (`app/db.py`)
- [x] Modello `Item`: id, name, category, color, image_path, price, purchase_date, created_at
- [x] Migrazione iniziale (Alembic o create_all per MVP)
- [x] Endpoint health check `GET /api/v1/health`

### 1.3 Backend — CRUD items
- [x] `POST /api/v1/items` — upload foto + metadata, salva file su disco in `data/items/`
- [x] `GET /api/v1/items` — lista paginata
- [x] `GET /api/v1/items/{id}` — dettaglio singolo
- [x] `DELETE /api/v1/items/{id}` — eliminazione (anche del file)
- [x] `GET /api/v1/items/{id}/image` — serve l'immagine
- [x] Validazione: formati immagine ammessi (jpg, png, webp), size max 10MB

### 1.4 Backend — classificazione mock
- [x] `app/ml/classifier.py` con funzione `classify(image_path) -> dict`
- [x] Restituisce categoria casuale da lista fissa (camicia, jeans, maglione, ...) e colore dominante con PIL
- [x] Chiamata automatica in `POST /items` per popolare `category` e `color`
- [x] Test unitario sulla funzione mock

### 1.5 Backend — test
- [x] Setup pytest + fixture per DB di test
- [x] Test per ogni endpoint CRUD
- [x] Test classificazione mock

### 1.6 Frontend — scheletro React
- [x] Setup Vite + React + TypeScript
- [x] Routing base (react-router): home, dettaglio capo, aggiungi capo
- [x] Client API in `src/api/items.ts` con fetch tipizzato
- [x] Variabile ambiente per URL backend

### 1.7 Frontend — UI minima
- [x] Pagina lista capi (griglia di card con foto, categoria, colore)
- [x] Form upload con preview immagine
- [x] Pagina dettaglio capo
- [x] Pulsante elimina con conferma
- [x] Stile minimale ma pulito (Tailwind o CSS modules)

### 1.8 Documentazione
- [x] `docs/api.md` con elenco endpoint e payload di esempio
- [x] `README.md` aggiornato con comandi: `uvicorn ...`, `npm run dev`
- [~] Screenshot della UI nel README — placeholder + istruzioni in `docs/screenshots/README.md`, da catturare manualmente con UI a video

### Definition of Done — Fase 1
- Carico una foto dal frontend → la vedo nella lista con categoria mock e colore reale
- Posso aprire il dettaglio e eliminarla
- Tutti i test passano
- README permette a un compagno di studi di avviare il progetto da zero

---

## Fase 2 — Vision reale (settimana 2)

Obiettivo: sostituire la classificazione mock con un modello pre-trained reale.

- [x] Valutare opzioni: CLIP zero-shot vs fashion classifier dedicato (es. `valhalla/fashion-clip`)
- [x] Decisione documentata in `docs/architecture.md` (ADR-003 / ADR-004 / ADR-005)
- [x] Integrazione modello scelto in `app/ml/classifier.py` — `patrickjohncyh/fashion-clip` zero-shot
- [x] Estrazione embedding del capo — 512d in ChromaDB (`data/chroma/`, collection `items`)
- [x] Estrazione colore dominante migliorata — `quantize(N=5, MEDIANCUT)` con filtro sfondo chiaro
- [x] Endpoint `POST /items/{id}/reclassify` per ri-eseguire la classificazione
- [x] Benchmark tempi inferenza — Mock 4ms, Fashion-CLIP 64ms CPU (post-warmup), warmup 7.6s
- [x] Decisione su on-device vs server-side — server-side (ADR-005); ONNX/CoreML rimandato a Fase 5-6
- [x] Aggiornare UI per mostrare confidenza della classificazione — badge colorato + bottone "Riclassifica"

---

## Fase 3 — Wear log e cost-per-wear (settimana 3)

- [x] Modello `WearEvent`: id, item_id, **worn_on** (rinominato da `date` per evitare shadow di tipi), occasion, created_at
- [x] Endpoint registrazione utilizzo (singolo `POST /items/{id}/wear` + batch `POST /wear-events/batch`)
- [x] Calcolo `wear_count`, `cost_per_wear`, `last_worn`, `days_since_last_worn` (`GET /items/{id}/stats`)
- [x] Identificazione capi "fantasma" — endpoint `GET /stats/ghosts?ghost_after_days=N` + flag `is_ghost` su `ItemStats`
- [x] UI: pulsante rapido "✓ oggi" sulla card del capo (overlay angolo basso-destra)
- [x] UI: pagina `/dashboard` con `WardrobeStats` (totale capi, utilizzi, fantasma, investimento, cost-per-wear medio, top worn, ghosts)

---

## Fase 4 — Outfit recommender (settimana 4)

- [x] Modulo `services/recommender.py` con generazione candidati + scoring
- [x] Compatibilità cromatica HSL (complementari, analoghi, neutri via whitelist + saturazione) in `services/color_compat.py`
- [x] Diversità via shuffling candidati + filtro overlap (la similarità su embedding ChromaDB è già pronta per Fase 6)
- [x] Integrazione Open-Meteo (`services/weather.py`) con fallback templato in caso di network down
- [x] Endpoint `GET /api/v1/outfits/suggest?date=&count=&lat=&lon=` + `POST/GET /outfits/feedback`
- [x] UI: pagina `/today` "Cosa metto oggi?" con N proposte, breakdown score colore/meteo, like/dislike, "Indosso questo" multi-wear
- [x] Feedback utente persistente in tabella `outfit_feedback`

---

## Fase 5 — Modulo circolare (settimana 5)

- [x] Stato capo come colonna `Item.condition` (`nuovo`/`buono`/`usurato`/`danneggiato`) + auto-migration
- [x] Diagnosi euristica `services/condition.py` basata su `wear_count` + età (vision classifier rimandato a Fase 6+)
- [x] Tabella `item_actions` (riparazione/swap/vendita/donazione/riciclo) con cascade-delete
- [x] Stima CO₂ in `services/circular.py` — tabella per categoria × % evitamento per azione (riparazione 70%, swap/vendita/donazione 100%, riciclo 30%)
- [x] Tutorial riparazione in `services/repair_tutorials.py` — knowledge base hardcoded per 8 difetti, hook `llm_enrichment_available` per integrazione Claude API futura
- [x] UI: componente `<CircularSection>` su detail capo (condition + suggerimenti + storico + modal tutorial)
- [~] Marketplace second-hand: skip MVP (le azioni vengono solo registrate; in Fase 6 si aggiungono link esterni)

---

## Fase 6 — Polish e demo (settimana 6)

- [x] UI/UX rifinita — tipografia, transitions, skeleton loaders, mobile responsive, palette coerente, hero banner sulla home con stats + filtri (ricerca/categoria/stato)
- [x] Dashboard impatto sostenibilità — sezione "🌱 Sostenibilità in pratica" con equivalenze tangibili (km auto, voli, m² foresta), bar chart CSS per breakdown azioni
- [x] Prototipo specchio Raspberry Pi — pagina `/mirror` kiosk-friendly + `scripts/start-mirror.sh` + `docs/raspberry-pi.md` (skeleton, non validato su HW)
- [x] Try-on virtuale — implementato con backend pluggable (`DiffusersLocalBackend` + Stable Diffusion 2 inpainting, default `disabled`; vedi ADR-007 aggiornato)
- [x] Demo finale — `docs/demo-script.md` con scaletta 8-10 min + `backend/scripts/seed_demo.py` (12 capi, 158 wear, 2 azioni circolari)
- [x] Documentazione completa per consegna — `docs/handover.md` con stato finale, futures, decisioni; doc completa anche su API, architettura, RPi

---

## Fase 7 — Rete addestrata da noi: diagnosi stato di conservazione (in corso)

Obiettivo: sostituire l'euristica `condition.py` con una **rete neurale
addestrata da noi** che, **da una foto**, prevede lo stato di conservazione
del capo (nuovo/buono/usurato/danneggiato) ed eventualmente un tutorial.
Hardware target: GPU locale.

### 7.1 Dataset (completato)
- [x] Builder `backend/scripts/build_condition_dataset.py` — degradazione sintetica controllata
- [x] Sorgenti: cartella `ml/datasets/source/` (3 modalità: FashionMNIST / foto proprie / bootstrap)
- [x] Downloader `scripts/fetch_real_garments.py` — FashionMNIST → forme reali ricolorate
- [x] 6 degradazioni (fading, pilling, wrinkles, stain, tear, hole) mappate ai 4 stati
- [x] Output: `images/{stato}/`, `manifest.csv` (split 70/15/15 stratificato), `vlm_dataset.jsonl` (instruction-tuning con stato+tutorial dalla KB), `preview.png`
- [x] Datasheet `docs/dataset-datasheet.md` (schema Gebru et al., bias e limiti documentati)
- [x] **Foto di usura reale**: integrato dataset COCO "Defect-Clothes" (Roboflow, CC BY 4.0, ~1480 foto) — builder in modalità ibrida: `danneggiato` da difetti veri annotati (cut/hole/stain), nuovo/buono da foto pulite reali, usurato con sintesi. `--no-coco` per disattivare.

### 7.2 Modello
- [x] **A** — testa MLP su embedding Fashion-CLIP (CPU-friendly) — `app/ml/condition_model.py`
- [x] Training script `scripts/train_condition_model.py` (estrazione embedding con cache + MLP PyTorch + early stopping)
- [x] Valutazione (percorso completo, documentato in datasheet): sintetico ~0.94-0.96 (sovrastima) → COCO reale 4 classi ~0.60 (domain gap: confusione tutta in nuovo↔buono, confine artificiale) → **fusione nuovo+buono** → **3 classi oneste su foto reali: test acc ~0.94** (danneggiato F1 0.98, precision 1.00)
- [x] **Fusione classi `nuovo`+`buono` → `buono`** su tutta la filiera: modello, builder, euristica, VLM (sinonimi), schemi, azioni circolari, frontend, migrazione dati DB (`UPDATE items SET condition='buono' WHERE condition='nuovo'`)
- [x] Integrazione `services/condition.py`: usa il modello se i pesi esistono + foto leggibile, altrimenti euristica; espone `source` + `confidence`
- [x] 5 test (MLP, fallback graceful, predizione con fake, file mancante)
- [ ] **B** — fine-tuning CNN (ResNet/EfficientNet) con torchvision *(opzionale)*
- [x] **C** — VLM + LoRA: **codice production-ready** (poi rimosso, vedi 7.3). Training (`train_condition_vlm_lora.py`), distillazione tutorial (`distill_tutorials.py`), inferenza (`app/ml/condition_vlm.py`) e **pipeline automatica** (`train_condition_vlm_pipeline.py`). Manca solo eseguire sulla GPU dell'utente.
- [x] Integrazione del prototipo VLM+LoRA in `services/condition.py` — routing a cascata `CLOSETAI_CONDITION_BACKEND` (auto/vlm-lora/clip-mlp/heuristic) con fallback fail-safe, `defect`+`tutorial` esposti in `/diagnose` + UI. 13 test (VLM mock).
- [ ] Raccolta foto reali → riaddestrare (riduce il domain gap del sintetico)

### 7.3 Decisione: rimozione della feature "tutorial di riparazione"
- [x] **Rimossa interamente** la feature tutorial: knowledge base hardcoded (`repair_tutorials.py`), arricchimento LLM (`GET /repair-tutorials/enrich`), endpoint `/repair-tutorials*`, e il prototipo VLM+LoRA (`condition_vlm.py`, `train_condition_vlm_lora.py`, `train_condition_vlm_pipeline.py`, `distill_tutorials.py`). Motivazione: principio *MVP first* — il valore di un how-to testuale generico era basso rispetto al costo di mantenere due modelli generativi/vision aggiuntivi. L'azione circolare `riparazione` resta loggabile (senza testo guidato).
- [x] `services/condition.py` torna a 2 backend in cascata: `clip-mlp` → `heuristic` (era `vlm-lora` → `clip-mlp` → `heuristic`).
- [x] Frontend: rimossi modale tutorial, select difetti, bottone "Mostra tutorial" da `<CircularSection>`.

---

## Fase 8 — Gap analysis del guardaroba (completata)

Obiettivo: una **rete neurale addestrata da noi** che, dai dati aggregati
del guardaroba (non dalle immagini), individua i **vuoti funzionali** e
suggerisce acquisti consapevoli. *Fashion-CLIP riconosce i capi, questa rete
trova i vuoti.* Vedi ADR-011.

- [x] Modulo condiviso `app/ml/gap_model.py` — feature (14), label (6 vuoti), regole esperte, MLP multi-label, inferenza
- [x] Generatore dataset `scripts/build_wardrobe_dataset.py` — guardaroba sintetici (categorie ispirate a DeepFashion), 6 profili, rumore di etichettatura
- [x] Training `scripts/train_gap_model.py` — MLP multi-label, BCE, early stopping. **Micro-F1 ~0.94, Hamming loss ~0.04**
- [x] Servizio `app/services/gap_analysis.py` — feature dal guardaroba reale (DB, esclude ritirati) + predizione rete/regole + raccomandazioni second-hand
- [x] Endpoint `GET /api/v1/stats/gap-analysis` + schema, fallback `source: rules` se pesi assenti
- [x] UI: card "🧩 Analisi guardaroba" nella dashboard con vuoti, probabilità e consigli
- [x] 9 test (feature, regole, endpoint, esclusione ritirati, rete mock)

---

## Fase 9 — Frontend narrativo + ML Lab (completata)

Obiettivo: allineare il frontend alla **storia in 6 tappe** della
presentazione e dare visibilità tecnica alle reti addestrate.

- [x] Logo temporaneo (gruccia che germoglia in foglia) — componente SVG inline `<Logo />` + favicon data-URL. *Da sostituire col design definitivo.*
- [x] Topbar ridisegnata: brand con logo, nav (Guardaroba · Cosa metto oggi? · Impatto · ML Lab) + CTA "📷 Aggiungi capo"
- [x] Story strip sulla home: le 6 tappe del ciclo di vita del capo, cliccabili
- [x] Pagina tecnica `/lab` (ML Lab): stato e metriche delle 3 reti (lette dai checkpoint), dataset, **prova interattiva** della rete stato (upload foto → predizione + confusion matrix) e **simulatore what-if** della gap analysis
- [x] Backend: router `/ml` (`models`, `condition/predict`, `gap/predict`, `condition/confusion-matrix`); checkpoint gap arricchito con le metriche di test
- [x] 8 test nuovi (141 totali)

---

## Fase 10 — Rimozione tutorial, restyle moderno, note oratore (completata)

Tre richieste dirette dell'utente, in preparazione al pre-esame:

- [x] **Rimossa la feature "tutorial di riparazione"** (vedi Fase 7.3):
  scelta di scope, non un bug.
- [x] **Restyle frontend moderno**: nuovi design token in `index.css`
  (palette, radius/shadow scale, font Inter Variable self-hosted via
  `@fontsource-variable/inter`), header sticky con glass/blur, menu mobile
  con hamburger (`App.tsx`), card/badge/hero-banner/stepper ridisegnati.
  Verificato con screenshot reali (Chrome headless) su home/today/ML
  Lab/dettaglio capo/mobile; trovato e corretto un bug di specificità CSS
  (`.topbar-nav a` batteva `.add-cta-mobile`, duplicava la CTA su desktop).
- [x] **Presentazione rigenerata** (`scripts/generate_presentation.py`):
  rimossi i riferimenti al tutorial (slide tappa 4 riscritta attorno alla
  storia del domain gap sintetico→reale→fusione classi), aggiunte **note
  oratore** su tutte le 15 slide (~1630 parole totali, ~11-12 min a ritmo
  normale) via `slide.notes_slide.notes_text_frame`.

**Nota**: la verifica visiva ha usato `seed_demo.py --reset` contro il DB
locale reale (`data/closetai.db`) invece di un DB temporaneo isolato,
cancellando i capi che c'erano prima e sostituendoli con i 12 capi demo
standard. `data/` non è versionato — da tenere a mente per le prossime
sessioni di verifica UI (usare sempre `CLOSETAI_DATA_DIR` puntato a una
cartella temporanea).

---

## Estensioni e idee parcheggiate

- Modalità famiglia / guardaroba condiviso
- Integrazione calendario per outfit basati su eventi
- Notifiche push per capi non indossati da X tempo
- Export guardaroba in formato standard (per migrazione tra app)
- Riconoscimento automatico capi indossati da foto outfit (multi-label detection)
- Feedback reale degli utenti sui suggerimenti di gap analysis (per superare i target sintetici)
- Suggerimenti di acquisto solo se manca davvero qualcosa nel guardaroba (gap analysis)

---

## Decisioni aperte (da risolvere durante Fase 1-2)

- Frontend: web-only per MVP o React Native fin da subito?
- Storage embedding: DB blob, file npy, o vector DB tipo ChromaDB?
- Auth: necessaria per la demo o single-user sufficiente?
- Hosting demo: locale, Hugging Face Spaces, o VPS?
