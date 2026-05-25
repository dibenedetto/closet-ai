# Handover — stato finale del progetto

> Documento di consegna del prototipo. Riepiloga lo stato del codebase al
> termine delle 6 fasi pianificate (vedi [PLAN.md](../PLAN.md)) e indica
> cosa è "pronto", cosa è "skeleton" e cosa è **futuro** (ovvero estensione
> che richiede ulteriore lavoro).

---

## Cosa è completo (Fase 1-6)

### Backend (FastAPI + SQLite + ChromaDB)

| Endpoint                                  | Funzione                                          |
| ----------------------------------------- | ------------------------------------------------- |
| `GET /api/v1/health`                      | health check                                      |
| `POST/GET/DELETE /api/v1/items`           | CRUD capi + upload immagine + auto-classifier     |
| `GET /api/v1/items/{id}/image`            | serve l'immagine del capo                         |
| `POST /api/v1/items/{id}/reclassify`      | ri-classifica via Fashion-CLIP                    |
| `POST /api/v1/items/{id}/wear`            | registra utilizzo                                 |
| `POST /api/v1/wear-events/batch`          | registrazione batch                               |
| `GET /api/v1/items/{id}/wears`            | storico utilizzi                                  |
| `DELETE /api/v1/wear-events/{id}`         | rimuove un singolo evento                         |
| `GET /api/v1/items/{id}/stats`            | stats per capo (count, cpw, ghost, ecc.)          |
| `GET /api/v1/stats/wardrobe`              | stats aggregate guardaroba                        |
| `GET /api/v1/stats/ghosts`                | lista capi fantasma                               |
| `GET /api/v1/stats/impact`                | impact circolare aggregato                        |
| `GET /api/v1/outfits/suggest`             | N proposte di outfit (meteo + colore + ghost)     |
| `POST/GET /api/v1/outfits/feedback`       | like/dislike sugli outfit                         |
| `POST /api/v1/items/{id}/diagnose`        | diagnosi euristica + suggerimenti                 |
| `PUT /api/v1/items/{id}/condition`        | override manuale condizione                       |
| `POST/GET /api/v1/items/{id}/actions`     | azioni circolari (registra/lista)                 |
| `DELETE /api/v1/actions/{id}`             | rimuove azione (riattiva il capo se necessario)   |
| `GET /api/v1/repair-tutorials[/defects]`  | tutorial riparazione (KB hardcoded)               |

| `GET /api/v1/llm/status` · `/tryon/status` | introspection per UI            |
| `POST /api/v1/items/{id}/describe`        | descrizione capo via LLM          |
| `GET /api/v1/stats/coach`                 | coach sostenibilità via LLM       |
| `GET /api/v1/repair-tutorials/enrich`     | tutorial via LLM (con fallback)   |
| `POST /api/v1/items/{id}/try-on`          | try-on virtuale via diffusion     |
| `GET /api/v1/items/{id}/try-on/{file}`    | serve immagine try-on generata    |

Riferimento completo con payload di esempio: [docs/api.md](api.md).

### Machine Learning (applicato)

- **Fashion-CLIP** (`patrickjohncyh/fashion-clip`) integrato server-side
  con fallback su mock zero-shot via env var.
- Embedding 512d salvati su **ChromaDB persistente** (`data/chroma/`).
- Estrazione colore dominante con quantize + filtro sfondo chiaro.
- Diagnosi condizione capo via euristica `wear_count + età`.
- Tabella CO₂ × % evitamento per stima dell'impatto circolare.
- **Notebook addestrato** [ml/notebooks/closetai_ml.ipynb](../ml/notebooks/closetai_ml.ipynb):
  3 modelli sklearn su dati sintetici (classificazione "ghost predictor",
  regressione "wear forecast", clustering "stili"). Soddisfa il requisito
  del corso "INTEGRAZIONE OBBLIGATORIA — Classificazione, Regressione,
  Clustering". Riproducibile via
  `backend/scripts/build_ml_notebook.py` + `jupyter nbconvert --execute`.

