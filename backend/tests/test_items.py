"""Test per gli endpoint CRUD `/api/v1/items`."""

from __future__ import annotations

from pathlib import Path

from app.ml.classifier import CATEGORIES
from app.ml.color import NAMED_COLORS


def test_list_empty(client) -> None:
    r = client.get("/api/v1/items")
    assert r.status_code == 200
    assert r.json() == []


def test_create_minimal_fills_category_and_color_from_classifier(client, png) -> None:
    r = client.post(
        "/api/v1/items",
        data={"name": "T-shirt blu"},
        files={"image": ("a.png", png((40, 80, 200)), "image/png")},
    )
    assert r.status_code == 201, r.text
    item = r.json()
    assert item["id"] >= 1
    assert item["name"] == "T-shirt blu"
    assert item["category"] in CATEGORIES
    assert item["color"] == "blu"
    assert item["image_path"].endswith(".png")
    assert item["price"] is None
    assert item["purchase_date"] is None


def test_create_full_metadata(client, png) -> None:
    r = client.post(
        "/api/v1/items",
        data={
            "name": "Jeans slim",
            "category": "jeans",
            "color": "denim",
            "price": "59.90",
            "purchase_date": "2025-09-10",
        },
        files={"image": ("j.png", png((30, 30, 90)), "image/png")},
    )
    assert r.status_code == 201, r.text
    item = r.json()
    # Categoria e colore forniti dall'utente NON devono essere sovrascritti
    assert item["category"] == "jeans"
    assert item["color"] == "denim"
    assert item["price"] == 59.9
    assert item["purchase_date"] == "2025-09-10"


def test_user_provided_color_only_keeps_user_color_but_fills_category(client, png) -> None:
    r = client.post(
        "/api/v1/items",
        data={"name": "Capo X", "color": "fuxia"},
        files={"image": ("x.png", png((10, 10, 10)), "image/png")},
    )
    item = r.json()
    assert item["color"] == "fuxia"
    assert item["category"] in CATEGORIES


def test_create_rejects_invalid_mime(client) -> None:
    r = client.post(
        "/api/v1/items",
        data={"name": "doc"},
        files={"image": ("a.pdf", b"%PDF-1.4...", "application/pdf")},
    )
    assert r.status_code == 400
    assert "Tipo file non supportato" in r.json()["detail"]


def test_create_rejects_oversize(client) -> None:
    huge = b"x" * (11 * 1024 * 1024)  # 11 MB > limite 10 MB
    r = client.post(
        "/api/v1/items",
        data={"name": "huge"},
        files={"image": ("big.png", huge, "image/png")},
    )
    assert r.status_code == 413
    assert "troppo grande" in r.json()["detail"]


def test_create_requires_name(client, png) -> None:
    r = client.post(
        "/api/v1/items",
        data={},
        files={"image": ("a.png", png(), "image/png")},
    )
    assert r.status_code == 422


def test_create_requires_image(client) -> None:
    r = client.post("/api/v1/items", data={"name": "x"})
    assert r.status_code == 422


def test_get_detail(client, png) -> None:
    created = client.post(
        "/api/v1/items",
        data={"name": "Maglione"},
        files={"image": ("m.png", png((110, 70, 40)), "image/png")},
    ).json()

    r = client.get(f"/api/v1/items/{created['id']}")
    assert r.status_code == 200
    assert r.json() == created


def test_get_detail_not_found(client) -> None:
    r = client.get("/api/v1/items/9999")
    assert r.status_code == 404
    assert "non trovato" in r.json()["detail"]


def test_list_after_create(client, png) -> None:
    for i in range(3):
        client.post(
            "/api/v1/items",
            data={"name": f"capo-{i}"},
            files={"image": (f"i{i}.png", png(), "image/png")},
        )
    r = client.get("/api/v1/items")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 3
    # ordinati per created_at DESC -> ultimo creato in testa
    assert body[0]["name"] == "capo-2"
    assert body[-1]["name"] == "capo-0"


def test_list_pagination(client, png) -> None:
    for i in range(5):
        client.post(
            "/api/v1/items",
            data={"name": f"p-{i}"},
            files={"image": (f"i{i}.png", png(), "image/png")},
        )
    r = client.get("/api/v1/items?skip=1&limit=2")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 2
    # skip=1, limit=2 sull'ordine DESC: aspetto p-3, p-2
    assert [it["name"] for it in body] == ["p-3", "p-2"]


def test_list_pagination_rejects_bad_limit(client) -> None:
    assert client.get("/api/v1/items?limit=0").status_code == 422
    assert client.get("/api/v1/items?limit=999").status_code == 422
    assert client.get("/api/v1/items?skip=-1").status_code == 422


def test_get_image_returns_file_bytes(client, png) -> None:
    payload = png((255, 0, 0))
    created = client.post(
        "/api/v1/items",
        data={"name": "rossa"},
        files={"image": ("r.png", payload, "image/png")},
    ).json()

    r = client.get(f"/api/v1/items/{created['id']}/image")
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/png"
    assert r.content == payload


def test_get_image_not_found_when_item_missing(client) -> None:
    r = client.get("/api/v1/items/9999/image")
    assert r.status_code == 404


def test_get_image_404_when_file_missing(client, png, items_dir: Path) -> None:
    created = client.post(
        "/api/v1/items",
        data={"name": "ghost"},
        files={"image": ("g.png", png(), "image/png")},
    ).json()

    # Cancello il file fisico, lasciando il record DB
    (items_dir / created["image_path"]).unlink()

    r = client.get(f"/api/v1/items/{created['id']}/image")
    assert r.status_code == 404
    assert "mancante" in r.json()["detail"]


def test_delete_removes_record_and_file(client, png, items_dir: Path) -> None:
    created = client.post(
        "/api/v1/items",
        data={"name": "delete-me"},
        files={"image": ("d.png", png(), "image/png")},
    ).json()
    image_file = items_dir / created["image_path"]
    assert image_file.is_file()

    r = client.delete(f"/api/v1/items/{created['id']}")
    assert r.status_code == 204

    # record sparito
    assert client.get(f"/api/v1/items/{created['id']}").status_code == 404
    # file sparito
    assert not image_file.exists()


def test_delete_idempotent_not_found(client) -> None:
    r = client.delete("/api/v1/items/9999")
    assert r.status_code == 404


def test_item_color_returned_is_named(client, png) -> None:
    """Sanity: tutti i colori restituiti dal classificatore mock sono nominabili."""
    for rgb in [(0, 0, 0), (240, 220, 30), (60, 160, 60)]:
        item = client.post(
            "/api/v1/items",
            data={"name": "x"},
            files={"image": ("a.png", png(rgb), "image/png")},
        ).json()
        assert item["color"] in NAMED_COLORS
