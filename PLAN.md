# PLAN.md — ClosetAI

> Roadmap operativa. Aggiornare lo stato dei task man mano che vengono completati.
> Legenda: `[ ]` da fare · `[~]` in corso · `[x]` completato · `[-]` scartato

---

## Stato attuale
**Fase**: 1 — Scheletro
**Ultimo aggiornamento**: 2026-05-21

> 1.1 Setup repository completato.

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
- [ ] `uv init` in `backend/`, target Python 3.14
- [ ] `uv add fastapi uvicorn sqlalchemy pydantic pillow python-multipart`
- [ ] `uv add --dev pytest httpx ruff`
- [ ] `app/main.py` con app FastAPI, CORS abilitato per frontend locale
- [ ] Configurazione SQLite (`app/db.py`)
- [ ] Modello `Item`: id, name, category, color, image_path, price, purchase_date, created_at
- [ ] Migrazione iniziale (Alembic o create_all per MVP)
- [ ] Endpoint health check `GET /api/v1/health`

### 1.3 Backend — CRUD items
- [ ] `POST /api/v1/items` — upload foto + metadata, salva file su disco in `data/items/`
- [ ] `GET /api/v1/items` — lista paginata
- [ ] `GET /api/v1/items/{id}` — dettaglio singolo
- [ ] `DELETE /api/v1/items/{id}` — eliminazione (anche del file)
- [ ] `GET /api/v1/items/{id}/image` — serve l'immagine
- [ ] Validazione: formati immagine ammessi (jpg, png, webp), size max 10MB

### 1.4 Backend — classificazione mock
- [ ] `app/ml/classifier.py` con funzione `classify(image_path) -> dict`
- [ ] Restituisce categoria casuale da lista fissa (camicia, jeans, maglione, ...) e colore dominante con PIL
- [ ] Chiamata automatica in `POST /items` per popolare `category` e `color`
- [ ] Test unitario sulla funzione mock

### 1.5 Backend — test
- [ ] Setup pytest + fixture per DB di test
- [ ] Test per ogni endpoint CRUD
- [ ] Test classificazione mock

### 1.6 Frontend — scheletro React
- [ ] Setup Vite + React + TypeScript
- [ ] Routing base (react-router): home, dettaglio capo, aggiungi capo
- [ ] Client API in `src/api/items.ts` con fetch tipizzato
- [ ] Variabile ambiente per URL backend

### 1.7 Frontend — UI minima
- [ ] Pagina lista capi (griglia di card con foto, categoria, colore)
- [ ] Form upload con preview immagine
- [ ] Pagina dettaglio capo
- [ ] Pulsante elimina con conferma
- [ ] Stile minimale ma pulito (Tailwind o CSS modules)

### 1.8 Documentazione
- [ ] `docs/api.md` con elenco endpoint e payload di esempio
- [ ] `README.md` aggiornato con comandi: `uvicorn ...`, `npm run dev`
- [ ] Screenshot della UI nel README

### Definition of Done — Fase 1
- Carico una foto dal frontend → la vedo nella lista con categoria mock e colore reale
- Posso aprire il dettaglio e eliminarla
- Tutti i test passano
- README permette a un compagno di studi di avviare il progetto da zero

---

## Fase 2 — Vision reale (settimana 2)

Obiettivo: sostituire la classificazione mock con un modello pre-trained reale.

- [ ] Valutare opzioni: CLIP zero-shot vs fashion classifier dedicato (es. `valhalla/fashion-clip`)
- [ ] Decisione documentata in `docs/architecture.md`
- [ ] Integrazione modello scelto in `app/ml/classifier.py`
- [ ] Estrazione embedding del capo (vettore salvato in DB come blob o file npy)
- [ ] Estrazione colore dominante migliorata (es. k-means su pixel)
- [ ] Endpoint `POST /items/{id}/reclassify` per ri-eseguire la classificazione
- [ ] Benchmark tempi inferenza (CPU vs GPU se disponibile)
- [ ] Decisione su on-device vs server-side, motivata
- [ ] Aggiornare UI per mostrare confidenza della classificazione

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
