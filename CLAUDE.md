# CLAUDE.md — ClosetAI

## Contesto del progetto

Progetto didattico per il corso di **Virtual Worlds** (Master in Informatica per la Salute Digitale, Università di Pisa). Obiettivo: prototipare un sistema (app + eventuale specchio smart) che digitalizza il guardaroba dell'utente, ne traccia l'uso reale e usa l'AI per massimizzare il valore dei capi posseduti — riducendo acquisti impulsivi e favorendo riparazione, scambio, rivendita.

Il progetto deve dimostrare AI in **due ruoli distinti**:
- **AI generativa** come supporto al design (UI, tutorial, try-on virtuale)
- **Machine learning applicato** come componente funzionale del prodotto (classificazione, recommendation, diagnosi)

## Principi guida

1. **MVP first** — niente over-engineering, costruisci slice verticali end-to-end prima di approfondire un layer
2. **Privacy by design** — foto degli utenti sono sensibili (camera da letto, corpo); preferire inference on-device, non salvare immagini grezze in cloud
3. **Pre-trained > training from scratch** — per l'MVP usa modelli HuggingFace esistenti (CLIP, fashion classifiers); il fine-tuning è un'estensione opzionale
4. **Misurabilità sostenibilità** — ogni feature deve poter essere collegata a una metrica di impatto (capi non acquistati, CO₂ evitata, utilizzi/capo)
5. **Modularità** — il progetto è suddivisibile in moduli assegnabili a sottogruppi di studenti

## Stack tecnico