### AI generativa (attivata in Fase 6.1)

- **Gateway litellm** (`services/llm.py`): unico punto di chiamata
  multi-provider (Anthropic, OpenAI, Ollama locale, vLLM, HF Inference).
  Configurabile via `CLOSETAI_LLM_MODEL`.
- **Descrizione capi** (`services/descriptions.py`): genera 1-2 frasi
  italiane per ogni capo, salvate su `Item.description`.
- **Coach sostenibilità** (`services/coach.py`): consiglio personalizzato
  dalla dashboard, basato su stats + capi fantasma.
- **Tutorial riparazione** (`services/repair_tutorials.py`): KB hardcoded
  + funzione `enrich_with_llm()` per personalizzazione su categoria/colore/
  condizione del capo.
- **Try-on virtuale** (`services/tryon.py`): backend astratto, default
  `disabled`; `DiffusersLocalBackend` esegue Stable Diffusion 2 inpainting
  locale con maschera torso euristica.
- **Cache risposte** (`models/llm_cache.py`): tabella con TTL 24h.
- Tutti i path hanno **graceful fallback**: se il provider non è
  configurato, l'endpoint risponde 503 e il frontend nasconde i bottoni AI.

### Frontend (React 19 + Vite 7 + TypeScript)

- 6 pagine: `/` (guardaroba), `/items/new`, `/items/:id`, `/today`,
  `/dashboard`, `/mirror`.
- API client tipizzato in `src/api/` (5 file).
- Componente riutilizzabile `<CircularSection>` per il modulo circolare.
- UI dark theme con palette coerente, skeleton loaders, transitions,
  mobile responsive.
- Filtri sulla home (categoria, ricerca, stato attivo/ritirato).
- Dashboard con equivalenze CO₂ tangibili (km auto, voli, m² foresta) e
  bar chart CSS-only.

### Testing

- **108 test backend** (`pytest`) verdi:
  - 31 CRUD items + validazioni
  - 12 classifier (mock + color)
  - 5 reclassify + Chroma
  - 14 wear log + stats
  - 17 outfit recommender + meteo fallback + feedback
  - 20 modulo circolare (diagnosi + azioni + impact + tutorial)
  - + health
- Fixture isolata per ogni test: DB SQLite temp, cartella `items/`, Chroma,
  classifier mock obbligatorio.

### Documentazione

- [README.md](../README.md) — quick start + comandi utili.
- [PROJECT.md](../PROJECT.md) — scheda di progetto completa (14 sezioni).
- [PLAN.md](../PLAN.md) — roadmap operativa e stato.
- [CLAUDE.md](../CLAUDE.md) — convenzioni e istruzioni AI.
- [docs/api.md](api.md) — riferimento API completo.
- [docs/architecture.md](architecture.md) — 7 ADR motivate.
- [docs/raspberry-pi.md](raspberry-pi.md) — setup hardware specchio.
- [docs/demo-script.md](demo-script.md) — scaletta operativa demo finale.
- [docs/screenshots/README.md](screenshots/README.md) — come catturare gli
  screenshot (manuale).
- [docs/presentation.pptx](presentation.pptx) — slide consegna (23 slide,
  italiano). Rigenerabile via
  `backend/scripts/generate_presentation.py`.

### Tooling

- Setup cross-platform: `scripts/setup.{sh,ps1,bat}`,
  `scripts/run-{backend,frontend}.{sh,ps1,bat}`, `scripts/start-mirror.sh`.
- Seed data demo: `backend/scripts/seed_demo.py`.
- Benchmark classifier: `backend/scripts/benchmark_classifier.py`.
- VS Code launch profiles + settings (`.vscode/`).

---

## Cosa è "skeleton" (da completare)

Funzionalità predisposte ma non al 100% per la produzione reale:

