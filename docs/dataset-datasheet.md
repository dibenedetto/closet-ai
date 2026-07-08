# Datasheet — Garment Condition Dataset

> Scheda del dataset per la **diagnosi dello stato di conservazione** dei
> capi, secondo lo schema *Datasheets for Datasets* (Gebru et al., 2018).
> Generato da [`backend/scripts/build_condition_dataset.py`](../backend/scripts/build_condition_dataset.py).

---

## 1 · Motivazione

**Perché esiste questo dataset?**
ClosetAI vuole diagnosticare dalla **foto** di un capo il suo stato di
conservazione (`buono` / `usurato` / `danneggiato`) e suggerire
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
| `condition`  | **etichetta target**: buono / usurato / danneggiato               |
| `defect`     | difetto principale (scolorimento, pilling, macchia, strappo, buco) o vuoto |
| `severity`   | gravità della degradazione applicata, 0.0–1.0                    |
| `split`      | train / val / test (70 / 15 / 15, stratificato per stato)        |

**Bilanciamento**: per costruzione le 3 classi sono bilanciate
(default 60 immagini/classe → 180 totali; configurabile con `--per-class`).

**Formati di output**:
- `images/{stato}/*.png` — le immagini
- `manifest.csv` — tabella di etichette
- `preview.png` — griglia di anteprima (un esempio per stato)

---

## 3 · Processo di raccolta / generazione

Il dataset è **semi-sintetico**: partiamo da immagini di capi in buono
stato e applichiamo **degradazioni controllate** che simulano l'usura.
È una tecnica standard quando i dati etichettati scarseggiano (data
augmentation per *damage simulation*).

**Sorgenti delle immagini** (in ordine di preferenza, auto-rilevate):

1. **Dataset COCO di difetti reali** (consigliato) —
   `ml/datasets/Defect-Clothes.v3i.coco/` (Roboflow "Defect-Clothes",
   CC BY 4.0, ~1480 foto). Modalità **ibrida**:
   - `danneggiato` ← foto con **difetti veri annotati** (cut→strappo,
     hole→buco, stain→macchia): niente sintesi, etichetta dal COCO;
   - `buono` ← foto reali pulite (metà intatte, metà con lievi pieghe);
   - `usurato` ← foto pulite + fading/pilling sintetici (il COCO non ha la
     classe "consumato").
   Disattivabile con `--no-coco`.
2. `ml/datasets/source/` — capi puliti da degradare (foto proprie oppure
   output di [`fetch_real_garments.py`](../backend/scripts/fetch_real_garments.py),
   che ricolora silhouette FashionMNIST).
3. Bootstrap sintetico — sagome PIL, solo per validare la pipeline.

**Workflow consigliato** (con il COCO scaricato):

```bash
cd backend
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

- **Approccio A** (adottato): addestrare una testa di classificazione
  leggera sopra gli embedding di Fashion-CLIP (foto → embedding → stato).
- **Approccio B** (non esplorato): fine-tuning di una CNN
  (ResNet/EfficientNet) per la classificazione dello stato.

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

> **Baseline misurate** (Approccio A, MLP su embedding Fashion-CLIP):
>
> | Sorgente dataset                    | Test acc | Note                                |
> | ----------------------------------- | -------- | ----------------------------------- |
> | Sagome disegnate (bootstrap)        | ~0.94    | sovrastima: degradazioni "facili"   |
> | Silhouette FashionMNIST ricolorate  | ~0.96    | idem                                |
> | **COCO difetti reali (ibrido)**     | **~0.60 globale, ma F1 0.95 su `danneggiato`** | il numero onesto |
>
> Il passaggio alle foto reali **rende visibile il domain gap** previsto:
> l'accuracy globale crolla da 0.96 a 0.60, ma la classe che conta di più
> (`danneggiato`, con difetti **veri**) è riconosciuta al 95%, e `usurato`
> al 100% di recall. La confusione è concentrata in `nuovo ↔ buono`: due
> classi di foto pulite reali distinte solo da pieghe sintetiche leggere —
> un confine **artificiale del nostro labeling**, non un limite del modello.
> **Decisione presa**: le due classi sono state FUSE in `buono` — con lo
> schema a 3 classi oneste, sulla stessa base reale, il modello raggiunge
> **test accuracy ~0.94** (danneggiato F1 0.98, precision 1.00).
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

## 6.bis · Dataset secondario — Wardrobe Gap Analysis

Oltre al dataset di immagini per lo stato del capo, il progetto usa un
**secondo dataset tabellare** per la *gap analysis* del guardaroba (ADR-011).

- **Generatore**: [`scripts/build_wardrobe_dataset.py`](../backend/scripts/build_wardrobe_dataset.py)
- **Output**: `ml/datasets/wardrobe/wardrobe_dataset.csv`
- **Una riga = un guardaroba simulato**: 14 feature aggregate (conteggi per
  ruolo, frazioni, colori, ghost-ratio) + 6 label binarie (vuoti
  funzionali) + profilo.
- **Categorie ispirate a DeepFashion**: la tassonomia dei capi riprende le
  categorie/attributi di DeepFashion; i guardaroba sono **simulati** da
  profili (minimal / balanced / tshirt_heavy / summer_only / formal /
  random), non estratti da utenti reali.
- **Etichette**: prodotte da regole esperte (`gap_model.rule_based_gaps`)
  con rumore di etichettatura (default 8%), così la rete apprende le soglie
  invece di copiarle.
- **Modello**: MLP multi-label (vedi `train_gap_model.py`). Metriche
  baseline: Micro-F1 ~0.94, Hamming loss ~0.04.

**Limite**: come per il dataset immagini, i dati sono **sintetici**. La rete
è valida quanto le regole con cui sono stati generati i target; per superare
questo limite servirebbe il feedback reale degli utenti sui suggerimenti
d'acquisto (segnale che il prototipo non raccoglie ancora).

---

## 7 · Note etiche

- Nessun dato personale: le immagini sono di capi, non di persone.
- Se in futuro si raccolgono foto reali di guardaroba di utenti, applicare
  il principio *privacy by design* del progetto (consenso, no volti, no
  metadati di geolocalizzazione).
