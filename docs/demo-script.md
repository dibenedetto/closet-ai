# Demo script — ClosetAI

> Scaletta operativa per la **demo finale** del corso (durata target 8-10
> minuti). Pensata per due persone: un *demo driver* che clicca, un *narrator*
> che racconta. Funziona benissimo anche con una sola persona.

---

## Preparazione (5 minuti prima)

1. Avvia i due server in due terminali separati:

   ```powershell
   .\scripts\run-backend.ps1      # PowerShell
   .\scripts\run-frontend.ps1
   ```

2. **(Opzionale, fortemente consigliato per la demo)** Popola il guardaroba
   con dati realistici:

   ```powershell
   cd backend
   uv run python scripts/seed_demo.py --reset
   ```

   In ~20 secondi crea 12 capi con immagini placeholder colorate, 158
   utilizzi distribuiti sugli ultimi 90 giorni, e un paio di azioni
   circolari di esempio. Stampa anche le stats finali.

3. Apri **due tab** nel browser:
   - <http://localhost:5173> — UI principale
   - <http://localhost:8000/docs> — Swagger UI (in caso serva mostrare un endpoint dal vivo)

---

## Scaletta (8-10 minuti)

> **Filo narrativo** — la presentazione ufficiale
> (`docs/ClosetAI-esame-ufficiale.pptx`) racconta
> il **ciclo di vita di un capo** in 6 tappe, ognuna con doppia lente
> 👤 utente / ⚙️ tecnico. La demo live segue le stesse tappe: mostra la
> slide, poi fai l'azione corrispondente nell'app.
>
> | Tappa (slide) | Storia | Demo live |
> | --- | --- | --- |
> | 1 · «L'ho comprato» | lo fotografo → riconoscimento | §1–2 (guardaroba + aggiungi capo) |
> | 2 · «L'ho indossato» | tracking uso | §3 (wear log + cost-per-wear) |
> | 3 · «Cosa metto oggi?» | recommender | §4 (`/today`) |
> | 4 · «Si è rovinato» | diagnosi stato | §6 (modulo circolare) |
> | 5 · «Mi serve altro?» | gap analysis | §5 (dashboard → card "Analisi guardaroba") |
> | 6 · «Lo lascio andare» | azione circolare + CO₂ | §6 (esegui azione) → §5 (impatto) |
>
> Ricorda il **codice colore delle 4 nature** (slide legenda + pipeline):
> 🟦 pre-addestrata (Fashion-CLIP) · 🟩 nostra (stato, gap) · 🟪 generativa
> (descrizioni, try-on) · 🟨 regole (cost-per-wear, CO₂).

### 0. Apertura (30s)

> "Ogni anno in Europa buttiamo via 5 milioni di tonnellate di vestiti,
> spesso senza averli indossati. ClosetAI è un prototipo che cerca di
> ridurre questo numero per la singola persona, combinando catalogazione
> automatica, tracking dell'uso reale e azioni circolari guidate."

### 1. Guardaroba (1 minuto) — `/`

- Mostra l'**hero banner** in alto: 12 capi attivi, 158 utilizzi, 2
  fantasma, cost-per-wear medio.
- Scorri la griglia: ogni card ha foto, nome, categoria + colore (estratti
  automaticamente dal classificatore Fashion-CLIP), prezzo.
- Usa il filtro per **categoria** (es. "jeans") o la barra di ricerca.
- Mostra il pulsante "✓ oggi" su una card → "Registra che l'ho indossato
  con un click."

### 2. Aggiungi un capo (1 minuto) — `/items/new`

- Clicca "Aggiungi capo", carica un'immagine. Compila solo il **nome**.
- Anteprima dell'immagine appare istantanea.
- Submit → la card del capo appare con **categoria e colore auto-dedotti
  da Fashion-CLIP**.
- Apri il dettaglio del capo appena creato: mostra **confidenza %** del
  classificatore (badge colorato).

### 3. Wear log + cost-per-wear (1 minuto) — dettaglio capo

