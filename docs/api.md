# API ClosetAI v1

> Documentazione di riferimento delle API HTTP. Tutte le rotte sono versionate
> sotto il prefisso **`/api/v1`**. La specifica OpenAPI auto-generata è anche
> disponibile su [`http://localhost:8000/docs`](http://localhost:8000/docs)
> (Swagger UI) e [`http://localhost:8000/redoc`](http://localhost:8000/redoc).

## Convenzioni

- **Base URL (dev)**: `http://localhost:8000/api/v1`
- **Content type**:
  - Risposte: `application/json` (eccetto `GET /items/{id}/image` → `image/*`).
  - Richieste con file: `multipart/form-data`.
- **Date e timestamp**:
  - `purchase_date` → stringa ISO `YYYY-MM-DD`.
  - `created_at` → stringa ISO-8601 con timezone UTC.
- **Identificatori**: `id` interi positivi assegnati dal DB (autoincrement).
- **Path immagine**: `image_path` nel record è il **nome file** (es. `8b7e…46.png`),
  servito tramite `GET /items/{id}/image`. La directory fisica
  (`data/items/`) **non** è raggiungibile direttamente.

### Formato errori

In caso di errore l'API restituisce un body JSON con campo `detail`:

```json
{ "detail": "Item 999 non trovato." }
```

Per errori di validazione FastAPI (status 422), `detail` è una lista
strutturata; vedere la sezione "Errori comuni" in fondo.

---

## Endpoint

### `GET /health`

Health check.

**Risposta `200`**

```json
{
  "status": "ok",
  "service": "closetai-backend",
  "time": "2026-05-21T17:08:01.612142Z"
}
```

**Esempio**

```bash
curl -s http://localhost:8000/api/v1/health
```

---

### `GET /items`

Lista paginata dei capi, ordinata per `created_at DESC`.

**Query string**

| nome    | tipo | default | vincoli       | descrizione         |
| ------- | ---- | ------- | ------------- | ------------------- |
| `skip`  | int  | `0`     | `>= 0`        | offset              |
| `limit` | int  | `50`    | `1..200`      | dimensione pagina   |

**Risposta `200`** — array di `Item`:

```json
[
  {
    "id": 12,
    "name": "T-shirt bordeaux",
    "category": "t-shirt",
    "color": "rosso",
    "image_path": "8b7e138a423f44668b45e27ff22d4146.png",
    "price": 19.9,
    "purchase_date": "2025-09-10",
    "created_at": "2026-05-21T17:08:01.612142Z"
  }
]
```

**Esempio**

```bash
curl -s "http://localhost:8000/api/v1/items?skip=0&limit=20"
```

---

### `GET /items/{id}`

Dettaglio di un singolo capo.

**Risposta `200`** — oggetto `Item` (vedi schema sopra).

**Risposta `404`** — `{"detail": "Item {id} non trovato."}`.

**Esempio**

```bash
curl -s http://localhost:8000/api/v1/items/12
```

---

### `POST /items`

Crea un nuovo capo: salva l'immagine in `data/items/`, registra il record,
e — **se `category` o `color` non sono passati** — invoca il classificatore
mock per popolarli automaticamente (`app/ml/classifier.py`).

**Content type**: `multipart/form-data`.

**Form fields**

| campo           | tipo   | obbl. | vincoli                                  |
| --------------- | ------ | ----- | ---------------------------------------- |
| `name`          | string | sì    | 1–200 caratteri                          |
| `category`      | string | no    | max 64. Vuoto → auto-popolato dal mock.  |
| `color`         | string | no    | max 32. Vuoto → auto-popolato dal mock.  |
| `price`         | number | no    | `>= 0`                                   |
| `purchase_date` | date   | no    | ISO `YYYY-MM-DD`                         |
| `image`         | file   | sì    | jpeg / png / webp, **max 10 MB**         |

**Risposta `201`** — oggetto `Item` appena creato.

**Risposta `400`** — formato/estensione non ammessi.
**Risposta `413`** — file più grande del limite.
**Risposta `422`** — payload non valido (es. `name` mancante).

**Esempio**

```bash
curl -s -X POST http://localhost:8000/api/v1/items \
  -F "name=T-shirt bordeaux" \
  -F "price=19.90" \
  -F "purchase_date=2025-09-10" \
  -F "image=@/percorso/foto.jpg"
```

---

### `PATCH /items/{id}`

Aggiorna parzialmente i metadati modificabili del capo. Il body è JSON e può
contenere `name`, `category`, `color`, `price` e `purchase_date`; i campi
omessi restano invariati. Un valore `null` rimuove un metadato facoltativo.

**Risposta `200`** — oggetto `Item` aggiornato.

**Risposta `404`** — item inesistente. **Risposta `422`** — nome vuoto/null,
prezzo negativo, valore troppo lungo o campo sconosciuto.

```bash
curl -s -X PATCH http://localhost:8000/api/v1/items/12 \
  -H "Content-Type: application/json" \
  -d '{"name":"T-shirt bordeaux preferita","price":null}'
```

---

### `DELETE /items/{id}`

Elimina il record DB **e** il file immagine dal disco.

**Risposta `204`** — nessun body.

**Risposta `404`** — item inesistente.

Se l'unlink del file fallisce (es. permessi, file già rimosso), l'API risponde
comunque `204`: il record DB è la fonte di verità, l'errore di filesystem
viene loggato lato server.

**Esempio**

```bash
curl -s -X DELETE http://localhost:8000/api/v1/items/12 -o /dev/null -w "%{http_code}\n"
```

---

### `GET /items/{id}/image`

Restituisce il file immagine dell'item.

**Risposta `200`** — il file binario con `Content-Type` appropriato
(`image/jpeg`, `image/png`, `image/webp`).

**Risposta `404`** — item inesistente, oppure record presente ma file mancante
sul disco (in tal caso `detail` contiene "mancante sul filesystem").

**Esempio**

```bash
curl -s http://localhost:8000/api/v1/items/12/image -o capo.jpg
```

---

### `POST /items/{id}/reclassify`

Ri-esegue la classificazione del capo: aggiorna `category`, `color`,
`classification_confidence` nel DB e l'embedding nella collection ChromaDB.
Utile dopo aver aggiornato il modello, modificato i prompt o caricato
un'immagine sotto stress (es. con sfondo non standard).

**Risposta `200`** — oggetto `Item` aggiornato.

**Risposta `404`** — item inesistente, o file immagine mancante sul disco.

**Risposta `400`** — item presente ma senza `image_path` associato.

**Esempio**

```bash
curl -s -X POST http://localhost:8000/api/v1/items/12/reclassify | jq .
```

```json
{
  "id": 12,
  "name": "T-shirt bordeaux",
  "category": "t-shirt",
  "color": "rosso",
  "image_path": "8b7e138a423f44668b45e27ff22d4146.png",
  "price": 19.9,
  "purchase_date": "2025-09-10",
  "classification_confidence": 0.83,
  "created_at": "2026-05-21T17:08:01.612142Z"
}
```

---

## Wear log e statistiche

### `POST /items/{item_id}/wear`

Registra un utilizzo del capo (un "wear event").

**Body** (JSON, opzionale):

```json
{ "worn_on": "2026-05-21", "occasion": "lavoro" }
```

| campo      | tipo   | obbl. | default      | note                          |
| ---------- | ------ | ----- | ------------ | ----------------------------- |
| `worn_on`  | date   | no    | oggi         | ISO `YYYY-MM-DD`              |
| `occasion` | string | no    | `null`       | max 64 caratteri              |

**Risposta `201`** — `WearEvent` creato.
**Risposta `404`** — item inesistente.
**Risposta `409`** — il capo è già in seconda vita e non può ricevere nuovi utilizzi.

---

### `GET /items/{item_id}/wears`

Lista cronologica (desc) degli eventi di utilizzo per il capo.

**Risposta `200`** — `WearEvent[]`.
**Risposta `404`** — item inesistente.

---

### `POST /wear-events/batch`

Registra più eventi in una transazione singola. Utile per inserimenti
massivi dall'app mobile o da uno specchio smart.

**Body**:

```json
{
  "events": [
    { "item_id": 12, "worn_on": "2026-05-20" },
    { "item_id": 12, "worn_on": "2026-05-21", "occasion": "ufficio" },
    { "item_id": 7 }
  ]
}
```

**Risposta `201`** — `WearEvent[]` (preserva l'ordine).
**Risposta `404`** — se almeno un `item_id` non esiste (la transazione viene annullata).

---

### `DELETE /wear-events/{event_id}`

Elimina un singolo wear event.

**Risposta `204` / `404`**.

---

### `GET /items/{item_id}/stats`

Statistiche del capo: count, ultimo utilizzo, cost-per-wear, flag fantasma.

**Query string**

| nome              | default | range  | descrizione                                    |
| ----------------- | ------- | ------ | ---------------------------------------------- |
| `ghost_after_days`| 30      | 1–365  | soglia per considerare il capo "fantasma"      |

**Risposta `200`** — `ItemStats`:

```json
{
  "item_id": 12,
  "wear_count": 4,
  "last_worn": "2026-05-15",
  "days_since_last_worn": 6,
  "cost_per_wear": 4.99,
  "is_ghost": false,
  "ghost_after_days": 30
}
```

---

### `GET /stats/wardrobe`

Statistiche aggregate sul guardaroba.

**Query string**

| nome              | default | range  | descrizione                            |
| ----------------- | ------- | ------ | -------------------------------------- |
| `ghost_after_days`| 30      | 1–365  | soglia fantasma                        |
| `top_n`           | 5       | 1–50   | dimensione classifica top-worn         |

**Risposta `200`** — `WardrobeStats`:

```json
{
  "total_items": 12,
  "total_wears": 47,
  "avg_wears_per_item": 3.92,
  "ghost_count": 2,
  "ghost_after_days": 30,
  "total_investment": 690.50,
  "avg_cost_per_wear": 12.30,
  "top_worn": [
    { "item_id": 12, "name": "T-shirt bordeaux", "wear_count": 8 }
  ]
}
```

---

### `GET /stats/ghosts`

Lista dei capi mai indossati e posseduti da almeno `ghost_after_days`
(default 30). Ordina dai più recenti aggiunti.

**Risposta `200`** — `GhostItem[]`:

```json
[
  {
    "item_id": 5,
    "name": "Maglione verde",
    "category": "maglione",
    "purchase_date": "2026-01-10",
    "days_owned": 131,
    "price": 49.90
  }
]
```

---

## Outfit recommender

### `GET /outfits/suggest`

Genera fino a `count` proposte di outfit per la data indicata, condizionate
dal meteo recuperato via Open-Meteo (con fallback se l'API non risponde).

**Query string**

| nome    | tipo  | default              | range                | descrizione                       |
| ------- | ----- | -------------------- | -------------------- | --------------------------------- |
| `date`  | date  | oggi                 | YYYY-MM-DD           | giorno per cui suggerire l'outfit |
| `count` | int   | 3                    | 1–10                 | numero proposte                   |
| `lat`   | float | `CLOSETAI_DEFAULT_LAT` (43.7228 = Pisa) | -90..90  | latitudine                      |
| `lon`   | float | `CLOSETAI_DEFAULT_LON` (10.4017 = Pisa) | -180..180 | longitudine                    |

**Risposta `200`** — `OutfitSuggestResponse`:

```json
{
  "target_date": "2026-05-22",
  "weather": {
    "target_date": "2026-05-22",
    "temperature_c": 18.5,
    "precipitation_mm": 0.0,
    "wind_kmh": 12.0,
    "weather_code": 1,
    "source": "open-meteo"
  },
  "outfits": [
    {
      "items": [
        { "id": 12, "name": "T-shirt blu", "category": "t-shirt", "color": "blu", ... }
      ],
      "score": 0.83,
      "color_score": 0.90,
      "weather_score": 0.85,
      "ghost_bonus": 0.08,
      "rationale": "colori: blu, nero; leggero per il caldo; contiene capi mai indossati"
    }
  ]
}
```

Lo score è
`0.55 * color_score + 0.35 * weather_score + ghost_bonus + preference_bonus`,
clamped a `[0, 1]`. `ghost_bonus` arriva a `0.15` e considera solo capi mai
indossati posseduti da almeno 30 giorni; `preference_bonus` vale
`0.04 * affinità_feedback_media` (quindi circa `-0.04..+0.04`). Se Open-Meteo
non risponde, `weather.source = "fallback"` e i valori sono valori "miti"
(~18°C, no pioggia).

**Esempio**

```bash
curl -s "http://localhost:8000/api/v1/outfits/suggest?count=3&date=2026-05-22" | jq .
```

---

### `POST /outfits/feedback`

Salva un like/dislike su una proposta di outfit. Il segnale entra con peso
leggero nel ranking delle proposte successive; non riaddestra un modello.

**Body**:

```json
{ "item_ids": [12, 7], "rating": 1, "occasion": "lavoro" }
```

| campo      | tipo       | obbl. | vincoli            |
| ---------- | ---------- | ----- | ------------------ |
| `item_ids` | int[]      | sì    | 1–10 elementi      |
| `rating`   | int        | sì    | `1` o `-1`         |
| `occasion` | string     | no    | max 64 caratteri   |

**Risposta `201`** — `OutfitFeedback`.
**Risposta `422`** — `rating=0` o array vuoto.

---

### `GET /outfits/feedback`

Lista cronologica (desc) dei feedback salvati. Query: `limit` (1–200, default 50).

---

## Modulo circolare (Fase 5)

### `POST /items/{item_id}/diagnose`

Diagnostica la condizione del capo (`buono`/`usurato`/`danneggiato` — "nuovo" è stato fuso in "buono", vedi ADR-009).
Usa il backend configurato da `CLOSETAI_CONDITION_BACKEND` (default `auto`:
prova l'MLP su Fashion-CLIP, poi l'euristica `wear_count` + età). Il campo
`source` indica quale backend ha risposto. Se l'item non aveva ancora una
`condition`, viene persistita. Restituisce anche la lista di azioni
circolari suggerite con stima CO₂.

**Risposta `200`** — `DiagnoseResponse`:

```json
{
  "item_id": 12,
  "condition": "usurato",
  "wear_count": 42,
  "days_owned": 540,
  "rationale": "42 utilizzi su 540 giorni: segni d'uso attesi",
  "source": "heuristic",
  "confidence": null,
  "suggestions": [
    {
      "action_type": "riparazione",
      "co2_saved_kg": 22.4,
      "rationale": "alcune riparazioni mirate possono prolungarne la vita",
      "priority": 1
    },
    { "action_type": "donazione", "co2_saved_kg": 32.0, "rationale": "…", "priority": 2 }
  ]
}
```

---

### `PUT /items/{item_id}/condition`

Override manuale della condizione. Body: `{"condition": "danneggiato"}`.
Risposta `200`: stesso shape di `/diagnose`.

---

### `POST /items/{item_id}/actions`

Registra l'esecuzione di un'azione circolare. Body:

```json
{ "action_type": "donazione", "notes": "consegnata a Caritas", "co2_saved_kg": null }
```

Se `co2_saved_kg` è `null`, il backend la stima dalla tabella interna
(categoria × percentuale d'azione). Le azioni **di ritiro** (donazione,
swap, vendita, riciclo) marcano il capo con `retired_at = now`; la
**riparazione** non lo ritira.

**Risposta `201`** — `ItemAction`.

---

### `GET /items/{item_id}/actions` · `DELETE /actions/{action_id}`

Lista cronologica desc + delete singola. Eliminando un'azione di ritiro
quando non ce ne sono altre sullo stesso capo, il capo viene **riattivato**
(`retired_at = NULL`).

---

### `GET /stats/gap-analysis`

Analizza la composizione del guardaroba con una **rete neurale** addestrata
(fallback a regole esperte se i pesi non ci sono) e individua i **vuoti
funzionali** con raccomandazioni d'acquisto consapevole. Esclude i capi
ritirati. Vedi ADR-011.

**Risposta `200`** — `GapAnalysis`:

```json
{
  "total_items": 13,
  "counts_by_category": { "t-shirt": 12, "jeans": 1 },
  "n_colors": 1,
  "has_neutral": false,
  "ghost_ratio": 0.0,
  "balanced": false,
  "source": "neural-net",
  "gaps": [
    {
      "code": "manca_capospalla",
      "label": "Manca una giacca o un cappotto",
      "advice": "Cerca una giacca o un cappotto versatile, meglio se second-hand…",
      "probability": 1.0
    }
  ]
}
```

`source` è `"neural-net"` quando risponde la rete, `"rules"` col fallback.
`probability` è valorizzata solo dalla rete.

---

### `GET /stats/impact`

Statistiche aggregate del modulo circolare.

**Risposta `200`** — `ImpactStats`:

```json
{
  "total_actions": 7,
  "total_co2_saved_kg": 84.5,
  "actions_by_type": { "riparazione": 3, "donazione": 2, "riciclo": 2 },
  "co2_by_type": { "riparazione": 33.6, "donazione": 39.0, "riciclo": 11.9 },
  "retired_items_count": 4,
  "repaired_items_count": 2
}
```

---

## AI generativa (LLM + try-on)

Endpoint che usano un LLM (litellm) o un modello diffusion (diffusers).
Tutti restituiscono **503** se il backend non è configurato; il frontend
si nasconde i bottoni quando `GET /llm/status` riporta `configured: false`.

Vedi ADR-007 (try-on) e ADR-008 (LLM gateway) in
[architecture.md](architecture.md).

### `GET /llm/status` · `GET /tryon/status`

Introspection per il frontend.

```json
// GET /api/v1/llm/status
{ "configured": true, "model": "claude-haiku-4-5", "tryon_backend": "disabled" }

// GET /api/v1/tryon/status
{ "backend": "disabled", "available": false, "model": null }
```

---

### `POST /items/{item_id}/describe`

Genera una descrizione narrativa breve (1-2 frasi) via LLM. La descrizione
viene salvata su `Item.description`.

**Query**

| nome         | tipo  | default | descrizione                                       |
| ------------ | ----- | ------- | ------------------------------------------------- |
| `regenerate` | bool  | `false` | rigenera anche se già presente                    |

**Risposta `200`** — `ItemDescriptionOut`:

```json
{
  "item_id": 12,
  "description": "T-shirt bordeaux versatile, ideale per outfit casual.",
  "generated": true,
  "model": "claude-haiku-4-5"
}
```

**Risposta `503`** — nessun LLM configurato.

---

### `GET /stats/coach`

Messaggio personalizzato del "coach AI sostenibilità", basato su
`WardrobeStats + ImpactStats + ghost items top 3`. Output cached 24h.

**Query**: `ghost_after_days` (default 30).

**Risposta `200`** — `CoachOut`:

```json
{
  "text": "Hai evitato 12 kg di CO₂ con la riparazione della giacca…",
  "facts": { "wardrobe": {...}, "impact": {...}, "ghosts_top3": [...] },
  "model": "claude-haiku-4-5",
  "cached": false
}
```

Se il guardaroba è vuoto, restituisce un messaggio canned (senza
chiamare l'LLM). **503** se LLM non configurato.

---

### `POST /items/{item_id}/try-on`

Try-on virtuale via diffusion model locale (Stable Diffusion inpainting).
Richiede `CLOSETAI_TRYON_BACKEND=diffusers`.

**Multipart**: `portrait` (file jpeg/png/webp ≤ 10MB).

**Risposta `200`** — `TryOnOut`:

```json
{
  "item_id": 12,
  "filename": "9f8e7d6c5b4a.png",
  "url": "/api/v1/items/12/try-on/9f8e7d6c5b4a.png",
  "backend": "diffusers",
  "prompt": "a photorealistic portrait of a person wearing a rosso t-shirt…",
  "elapsed_ms": 142300
}
```

L'inferenza su CPU è lenta (30s-3min). Su GPU CUDA pochi secondi.

**Risposta `503`** — backend `disabled` o non disponibile.

---

### `GET /items/{item_id}/try-on/{filename}`

Serve l'immagine generata. Il filename UUID funge da capability token.

---

## ML Lab (pagina tecnica)

Endpoint di **ispezione e prova** delle reti addestrate da noi, usati dalla
pagina `/lab` del frontend. Sola lettura rispetto al DB.

### `GET /ml/models`

Stato + metriche di training dei due modelli (rete stato, rete gap) e dei
loro dataset. Le metriche vengono lette dai checkpoint salvati al momento
del training.

```json
{
  "models": [
    {
      "key": "condition-mlp",
      "name": "Rete stato del capo (Approccio A)",
      "nature": "own",
      "available": true,
      "architecture": "Fashion-CLIP (frozen) → MLP 512→256→128→3",
      "metrics": { "val_accuracy": 0.960, "test_accuracy": 0.940 },
      "train_command": "uv run python scripts/train_condition_model.py"
    }
  ],
  "datasets": [
    { "key": "garment_condition", "available": true, "n_samples": 600 }
  ]
}
```

### `POST /ml/condition/predict`

Prova interattiva della rete stato: multipart `image` → predizione con
probabilità per classe. **Non** crea alcun item. `503` se la rete non è
addestrata.

### `POST /ml/gap/predict`

Simulatore *what-if* della gap analysis: body JSON con `counts` (conteggi
per categoria), `n_colors`, `has_neutral`, `ghost_ratio` → vuoti predetti.
Usa la rete se addestrata (`source: "neural-net"`), altrimenti le regole.

### `GET /ml/condition/confusion-matrix`

Serve il PNG della confusion matrix salvata dall'ultimo training (404 se
il training non è mai stato eseguito).

---

## Schemi

### `Item`

```ts
interface Item {
  id: number
  name: string
  category: string | null
  color: string | null
  image_path: string | null              // filename, non path completo
  price: number | null
  purchase_date: string | null           // "YYYY-MM-DD"
  classification_confidence: number | null  // 0–1, null per mock o se ignota
  description: string | null             // descrizione AI-generata, null se assente
  condition: 'buono' | 'usurato' | 'danneggiato' | null
  retired_at: string | null              // ISO-8601 UTC quando ritirato
  created_at: string                     // ISO-8601 UTC
}
```

### `WearEvent`

```ts
interface WearEvent {
  id: number
  item_id: number
  worn_on: string      // "YYYY-MM-DD"
  occasion: string | null
  created_at: string   // ISO-8601 UTC
}
```

### `OutfitSuggestion` / `OutfitSuggestResponse`

```ts
interface WeatherSummary {
  target_date: string
  temperature_c: number
  precipitation_mm: number
  wind_kmh: number
  weather_code: number
  source: 'open-meteo' | 'fallback'
}

interface OutfitSuggestion {
  items: Item[]
  score: number          // 0..1
  color_score: number    // 0..1
  weather_score: number  // 0..1
  ghost_bonus: number    // 0..0.15
  rationale: string
}

interface OutfitSuggestResponse {
  target_date: string
  weather: WeatherSummary
  outfits: OutfitSuggestion[]
}
```

### `OutfitFeedback`

```ts
interface OutfitFeedback {
  id: number
  item_ids: number[]
  rating: 1 | -1
  occasion: string | null
  created_at: string
}
```

### `ItemAction` / `ImpactStats`

```ts
type ActionType = 'riparazione' | 'swap' | 'vendita' | 'donazione' | 'riciclo'

interface ItemAction {
  id: number
  item_id: number
  action_type: ActionType
  notes: string | null
  co2_saved_kg: number
  created_at: string
}

interface ImpactStats {
  total_actions: number
  total_co2_saved_kg: number
  actions_by_type: Record<ActionType, number>
  co2_by_type: Record<ActionType, number>
  retired_items_count: number
  repaired_items_count: number
}
```

---

## Errori comuni

### `422 Unprocessable Entity` (validazione FastAPI)

Body strutturato. Esempio quando manca `name`:

```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "name"],
      "msg": "Field required",
      "input": null
    }
  ]
}
```

### `400 Bad Request`

Per validazioni applicative (es. MIME non ammesso):

```json
{
  "detail": "Tipo file non supportato: 'application/pdf'. Ammessi: ['image/jpeg', 'image/png', 'image/webp']."
}
```

### `413 Content Too Large`

Per upload oltre 10 MB:

```json
{ "detail": "File troppo grande: limite 10485760 byte." }
```

---

## CORS

Il backend abilita CORS per il dev server Vite:

```
http://localhost:5173
http://127.0.0.1:5173
```

In dev, il frontend usa il proxy Vite (`/api/...` → `http://localhost:8000`):
le richieste sono **same-origin** dal punto di vista del browser, quindi
CORS non interviene.

In produzione, configurare `CORS_ORIGINS` in `app/config.py` con i domini
effettivi del frontend.

---

## Variabili d'ambiente lato backend

| variabile                | default                              | uso                                                  |
| ------------------------ | ------------------------------------ | ---------------------------------------------------- |
| `CLOSETAI_DATA_DIR`      | `<repo>/data`                        | root dello storage locale                            |
| `CLOSETAI_DB_PATH`       | `<CLOSETAI_DATA_DIR>/closetai.db`    | percorso del file SQLite                             |
| `CLOSETAI_CHROMA_DIR`    | `<CLOSETAI_DATA_DIR>/chroma`         | persistenza collection ChromaDB                      |
| `CLOSETAI_DATABASE_URL`  | `sqlite:///<CLOSETAI_DB_PATH>`       | DSN SQLAlchemy completo (sovrascrive)                |
| `CLOSETAI_CLASSIFIER`    | `fashion-clip`                       | `mock` per fallback / test; `fashion-clip` per ML.   |
| `CLOSETAI_DEFAULT_LAT`   | `43.7228` (Pisa)                     | latitudine di default per `/outfits/suggest`.        |
| `CLOSETAI_DEFAULT_LON`   | `10.4017` (Pisa)                     | longitudine di default per `/outfits/suggest`.       |
| `CLOSETAI_LLM_MODEL`     | `claude-haiku-4-5`                   | modello litellm (Anthropic / OpenAI / Ollama / HF). Vedi ADR-008.       |
| `CLOSETAI_TRYON_BACKEND` | `disabled`                           | `diffusers` per attivare il try-on virtuale (scarica ~5GB di pesi).     |
| `ANTHROPIC_API_KEY`      | _(non set)_                          | richiesto per modelli Claude.                                            |
| `OPENAI_API_KEY`         | _(non set)_                          | richiesto per modelli OpenAI.                                            |

I test impostano questi automaticamente su una tempdir isolata e forzano
`CLOSETAI_CLASSIFIER=mock` (vedi `backend/tests/conftest.py`).
