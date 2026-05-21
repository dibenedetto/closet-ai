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

## Schemi

### `Item`

```ts
interface Item {
  id: number
  name: string
  category: string | null
  color: string | null
  image_path: string | null      // filename, non path completo
  price: number | null
  purchase_date: string | null   // "YYYY-MM-DD"
  created_at: string             // ISO-8601 UTC
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

| variabile              | default                              | uso                                  |
| ---------------------- | ------------------------------------ | ------------------------------------ |
| `CLOSETAI_DATA_DIR`    | `<repo>/data`                        | root dello storage locale            |
| `CLOSETAI_DB_PATH`     | `<CLOSETAI_DATA_DIR>/closetai.db`    | percorso del file SQLite             |
| `CLOSETAI_DATABASE_URL`| `sqlite:///<CLOSETAI_DB_PATH>`       | DSN SQLAlchemy completo (sovrascrive)|

I test impostano questi automaticamente su una tempdir isolata (vedi
`backend/tests/conftest.py`).