1. **Screenshot UI in README** — `docs/screenshots/` ha le istruzioni; i
   PNG vanno catturati a mano una volta avviato il sistema.
2. **Specchio Raspberry Pi** — la pagina `/mirror` funziona, lo script
   kiosk c'è, ma non è stato validato su hardware fisico.
3. **Try-on garment-aware (IDM-VTON)** — l'attuale backend usa Stable
   Diffusion inpainting con maschera torso euristica: visivamente
   convincente per la demo ma non è un vero try-on garment-aware.
   IDM-VTON è elencato come path di sblocco in ADR-007.
4. **Auth** — single-user locale (decisione consapevole, vedi PLAN
   "Decisioni aperte").
5. **Marketplace integration** — i suggerimenti di "vendita" oggi non
   linkano a Vinted/Wallapop. Aggiunta lineare in Fase 7+.

---

## Cosa è "futuro" (estensioni)

Idee parcheggiate, da affrontare in cicli successivi al corso:

- Detection automatica capi indossati da una foto outfit (multi-label).
- Wear log con riconoscimento da camera dello specchio (PIR + ML).
- Gap analysis: "ti manca un capo per coprire la categoria X".
- Modalità famiglia / guardaroba condiviso.
- Notifiche push capi non indossati da > N giorni.
- Export guardaroba in formato standard (migrazione cross-app).
- ONNX export del classifier per inference on-device (browser, WebGPU).
- Migrazione a Postgres + S3 per multi-user reale.
- Alembic per gestire le migrazioni (al momento `create_all` + ALTER
  TABLE idempotente in `app/db.py`).

---

## Decisioni architetturali (riassunto)

Vedi [docs/architecture.md](architecture.md) per dettagli e alternative
considerate.

| #     | Tema                       | Decisione                                                 |
| ----- | -------------------------- | --------------------------------------------------------- |
| ADR-001 | Persistenza              | SQLite + filesystem per immagini, Postgres+S3 in prod    |
| ADR-002 | Migrazioni               | `create_all` + ALTER TABLE idempotenti finché schema cambia |
| ADR-003 | Classifier               | Fashion-CLIP (`patrickjohncyh/fashion-clip`)              |
| ADR-004 | Embedding storage        | ChromaDB persistente locale                               |
| ADR-005 | Inference                | Server-side oggi; ONNX/on-device come estensione          |
| ADR-006 | Colore dominante         | Pillow quantize + filtro sfondo chiaro                    |
| ADR-007 | Try-on diffusion         | Backend pluggable (DiffusersLocalBackend, default disabled) |
| ADR-008 | LLM gateway              | litellm (Anthropic / OpenAI / Ollama / HF) + DB cache 24h |

---

## Per chi prende in mano il progetto

1. **Leggi** [README.md](../README.md) per avviare il sistema in 5 minuti.
2. **Leggi** [PROJECT.md](../PROJECT.md) per il contesto.
3. **Esegui** la suite di test:

   ```bash
   cd backend && uv run pytest
   ```

   Se non sono verdi, qualcosa è cambiato dopo la consegna: leggi il
   commit log per capire cosa.

4. **Popola** il guardaroba demo:

   ```bash
   cd backend && uv run python scripts/seed_demo.py --reset
   ```

5. **Esplora** il codice in questo ordine consigliato:
   - `backend/app/main.py` — entry point, routing.
   - `backend/app/models/` — schema dati.
   - `backend/app/services/` — logica di business (color, recommender,
     condition, circular, repair_tutorials, stats, weather, embeddings).
   - `backend/app/routers/` — endpoint REST.
   - `frontend/src/api/` — client API tipizzato.
   - `frontend/src/pages/` — pagine React.

6. **Estendi** prendendo come template uno dei moduli completi (es. wear
   log o circular: file paralleli `models/X.py + schemas/X.py +
   services/X.py + routers/X.py + tests/test_X.py`).
