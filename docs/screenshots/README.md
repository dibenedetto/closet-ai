# Screenshot della UI

Questa cartella contiene gli screenshot della web app linkati dal
[README.md](../../README.md) di progetto.

## File attesi

| File             | Pagina                          | Quando aggiornarlo                                  |
| ---------------- | ------------------------------- | --------------------------------------------------- |
| `01-home.png`    | Guardaroba (`/`)                | Cambiano griglia, card, toolbar                     |
| `02-add.png`     | Aggiungi capo (`/items/new`)    | Cambiano form upload, anteprima, validazioni        |
| `03-detail.png`  | Dettaglio capo (`/items/:id`)   | Cambiano layout dettaglio o metadata mostrati       |

## Come catturarli

1. Avvia entrambi i server in dev (vedi
   [scripts/run-backend.*](../../scripts) e [run-frontend.*](../../scripts)):

   - backend → http://localhost:8000
   - frontend → http://localhost:5173

2. Carica 4–6 capi di esempio dal form (immagini libere o quelle in
   [seed/](./seed/) se presenti). Questo popola la home con contenuto realistico.

3. Apri ciascuna pagina nel browser e cattura uno screenshot del viewport
   (tipicamente **1280×800**, scala 100%). Suggerimenti:

   - **Windows**: `Win + Shift + S` (Strumento di cattura).
   - **macOS**: `Cmd + Shift + 4`, poi spazio per catturare la finestra.
   - **Linux**: `gnome-screenshot -a` o tool equivalente.

4. Salva i file in questa cartella con i nomi della tabella sopra. Usa PNG
   (lossless, peso accettabile per UI prevalentemente piatta).

5. Verifica che le anteprime nel [README.md](../../README.md) si vedano
   correttamente.

## Convenzioni

- **Niente dati personali** negli screenshot (foto di capi reali identificabili,
  email, ecc.). Usare seed o foto neutre.
- **Niente PII** nella URL bar — catturare solo il viewport dell'app, non la
  finestra browser intera quando possibile.
- Quando si rifà uno screenshot, sovrascrivere il file esistente con lo stesso
  nome (così i link nel README restano validi).