- Apri un capo molto indossato (es. "T-shirt bordeaux", 30 utilizzi).
- Scorri lo storico utilizzi.
- Mostra **cost-per-wear**: € 0,66.
- Apri un *capo fantasma* dalla home (badge rosso "fantasma"):
  cost-per-wear assente, suggerimento di azione.

### 4. Cosa metto oggi? (1.5 minuti) — `/today`

- Mostra il **meteo del giorno** in alto (icona + temperatura + vento).
- Mostra le 3 proposte: ogni outfit ha
  - thumbnails dei capi,
  - **breakdown** colore + meteo (barre orizzontali),
  - rationale ("colori: blu, beige; leggero per il caldo; …").
- Spiega il punteggio: **regole** sulla compatibilità cromatica (HSL) +
  matching meteo (Open-Meteo) + bonus per capi mai indossati.
- Clicca **👍** per dare un feedback (verrà ricordato per future
  iterazioni).
- (Opzionale) Clicca **"Indosso questo"**: registra in un colpo il wear
  log per tutti i capi dell'outfit.

### 5. Dashboard impatto (1.5 minuti) — `/dashboard`

- Mostra le card riassuntive: capi totali, utilizzi, fantasma, investimento,
  cost-per-wear medio.
- Scorri la sezione **"🌱 Sostenibilità in pratica"**:
  > "Hai evitato 35 kg di CO₂. È come 195 km in auto risparmiati, 0.44
  > voli Pisa-Roma evitati, o quanto assorbono 4.4 m² di foresta in un
  > anno."
- Mostra la sezione "Azioni circolari per tipo" con il **bar chart CSS**.
- Top capi più indossati / lista capi fantasma → invita a controllare il
  guardaroba prima del prossimo acquisto.

### 6. Modulo circolare (1.5 minuti) — dettaglio di un capo "usurato"

- Apri il dettaglio della **giacca denim** (seedata come `usurato`).
- Mostra la sezione "Azioni circolari": dropdown condition + suggerimenti
  in ordine di priorità ("riparazione" prima per un capo usurato), con
  **stima CO₂ evitata** per ciascuno.
- Esegui un'azione: appare nello storico e aggiorna le stats.

### 7. Chiusura (30s)

- Riassumi: due ruoli AI:
  - **Machine learning applicato**: Fashion-CLIP pre-addestrato
    (classificazione + embedding), MLP dello stato e MLP dei gap addestrati da
    noi; regole color+meteo+feedback per il recommender.
  - **AI generativa**: descrizioni capi, coach sostenibilità, try-on
    virtuale, supporto AI in fase di design UI.
- Sostenibilità "misurabile" — ogni feature popola una metrica concreta.
- Modularità: 6 moduli funzionali (M1-M6) assegnabili a sottogruppi del
  corso.

---

## Plan B se qualcosa non va

| Problema                                 | Workaround                                                                          |
| ---------------------------------------- | ----------------------------------------------------------------------------------- |
| Fashion-CLIP non scarica i pesi (offline)| Imposta `CLOSETAI_CLASSIFIER=mock` prima di avviare il backend → il classifier mock continua a popolare category/color con euristica. |
| Open-Meteo irraggiungibile               | `/today` mostra meteo "mite" di fallback (18°C, no pioggia) — il banner lo segnala. |
| ChromaDB lentissimo all'avvio            | Cancella `data/chroma/` → si rigenera vuoto al prossimo POST.                       |
| Frontend non si connette                 | Verifica che il backend sia up con `curl http://localhost:8000/api/v1/health`.      |

---

## File di riferimento per la demo

- [README.md](../README.md) — quick start
- [PROJECT.md](../PROJECT.md) — scheda di progetto completa
- [PLAN.md](../PLAN.md) — roadmap e stato dei task
- [docs/api.md](api.md) — riferimento API
- [docs/architecture.md](architecture.md) — ADR e decisioni tecniche
- [backend/scripts/seed_demo.py](../backend/scripts/seed_demo.py) — seed dei dati di demo
