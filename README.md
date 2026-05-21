# ClosetAI

Closet AI for green clothing — digitalizza il guardaroba, traccia l'uso reale dei capi e
usa il machine learning per ridurre acquisti impulsivi favorendo riparazione, scambio e rivendita.

Progetto didattico per il corso di **Virtual Worlds** (Master in Informatica per la Salute Digitale,
Università di Pisa). Per la scheda di progetto completa (motivazione, architettura, moduli) vedi
[PROJECT.md](PROJECT.md); per le convenzioni di codice e le istruzioni a Claude vedi
[CLAUDE.md](CLAUDE.md); per la roadmap operativa e lo stato dei task vedi [PLAN.md](PLAN.md).

## Stack

- **Backend**: Python 3.14, FastAPI, SQLAlchemy, SQLite — gestito con [uv](https://docs.astral.sh/uv/)
- **Frontend**: React + Vite + TypeScript
- **ML**: PyTorch + HuggingFace transformers + OpenCLIP (introdotti in Fase 2)

## Struttura del repository

```
closet-ai/
├── backend/      # API FastAPI + servizi + wrapper modelli ML
├── frontend/     # web app React/Vite
├── ml/           # notebook di esplorazione e pesi modelli (gitignored)
├── data/         # storage locale foto e DB (gitignored)
├── docs/         # architettura, API, decisioni tecniche
├── scripts/      # setup e run per macOS/Linux/Windows
├── CLAUDE.md     # istruzioni per Claude Code e convenzioni di progetto
└── PLAN.md       # roadmap e stato dei task
```

## Prerequisiti

- **Git**
- **Node.js >= 20** (necessario per il frontend) — https://nodejs.org/
- **uv** verrà installato automaticamente dallo script di setup se mancante
- Python 3.14 viene installato da uv stesso, non serve averlo nel sistema

## Quick start

### macOS / Linux

```bash
git clone <repo-url> closet-ai
cd closet-ai
chmod +x scripts/*.sh
./scripts/setup.sh
./scripts/run-backend.sh        # in un terminale
./scripts/run-frontend.sh       # in un altro terminale
```

### Windows (PowerShell)

```powershell
git clone <repo-url> closet-ai
cd closet-ai
.\scripts\setup.ps1
.\scripts\run-backend.ps1
.\scripts\run-frontend.ps1
```

### Windows (cmd.exe)

```bat
git clone <repo-url> closet-ai
cd closet-ai
scripts\setup.bat
scripts\run-backend.bat
scripts\run-frontend.bat
```

A backend attivo:

- API: http://localhost:8000
- Documentazione OpenAPI: http://localhost:8000/docs
- Pagina di test (CRUD via UI HTML): http://localhost:8000/test/

Il frontend di sviluppo gira su http://localhost:5173 (default Vite).

## Comandi utili

```bash
# Backend (eseguiti dalla cartella backend/)
uv sync                                  # installa/aggiorna dipendenze
uv add <pkg>                             # aggiunge una dipendenza runtime
uv add --dev <pkg>                       # aggiunge una dipendenza di sviluppo
uv run pytest                            # esegue i test
uv run uvicorn app.main:app --reload     # avvio manuale del backend

# Frontend (eseguiti dalla cartella frontend/)
npm install
npm run dev
npm run build
```

## Stato

Vedi [PLAN.md](PLAN.md) per lo stato dei task e la roadmap completa.

## Licenza

Vedi [LICENSE](LICENSE).
