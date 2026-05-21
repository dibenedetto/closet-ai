# ClosetAI — Scheda di progetto

> Documento di presentazione del progetto. Per la roadmap operativa e lo stato dei
> task vedi [PLAN.md](PLAN.md); per le convenzioni di codice e le istruzioni
> tecniche vedi [CLAUDE.md](CLAUDE.md).

---

## 1. In breve

**ClosetAI** è un prototipo di applicazione (con possibile estensione hardware
sotto forma di "specchio smart") che **digitalizza il guardaroba** dell'utente,
ne **traccia l'uso reale** e usa l'intelligenza artificiale per
**massimizzare il valore dei capi posseduti**, riducendo gli acquisti impulsivi
e favorendo riparazione, scambio e rivendita.

Il sistema dimostra l'AI in due ruoli distinti:

- **Machine learning applicato** come componente funzionale del prodotto:
  classificazione capi, recommendation di outfit, diagnosi difetti.
- **AI generativa** come supporto al design e all'esperienza: UI/UX,
  tutorial, try-on virtuale.

Progetto didattico realizzato per il corso di **Virtual Worlds** del
**Master in Informatica per la Salute Digitale** dell'**Università di Pisa**.

---

## 2. Il problema

L'industria della moda è una delle più impattanti del pianeta dal punto di vista
ambientale: produce circa il 10% delle emissioni globali di CO₂, è la seconda
consumatrice di acqua, e ogni anno milioni di tonnellate di tessuti finiscono in
discarica. Una parte sostanziale di questo impatto è imputabile al
**fast fashion**: acquisti frequenti, capi indossati poche volte, vita media del
capo molto inferiore al suo potenziale.

A livello individuale i comportamenti più comuni sono:

- **Acquisto impulsivo** — non si ha una visione chiara di ciò che già si possiede.
- **Capi "fantasma"** — vestiti dimenticati nell'armadio e mai indossati dopo
  l'acquisto.
- **Smaltimento prematuro** — un capo viene buttato invece di essere riparato,
  ceduto, donato o riciclato.

Gli strumenti digitali esistenti coprono di solito **uno solo** di questi assi
(catalogazione *oppure* tracking *oppure* marketplace second-hand), senza
collegarli a una metrica di impatto né a un suggerimento di azione concreto.

---

## 3. La soluzione proposta

ClosetAI propone un flusso unico che integra catalogazione, tracking d'uso e
azioni circolari, supportato da modelli AI per ridurre l'attrito su ciascun passo.

Flusso utente di riferimento:

1. **Catalogazione** — l'utente fotografa un capo; un classificatore vision
   identifica categoria, colore e produce un embedding del capo.
2. **Wear log** — l'utente registra cosa indossa (manualmente, da foto outfit
   o, in futuro, automaticamente tramite lo specchio); il sistema calcola
   *cost-per-wear* e identifica i capi fantasma.
3. **Recommendation** — su richiesta ("cosa metto oggi?"), il sistema propone
   combinazioni a partire dai capi posseduti, condizionate da meteo e calendario.
4. **Azione circolare** — periodicamente o su richiesta, il sistema diagnostica
   lo stato dei capi e suggerisce **riparazione, scambio, vendita o riciclo**,
   stimando la CO₂ evitata per ogni capo "salvato".
5. **Dashboard impatto** — l'utente vede le sue metriche di sostenibilità
   personali e può confrontarle con benchmark aggregati.

L'**estensione hardware** opzionale è uno specchio smart (Raspberry Pi + monitor
verticale + camera) installabile in camera da letto: cattura outfit, mostra
proposte, dialoga con l'app mobile.

---

## 4. Ruolo dell'AI

Il progetto è esplicitamente costruito per esibire **due ruoli distinti**
dell'AI, soddisfacendo i requisiti didattici del corso.

### 4.1 Machine learning applicato (componente funzionale)

- **Classificazione capi** — CLIP o classificatore fashion pre-trained
  (`fashion-clip`, `valhalla/fashion-clip`, ecc.) per dedurre categoria,
  attributi e generare embedding.
- **Estrazione colore dominante** — k-means su pixel o palette estraction.
- **Outfit recommender** — regole di compatibilità cromatica + similarità su
  embedding per garantire varietà.
- **Diagnosi difetti** — vision classifier su poche classi (nuovo, buono,
  usurato, danneggiato).
