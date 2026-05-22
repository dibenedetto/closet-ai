"""Test dell'endpoint POST /items/{id}/reclassify e dell'integrazione ChromaDB."""

from __future__ import annotations


def test_reclassify_updates_category_and_color(client, png) -> None:
    created = client.post(
        "/api/v1/items",
        data={"name": "X", "category": "gonna", "color": "viola"},
        files={"image": ("a.png", png((40, 80, 200)), "image/png")},
    ).json()
    assert created["category"] == "gonna"
    assert created["color"] == "viola"

    r = client.post(f"/api/v1/items/{created['id']}/reclassify")
    assert r.status_code == 200, r.text
    updated = r.json()
    # Il mock rifa categoria casuale e ricalcola il colore: l'immagine è blu pura.
    assert updated["color"] == "blu"
    assert updated["id"] == created["id"]


def test_reclassify_404_when_item_missing(client) -> None:
    r = client.post("/api/v1/items/9999/reclassify")
    assert r.status_code == 404


def test_reclassify_400_when_item_has_no_image(client, png) -> None:
    """Si simula un item con `image_path = NULL` patchando dopo la creazione."""
    from sqlalchemy import update

    from app.models import Item

    created = client.post(
        "/api/v1/items",
        data={"name": "no-image"},
        files={"image": ("a.png", png(), "image/png")},
    ).json()

    # Manipoliamo direttamente il DB via la sessione overridata
    db = next(client.app.dependency_overrides[next(iter(client.app.dependency_overrides))]())
    try:
        db.execute(update(Item).where(Item.id == created["id"]).values(image_path=None))
        db.commit()
    finally:
        db.close()

    r = client.post(f"/api/v1/items/{created['id']}/reclassify")
    assert r.status_code == 400


def test_reclassify_404_when_file_missing_on_disk(client, png, items_dir) -> None:
    created = client.post(
        "/api/v1/items",
        data={"name": "ghost"},
        files={"image": ("g.png", png(), "image/png")},
    ).json()
    (items_dir / created["image_path"]).unlink()

    r = client.post(f"/api/v1/items/{created['id']}/reclassify")
    assert r.status_code == 404


def test_chroma_collection_excludes_deleted_items(client, png, chroma_dir) -> None:
    """Anche se il mock non produce embedding, ChromaDB deve restare 'count=0'
    perché non vengono mai inseriti record. Verifica che il delete non rompa nulla."""
    from app.services.embeddings import get_embedding_store

    _ = chroma_dir
    # Forziamo manualmente un upsert per simulare un classifier reale
    store = get_embedding_store()
    store.upsert(123, [0.0] * 4, metadata={"category": "test"})
    assert store.count() == 1

    store.delete(123)
    assert store.count() == 0
