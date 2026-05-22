# PLAN.md — ClosetAI

> Roadmap operativa. Aggiornare lo stato dei task man mano che vengono completati.
> Legenda: `[ ]` da fare · `[~]` in corso · `[x]` completato · `[-]` scartato

---

## Stato attuale
**Fase**: 2 — Vision reale (completata)
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

- [ ] Modello `WearEvent`: id, item_id, date, occasion (opzionale)
- [ ] Endpoint registrazione utilizzo (singolo o batch)
- [ ] Calcolo `wear_count`, `cost_per_wear`, `last_worn` per ogni capo
- [ ] Identificazione capi "fantasma" (mai indossati dopo X giorni dall'acquisto)
- [ ] UI: pulsante rapido "indossato oggi" sulla card del capo
- [ ] UI: vista dashboard con statistiche personali

---

## Fase 4 — Outfit recommender (settimana 4)

- [ ] Modulo `services/recommender.py`
- [ ] Compatibilità cromatica (regole base: complementari, analoghi, neutri)
- [ ] Similarità embedding per varietà
- [ ] Integrazione API meteo (Open-Meteo, gratuita, no auth)
- [ ] Endpoint `GET /api/v1/outfits/suggest?date=...`
- [ ] UI: pagina "Cosa metto oggi?" con 3 proposte
- [ ] Feedback utente (like/dislike) salvato per future iterazioni

---

## Fase 5 — Modulo circolare (settimana 5)

- [ ] Modello `ItemCondition`: stato capo (nuovo, buono, usurato, danneggiato)
- [ ] Vision model per diagnosi difetti (può essere semplice classifier addestrato su poche classi)
- [ ] Tabella `actions_suggested`: riparazione, swap, vendita, donazione, riciclo
- [ ] Stima CO₂ evitata per categoria capo (tabella di riferimento da Ellen MacArthur)
- [ ] Tutorial riparazione generati da LLM (chiamata a Claude API o modello locale)
- [ ] UI: scheda "azioni circolari" per ogni capo
- [ ] Eventuale integrazione con marketplace second-hand locali (mock o link esterni)

---

## Fase 6 — Polish e demo (settimana 6)

- [ ] UI/UX rifinita — usare strumenti AI generativi (v0, Figma AI) per design
- [ ] Dashboard impatto sostenibilità (CO₂ totale evitata, capi salvati, ecc.)
- [ ] Prototipo specchio con Raspberry Pi (opzionale, se tempo)
- [ ] Try-on virtuale con modello diffusion (estensione, opzionale)
- [ ] Demo video / presentazione finale
- [ ] Documentazione completa per consegna

---

## Estensioni e idee parcheggiate

- Modalità famiglia / guardaroba condiviso
- Integrazione calendario per outfit basati su eventi
- Notifiche push per capi non indossati da X tempo
- Export guardaroba in formato standard (per migrazione tra app)
- Riconoscimento automatico capi indossati da foto outfit (multi-label detection)
- Suggerimenti di acquisto solo se manca davvero qualcosa nel guardaroba (gap analysis)

---

## Decisioni aperte (da risolvere durante Fase 1-2)

- Frontend: web-only per MVP o React Native fin da subito?
- Storage embedding: DB blob, file npy, o vector DB tipo ChromaDB?
- Auth: necessaria per la demo o single-user sufficiente?
- Hosting demo: locale, Hugging Face Spaces, o VPS?