- **Detection automatica outfit** — multi-label detection da foto, per il
  wear log automatico.

### 4.2 AI generativa (supporto al design e all'esperienza)

- **Progettazione UI/UX** con strumenti tipo v0, Figma AI.
- **Tutorial di riparazione** generati da LLM personalizzati sul capo.
- **Try-on virtuale** tramite modelli diffusion (es. IDM-VTON).
- **Asset visivi** per la demo e la documentazione.

---

## 5. Architettura tecnica

### 5.1 Stack

| Layer        | Tecnologie                                                                |
| ------------ | ------------------------------------------------------------------------- |
| Backend      | Python 3.14, FastAPI, SQLAlchemy 2, SQLite (Postgres in produzione)       |
| Package mgmt | [uv](https://docs.astral.sh/uv/) — venv + dipendenze + lockfile           |
| ML           | PyTorch, HuggingFace transformers, OpenCLIP; ONNX per export on-device    |
| Frontend     | React + Vite + TypeScript (web); React Native come estensione mobile      |
| Storage      | Filesystem locale per immagini, SQLite per metadata (MVP)                 |
| Specchio     | Raspberry Pi 5 + monitor verticale + camera (opzionale)                   |

### 5.2 Struttura del repository

```
closet-ai/
├── backend/      # API FastAPI + servizi + wrapper modelli ML
│   └── app/
│       ├── models/   # SQLAlchemy
│       ├── routers/  # endpoint per dominio
│       ├── schemas/  # Pydantic I/O
│       ├── services/ # logica di business
│       └── ml/       # wrapper inferenza modelli
├── frontend/     # web app React/Vite/TS
├── ml/           # notebook esplorazione e pesi (weights/ gitignored)
├── data/         # storage locale foto e DB SQLite (gitignored)
├── docs/         # architettura, API, decisioni tecniche
├── scripts/      # setup e run per macOS/Linux/Windows
├── CLAUDE.md     # istruzioni per Claude Code e convenzioni
├── PLAN.md       # roadmap operativa e stato dei task
├── PROJECT.md    # questo documento
└── README.md     # quick start
```

### 5.3 Principi guida

1. **MVP first** — slice verticali end-to-end prima di approfondire i singoli
   layer; il primo obiettivo è "carico foto → la vedo nella lista".
2. **Privacy by design** — foto di utenti sono sensibili (camera da letto, corpo).
   Preferenza per inference on-device, niente upload in cloud per l'MVP, niente
   storage di immagini grezze su server di terzi.
3. **Pre-trained > training from scratch** — per l'MVP si usano modelli
   HuggingFace già addestrati; il fine-tuning è un'estensione opzionale.
4. **Misurabilità della sostenibilità** — ogni feature deve poter essere
   collegata a una metrica di impatto (capi non acquistati, CO₂ evitata,
   utilizzi/capo).
5. **Modularità** — il progetto è suddivisibile in moduli assegnabili a
   sottogruppi di studenti.

---

## 6. Moduli funzionali

Il sistema è organizzato in **sei moduli** indipendenti ma integrati.
Ogni modulo può essere assegnato a un sottogruppo di lavoro.

| #  | Modulo                                  | Tecnologia chiave                            |
| -- | --------------------------------------- | -------------------------------------------- |
| M1 | Catalogazione capi (vision)             | CLIP / fashion-classifier pre-trained        |
| M2 | Wear log e cost-per-wear                | CRUD + analytics                             |
| M3 | Outfit recommender                      | Regole + embedding + API meteo               |
| M4 | Diagnosi e azioni circolari             | Vision classifier + tabella CO₂ + LLM        |
| M5 | UI / Specchio fisico                    | React + Vite; RPi5 + camera (opz.)           |
| M6 | Dashboard impatto                       | Aggregazione metriche + visualizzazioni      |

Vedi [CLAUDE.md](CLAUDE.md) per la descrizione di dettaglio di ciascun modulo.

---

## 7. Roadmap (sintesi)

| Fase | Settimana | Obiettivo                                              |
| ---- | --------- | ------------------------------------------------------ |
| 1    | 1         | Scheletro end-to-end: upload foto + lista, mock ML     |
| 2    | 2         | Vision reale (CLIP o fashion classifier) + embedding   |
| 3    | 3         | Wear log + cost-per-wear + capi fantasma               |
| 4    | 4         | Outfit recommender + meteo                             |
| 5    | 5         | Modulo circolare: diagnosi, azioni, stima CO₂          |
| 6    | 6         | Polish UI/UX (AI generativa), demo, eventuale specchio |

Dettaglio completo dei task e stato corrente: [PLAN.md](PLAN.md).

---

## 8. Metriche di impatto

Il successo del progetto **non** è misurato solo dalle funzionalità implementate,
ma anche da metriche di sostenibilità tracciabili. Per ogni feature ci si chiede:
*che metrica di impatto popola?*

Metriche perseguite:

- **Utilizzi per capo** (target: > 30 utilizzi nel ciclo di vita).
- **Cost-per-wear medio** del guardaroba.
- **Capi fantasma** (mai indossati dopo X giorni dall'acquisto).
- **Capi salvati** da azioni circolari (riparati, scambiati, venduti).
- **CO₂ evitata stimata** per capo salvato, basata su tabelle Ellen MacArthur.
- **Acquisti evitati** grazie a suggerimenti gap-analysis (estensione).

---

## 9. Vincoli e decisioni deliberate

Decisioni prese in fase di disegno, da non rimettere in discussione senza una
ragione esplicita:

- **Niente autenticazione complessa nell'MVP** — single-user locale. OAuth solo
  se richiesto in seguito.
- **Niente cloud storage nell'MVP** — tutto locale, riduce i problemi di
  privacy e semplifica il deployment per la demo.
- **Inference on-device quando possibile** — se un modello gira accettabilmente
  via ONNX/CoreML/TFLite, si privilegia quella via.
- **uv come unico gestore Python** — non si mescola con pip / conda / poetry.
  Il lockfile `uv.lock` è la fonte di verità.
- **Dataset di riferimento**: DeepFashion2 e Fashionpedia. Si documenta
  esplicitamente il bias (sbilanciamento su moda occidentale, femminile,
  taglie standard).

---

## 10. Limitazioni note

- **Bias dei dataset** disponibili: moda occidentale, prevalenza femminile,
  taglie standard. Un sistema deployato su utenti reali richiederebbe dataset
  più rappresentativi.
- **Stime di CO₂** basate su tabelle medie per categoria, non su LCA puntuali.
- **Privacy delle immagini**: pur scegliendo storage locale, una versione in
  produzione richiederebbe un'analisi DPIA seria.
- **Detection automatica** dell'outfit indossato da foto è soggetta a errori
  (occlusioni, sovrapposizioni, illuminazione).

---

## 11. Estensioni e ricerche aperte

- Modalità famiglia / guardaroba condiviso.
- Integrazione calendario per outfit basati su eventi.
- Notifiche per capi non indossati da X tempo.
- Export guardaroba in formato standard (migrazione tra app).
- Marketplace second-hand integrato (mock o link esterni).
- Gap analysis: suggerimenti d'acquisto **solo** se manca davvero qualcosa.
- Try-on generativo con diffusion (IDM-VTON o successori).

---

## 12. Divisione del lavoro suggerita

Il progetto è pensato per essere realizzato da più persone in parallelo.
Suggerimento di assegnazione (sostituibile in base alle competenze del gruppo):

- **Backend & DB** — uno o due studenti: API, modelli, persistenza.
- **ML & vision** — uno o due studenti: classificazione, embedding, diagnosi.
- **Frontend** — uno o due studenti: UI, integrazione API, UX.
- **Sostenibilità & metriche** — uno studente: tabelle CO₂, dashboard, ricerca.
- **Hardware / specchio** — opzionale, se compatibile con tempi e tempo libero.
- **AI generativa & design** — trasversale, può essere svolto da chiunque del
  gruppo con interesse specifico.

---

## 13. Riferimenti

- uv docs — https://docs.astral.sh/uv/
- FastAPI docs — https://fastapi.tiangolo.com/
- Ellen MacArthur Foundation — *A New Textiles Economy*
- DeepFashion2 — https://github.com/switchablenorms/DeepFashion2
- Fashionpedia — https://fashionpedia.github.io/
- OpenCLIP — https://github.com/mlfoundations/open_clip
- IDM-VTON — https://github.com/yisol/IDM-VTON

---

## 14. Contatti

Master in Informatica per la Salute Digitale — Università di Pisa.
Corso di Virtual Worlds — A.A. 2025/2026.
