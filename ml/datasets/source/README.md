# Immagini sorgente (capi puliti)

Metti qui le tue **foto reali** di capi in buono stato (jpg/png/webp).
Il dataset builder le userà come base da degradare per ottenere le 4 classi
di stato di conservazione.

Se questa cartella è vuota, il builder genera immagini sintetiche di
bootstrap (sagome stilizzate) — utili solo per validare la pipeline, non
per il training finale.

```bash
cd backend
uv run python scripts/build_condition_dataset.py --per-class 60
```

Vedi `docs/dataset-datasheet.md` per i dettagli.