- **Backend**: Python 3.14+, FastAPI, SQLAlchemy, SQLite (Postgres in produzione)
- **Package manager Python**: [uv](https://docs.astral.sh/uv/) — gestione venv, dipendenze e lockfile
- **ML**: PyTorch, transformers (HuggingFace), open_clip, eventuale ONNX per export on-device
- **Frontend**: React (web) + Vite + TypeScript — React Native come estensione mobile
- **Storage**: filesystem locale per foto in MVP, S3-compatible in seguito
- **Specchio fisico (opzionale)**: Raspberry Pi 5 + monitor verticale + camera

## Struttura del repository

```
closetai/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry
│   │   ├── models/              # SQLAlchemy models
│   │   ├── routers/             # endpoints per dominio (items, outfits, wear_log)
│   │   ├── services/            # logica di business
│   │   └── ml/                  # wrapper inferenza modelli
│   ├── tests/
│   ├── pyproject.toml           # gestito da uv
│   └── uv.lock                  # lockfile, committato in repo
├── frontend/
│   └── src/
│       ├── components/
│       ├── pages/
│       └── api/
├── ml/
│   ├── notebooks/               # esplorazione, fine-tuning
│   └── weights/                 # checkpoint (gitignored)
├── data/                        # gitignored
├── docs/
│   ├── architecture.md
│   └── api.md
├── scripts/
│   ├── setup.sh                 # setup macOS/Linux
│   ├── setup.ps1                # setup Windows (PowerShell)
│   ├── setup.bat                # setup Windows (cmd.exe)
│   ├── run-backend.sh
│   ├── run-backend.ps1
│   ├── run-backend.bat
│   ├── run-frontend.sh
│   ├── run-frontend.ps1
│   └── run-frontend.bat
├── PLAN.md                      # roadmap aggiornata
└── CLAUDE.md                    # questo file
```

## Convenzioni di codice

- **Python**: PEP 8, type hints ovunque, docstring in formato Google
- **Naming**: `snake_case` per Python, `camelCase` per JS, `PascalCase` per componenti React e classi Python
- **Endpoint REST**: plurali, versionati (`/api/v1/items`)
- **Commit**: convenzione Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`)
- **Branch**: `main` stabile, lavoro in `feature/<nome>` o `module/<numero>`
- **Test**: pytest per backend, almeno un test per ogni endpoint
- **Dipendenze Python**: aggiunte sempre via `uv add <pkg>` (mai modificare `pyproject.toml` a mano per le dependency)

## Comandi uv di riferimento

```bash
uv sync                          # installa tutte le dipendenze del progetto
uv add fastapi uvicorn           # aggiunge una dipendenza runtime
uv add --dev pytest ruff         # aggiunge una dipendenza di sviluppo
uv remove <pkg>                  # rimuove una dipendenza
uv run <comando>                 # esegue un comando nel venv del progetto
uv run pytest                    # esegue i test
uv run uvicorn app.main:app --reload    # lancia il backend
uv python install 3.14           # installa una versione Python specifica
uv lock --upgrade                # aggiorna il lockfile
```

## Script di setup e avvio

Gli script vivono come file separati in `scripts/` — vedere quella cartella per i sorgenti. Convenzioni:

- **`setup.{sh,ps1,bat}`** — installano uv se mancante, eseguono `uv python install 3.14` e `uv sync` nel backend, e `npm install` nel frontend se presente
- **`run-backend.{sh,ps1,bat}`** — lanciano `uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
- **`run-frontend.{sh,ps1,bat}`** — lanciano `npm run dev` nel frontend

Note per Claude Code quando crea/modifica questi script:
- usare `set -euo pipefail` (bash) e `$ErrorActionPreference = "Stop"` (PowerShell) per fail-fast
- in `.bat` controllare `errorlevel` dopo i comandi critici
- nei `run-*` script usare path relativi alla posizione dello script (`$(dirname "$0")`, `$PSScriptRoot`, `%~dp0`), non al cwd
- non duplicare la documentazione di questi script in `CLAUDE.md`: la fonte di verità sono i file in `scripts/`

### Quick start (per il README)

**macOS / Linux**
```bash
git clone <repo-url> closetai
cd closetai
chmod +x scripts/*.sh
./scripts/setup.sh
./scripts/run-backend.sh        # in un terminale
./scripts/run-frontend.sh       # in un altro terminale
```

**Windows (PowerShell)**
```powershell
git clone <repo-url> closetai
cd closetai
.\scripts\setup.ps1
.\scripts\run-backend.ps1
.\scripts\run-frontend.ps1
```

**Windows (cmd.exe / doppio click)**
```bat
git clone <repo-url> closetai
cd closetai
scripts\setup.bat
scripts\run-backend.bat
scripts\run-frontend.bat
```

Backend disponibile su `http://localhost:8000`, docs su `http://localhost:8000/docs`.
Frontend su `http://localhost:5173` (default Vite).

## Moduli funzionali

### Modulo 1 — Catalogazione capi (vision)
Upload foto → classificazione categoria, colore, pattern → embedding salvato.
Modello: CLIP o fashion-classifier pre-trained.
Output: record in DB con metadata.

### Modulo 2 — Wear log (tracking uso)
L'utente registra cosa indossa (manuale rapido, foto outfit, o detection automatica via specchio).
Calcolo cost-per-wear, identificazione capi "fantasma".

### Modulo 3 — Outfit recommender
Da capi posseduti → combinazioni nuove, condizionate da meteo, calendario, diversificazione.
Approccio MVP: regole su compatibilità cromatica + similarità embedding.

### Modulo 4 — Diagnosi e azioni circolari
Vision model rileva difetti → suggerisce riparazione / swap / vendita / riciclo.
Stima CO₂ evitata per ogni capo "salvato".

### Modulo 5 — UI / specchio fisico
Web app responsive, eventuale prototipo specchio con Raspberry Pi.
Try-on generativo come estensione (IDM-VTON o simili).

### Modulo 6 — Dashboard impatto
Visualizzazione metriche di sostenibilità personali e aggregate.

## Roadmap suggerita (vedi PLAN.md per lo stato aggiornato)

**Fase 1 — Scheletro (settimana 1)**
- Setup repo, FastAPI con CRUD `items`, frontend con upload foto e lista
- Classificazione mock (placeholder che restituisce categoria casuale)

**Fase 2 — Vision reale (settimana 2)**
- Integrazione CLIP o fashion classifier
- Estrazione categoria + colore + embedding salvato

**Fase 3 — Wear log + cost-per-wear (settimana 3)**
- Endpoint registrazione utilizzo, calcolo metriche
- UI dashboard semplice

**Fase 4 — Recommender (settimana 4)**
- Suggerimento outfit basato su regole + embedding
- Integrazione meteo

**Fase 5 — Modulo circolare (settimana 5)**
- Diagnosi difetti, suggerimenti azioni, stima CO₂

**Fase 6 — Polish e demo (settimana 6)**
- UI/UX rifinita (qui usare AI generativa per design)
- Prototipo specchio se tempo lo consente
- Presentazione e metriche di impatto

## Vincoli e scelte deliberate

- **Niente autenticazione complessa per l'MVP** — single-user locale, OAuth solo se richiesto in seguito
- **Niente cloud storage in MVP** — tutto locale per ridurre problemi privacy
- **Inference on-device dove possibile** — se un modello gira accettabilmente via ONNX/CoreML/TFLite, preferire quella via
- **Dataset**: DeepFashion2 e Fashionpedia come riferimento; attenzione al bias (sbilanciato su moda occidentale, femminile, taglie standard) — documentare la limitazione
- **uv come unico gestore Python**: non mescolare con pip, conda, poetry; il lockfile (`uv.lock`) è la fonte di verità

## Cosa Claude Code dovrebbe fare di default

- Proporre slice verticali end-to-end, non layer separati
- Usare sempre `uv add` / `uv sync` / `uv run` per gestire Python (mai `pip install` diretto)
- Scrivere test per ogni endpoint nuovo (`uv run pytest`)
- Aggiornare `PLAN.md` quando completa step significativi
- Segnalare quando una scelta tecnica ha implicazioni di privacy o sostenibilità
- Preferire dipendenze stabili e ben mantenute; segnalare se sta introducendo qualcosa di esotico
- Chiedere conferma prima di modifiche strutturali grandi (rinominare moduli, cambiare DB, riorganizzare cartelle)

## Riferimenti utili

- uv docs: https://docs.astral.sh/uv/
- Ellen MacArthur Foundation — circular economy in fashion
- DeepFashion2: https://github.com/switchablenorms/DeepFashion2
- Fashionpedia dataset
- OpenCLIP: https://github.com/mlfoundations/open_clip
- IDM-VTON (try-on diffusion): https://github.com/yisol/IDM-VTON
