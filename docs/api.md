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

I test impostano questi automaticamente su una tempdir isolata e forzano
`CLOSETAI_CLASSIFIER=mock` (vedi `backend/tests/conftest.py`).
