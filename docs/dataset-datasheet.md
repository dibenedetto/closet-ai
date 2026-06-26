# Datasheet — Garment Condition Dataset

> Scheda del dataset per la **diagnosi dello stato di conservazione** dei
> capi, secondo lo schema *Datasheets for Datasets* (Gebru et al., 2018).
> Generato da [`backend/scripts/build_condition_dataset.py`](../backend/scripts/build_condition_dataset.py).

---

## 1 · Motivazione

**Perché esiste questo dataset?**
ClosetAI vuole diagnosticare dalla **foto** di un capo il suo stato di
conservazione (`nuovo` / `buono` / `usurato` / `danneggiato`) e suggerire
un'azione (riparare, donare, riciclare). Per addestrare un modello che lo
faccia, serve un dataset di immagini etichettate per stato d'usura.

**Perché lo costruiamo noi?**
Non esiste un dataset pubblico con questa etichettatura. I dataset fashion
standard (DeepFashion2, Fashionpedia, Fashion Product Images, FashionMNIST)
etichettano categoria, colore, attributi — **mai lo stato di usura**.

---

## 2 · Composizione

| Campo        | Descrizione                                                       |
| ------------ | ---------------------------------------------------------------- |
| `filename`   | percorso relativo dell'immagine                                  |
| `category`   | categoria del capo (t-shirt, jeans, vestito, …)                  |
| `color`      | colore dominante                                                 |
| `condition`  | **etichetta target**: nuovo / buono / usurato / danneggiato      |
| `defect`     | difetto principale (scolorimento, pilling, macchia, strappo, buco) o vuoto |
| `severity`   | gravità della degradazione applicata, 0.0–1.0                    |
| `split`      | train / val / test (70 / 15 / 15, stratificato per stato)        |

**Bilanciamento**: per costruzione le 4 classi sono bilanciate
(default 60 immagini/classe → 240 totali; configurabile con `--per-class`).

**Formati di output**:
- `images/{stato}/*.png` — le immagini
- `manifest.csv` — tabella di etichette
- `vlm_dataset.jsonl` — formato instruction-tuning per Visual-LLM (LoRA):
  ogni riga è `{image, messages:[user→<image>+istruzione, assistant→JSON
  con stato+difetto+tutorial]}`. Due varianti dei **target**:
  - **hardcoded** (default): il tutorial viene dalla knowledge base
    ([`repair_tutorials.py`](../backend/app/services/repair_tutorials.py)) —
    verificato ma fisso (8 tutorial, identici per ogni capo dello stesso
    difetto).
  - **distillato** (`vlm_dataset_distilled.jsonl`): il tutorial è generato
    da un **VLM grande** che guarda la foto
    ([`scripts/distill_tutorials.py`](../backend/scripts/distill_tutorials.py)),
    quindi **personalizzato** su colore, posizione ed entità del danno. Un
    campione dimostrativo è in `vlm_dataset_distilled_sample.jsonl`.

  Esempio (stesso capo — pantaloni blu con strappo):

  | | `difetto` | `tutorial` (estratto) |
  | --- | --- | --- |
  | hardcoded | `strappo` | "Riparare uno strappo con cucitura nascosta. 1) Stira… 2) Allinea…" |
  | distillato | "strappo netto e diagonale … sulla gamba destra" | "Questi pantaloni blu hanno uno strappo … zona ad alta tensione: applica una toppa termoadesiva sul retro, poi punto scala con filo blu…" |
- `preview.png` — griglia di anteprima (un esempio per stato)

---

## 3 · Processo di raccolta / generazione

Il dataset è **semi-sintetico**: partiamo da immagini di capi in buono
stato e applichiamo **degradazioni controllate** che simulano l'usura.
È una tecnica standard quando i dati etichettati scarseggiano (data
augmentation per *damage simulation*).

**Sorgenti delle immagini base** (in ordine di preferenza):

1. `ml/datasets/source/` — immagini di capi puliti. Si possono popolare in
   due modi:
   - **FashionMNIST** (consigliato, automatico): lo script
     [`fetch_real_garments.py`](../backend/scripts/fetch_real_garments.py)
     scarica FashionMNIST (70k foto reali di capi, 10 categorie), estrae le
     silhouette, le ricolora preservando ombre/pieghe reali e le salva qui.
     Forme **reali e varie**, non disegnate a mano.
   - **Foto proprie**: l'utente mette le sue foto di capi (jpg/png/webp).
     La modalità ideale per il training finale.
2. Bootstrap sintetico — se la cartella è vuota, lo script disegna sagome
   stilizzate di capi con PIL. Serve solo a validare la pipeline; **non** è
   adatto al training finale (sono icone, non foto).

**Workflow consigliato**:

```bash
cd backend
uv run python scripts/fetch_real_garments.py --count 240   # popola source/
uv run python scripts/build_condition_dataset.py --per-class 150
uv run python scripts/train_condition_model.py --no-cache
```

**Degradazioni implementate** (parametri randomizzati per severità):

| Funzione           | Effetto                                | Usata per       |
| ------------------ | -------------------------------------- | --------------- |
| `apply_fading`     | sbiadimento (desaturazione + schiarisce) | usurato, danneggiato |
| `apply_pilling`    | micro-pallini granulari a chiazze      | usurato         |
| `apply_wrinkles`   | pieghe (bande d'ombra)                 | tutti tranne nuovo |
| `apply_stain`      | macchia (blob scuro semitrasparente)   | danneggiato     |
| `apply_tear`       | strappo (linea che apre il tessuto)    | danneggiato     |
| `apply_hole`       | buco (ellisse colore sfondo)           | danneggiato     |

Mappatura stato → degradazioni:

- **nuovo** → nessuna (micro-pieghe trascurabili)
- **buono** → lievi pieghe + leggerissimo sbiadimento
- **usurato** → sbiadimento marcato + pilling + pieghe
- **danneggiato** → 1 difetto forte (macchia / strappo / buco) + sbiadimento

Seed fisso (`--seed 42`) → generazione **riproducibile**.

---

## 4 · Usi previsti

- **Approccio A**: addestrare una testa di classificazione leggera sopra
  gli embedding di Fashion-CLIP (foto → embedding → stato).
- **Approccio B**: fine-tuning di una CNN (ResNet/EfficientNet) per la
  classificazione dello stato.
- **Approccio C**: fine-tuning con LoRA di un Visual-LLM usando
  `vlm_dataset.jsonl`, per output strutturato {stato, tutorial}.

**Usi sconsigliati**: qualsiasi conclusione su capi reali senza prima
ri-generare il dataset a partire da **foto reali** (vedi limiti sotto).

---

## 5 · Limiti e bias

- **Degradazione sintetica**: anche partendo da forme reali (FashionMNIST),
  l'**usura** è simulata algoritmicamente, non fotografata da capi
  realmente consumati. Un modello addestrato così riconosce bene le
  *degradazioni che gli abbiamo insegnato*, ma il vero banco di prova sono
  foto di usura reale (domain gap residuo).
- **FashionMNIST è 28×28 grayscale** all'origine: pur upscalato e
  ricolorato, manca della ricchezza di una foto ad alta risoluzione.
- **Bootstrap = icone**: in assenza totale di immagini sorgente, le basi
  sono sagome stilizzate, ancora più lontane da foto reali.

> Baseline misurate (Approccio A, MLP su embedding Fashion-CLIP):
> ~0.94 test accuracy con basi sintetiche disegnate, ~0.96 con basi reali
> FashionMNIST. Entrambe **sovrastimano** la performance su foto di usura
> reale, perché le degradazioni di test sono dello stesso tipo di quelle di
> training.
- **Bias di categoria/colore**: distribuzione uniforme artificiale, non
  rappresentativa di un guardaroba reale.
- **Difetti semplificati**: un solo difetto dominante per immagine
  danneggiata; la realtà è più sfumata e multi-difetto.
- **Eredita i bias di Fashion-CLIP** se usato come feature extractor
  (moda prevalentemente occidentale).

**Mitigazione raccomandata**: raccogliere anche solo 100–300 foto reali di
capi in stati diversi e ri-generare il dataset con quelle come sorgente,
mantenendo le degradazioni sintetiche come *augmentation*.

---

## 6 · Manutenzione

- **Riproduzione**: `uv run python scripts/build_condition_dataset.py --per-class N`
- **Con foto reali**: popolare `ml/datasets/source/` e rilanciare.
- Le immagini generate **non** sono versionate in git (vedi `.gitignore`):
  si rigenerano dallo script. Lo script e questa datasheet sì.

---

## 7 · Note etiche

- Nessun dato personale: le immagini sono di capi, non di persone.
- Se in futuro si raccolgono foto reali di guardaroba di utenti, applicare
  il principio *privacy by design* del progetto (consenso, no volti, no
  metadati di geolocalizzazione).
