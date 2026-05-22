"""Test per gli endpoint wear log e per le statistiche di utilizzo."""

from __future__ import annotations

from datetime import date, timedelta


def _create_item(client, png, **extra):
    data = {"name": "X", **{k: str(v) for k, v in extra.items()}}
    r = client.post(
        "/api/v1/items",
        data=data,
        files={"image": ("a.png", png(), "image/png")},
    )
    assert r.status_code == 201, r.text
    return r.json()


def test_log_wear_defaults_to_today(client, png) -> None:
    item = _create_item(client, png)
    r = client.post(f"/api/v1/items/{item['id']}/wear", json={})
    assert r.status_code == 201, r.text
    event = r.json()
    assert event["item_id"] == item["id"]
    assert event["worn_on"] == date.today().isoformat()
    assert event["occasion"] is None


def test_log_wear_with_payload(client, png) -> None:
    item = _create_item(client, png)
    r = client.post(
        f"/api/v1/items/{item['id']}/wear",
        json={"worn_on": "2025-09-10", "occasion": "lavoro"},
    )
    event = r.json()
    assert event["worn_on"] == "2025-09-10"
    assert event["occasion"] == "lavoro"


def test_log_wear_404_when_item_missing(client) -> None:
    r = client.post("/api/v1/items/9999/wear", json={})
    assert r.status_code == 404


def test_list_wears_orders_by_worn_on_desc(client, png) -> None:
    item = _create_item(client, png)
    for d in ("2025-01-10", "2025-03-05", "2025-02-20"):
        client.post(f"/api/v1/items/{item['id']}/wear", json={"worn_on": d})

    r = client.get(f"/api/v1/items/{item['id']}/wears")
    assert r.status_code == 200
    body = r.json()
    assert [e["worn_on"] for e in body] == ["2025-03-05", "2025-02-20", "2025-01-10"]


def test_batch_log_wears(client, png) -> None:
    a = _create_item(client, png)
    b = _create_item(client, png)
    r = client.post(
        "/api/v1/wear-events/batch",
        json={
            "events": [
                {"item_id": a["id"], "worn_on": "2025-09-10"},
                {"item_id": b["id"]},  # default oggi
                {"item_id": a["id"], "worn_on": "2025-09-11", "occasion": "festa"},
            ]
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert len(body) == 3


def test_batch_log_wears_rejects_missing_items(client, png) -> None:
    a = _create_item(client, png)
    r = client.post(
        "/api/v1/wear-events/batch",
        json={"events": [{"item_id": a["id"]}, {"item_id": 9999}]},
    )
    assert r.status_code == 404
    assert "9999" in r.json()["detail"]


def test_delete_wear_event(client, png) -> None:
    item = _create_item(client, png)
    created = client.post(f"/api/v1/items/{item['id']}/wear", json={}).json()

    r = client.delete(f"/api/v1/wear-events/{created['id']}")
    assert r.status_code == 204
    assert client.delete(f"/api/v1/wear-events/{created['id']}").status_code == 404


def test_item_cascade_delete_removes_wears(client, png) -> None:
    item = _create_item(client, png)
    for _ in range(3):
        client.post(f"/api/v1/items/{item['id']}/wear", json={})
    assert len(client.get(f"/api/v1/items/{item['id']}/wears").json()) == 3

    assert client.delete(f"/api/v1/items/{item['id']}").status_code == 204
    # L'item è sparito, e così i suoi wear events: GET /wears torna 404 sull'item.
    assert client.get(f"/api/v1/items/{item['id']}/wears").status_code == 404


# ----- stats --------------------------------------------------------------


def test_item_stats_empty(client, png) -> None:
    item = _create_item(client, png, price="100.00")
    r = client.get(f"/api/v1/items/{item['id']}/stats")
    body = r.json()
    assert body["wear_count"] == 0
    assert body["last_worn"] is None
    assert body["cost_per_wear"] is None
    assert body["days_since_last_worn"] is None


def test_item_stats_with_wears_and_cost_per_wear(client, png) -> None:
    item = _create_item(client, png, price="100.00")
    for d in ("2025-09-01", "2025-09-05", "2025-09-10", "2025-09-15"):
        client.post(f"/api/v1/items/{item['id']}/wear", json={"worn_on": d})

    body = client.get(f"/api/v1/items/{item['id']}/stats").json()
    assert body["wear_count"] == 4
    assert body["last_worn"] == "2025-09-15"
    assert body["cost_per_wear"] == 25.0  # 100/4


def test_item_marked_as_ghost_after_threshold(client, png) -> None:
    # Capo acquistato 60 giorni fa, mai indossato → ghost con soglia 30 giorni
    long_ago = (date.today() - timedelta(days=60)).isoformat()
    item = _create_item(client, png, purchase_date=long_ago)
    body = client.get(
        f"/api/v1/items/{item['id']}/stats", params={"ghost_after_days": 30}
    ).json()
    assert body["is_ghost"] is True
    assert body["ghost_after_days"] == 30


def test_item_not_ghost_when_recently_worn(client, png) -> None:
    long_ago = (date.today() - timedelta(days=60)).isoformat()
    item = _create_item(client, png, purchase_date=long_ago)
    client.post(f"/api/v1/items/{item['id']}/wear", json={})

    body = client.get(f"/api/v1/items/{item['id']}/stats").json()
    assert body["is_ghost"] is False


def test_wardrobe_stats(client, png) -> None:
    a = _create_item(client, png, price="50.00")
    b = _create_item(client, png, price="100.00")
    _create_item(client, png)  # niente price → non entra in cost-per-wear

    client.post(f"/api/v1/items/{a['id']}/wear", json={})
    client.post(f"/api/v1/items/{a['id']}/wear", json={})  # a: 2 wears, cpw = 25
    client.post(f"/api/v1/items/{b['id']}/wear", json={})  # b: 1 wear, cpw = 100

    body = client.get("/api/v1/stats/wardrobe").json()
    assert body["total_items"] == 3
    assert body["total_wears"] == 3
    assert body["avg_wears_per_item"] == 1.0
    assert body["total_investment"] == 150.0
    # avg cpw = (25 + 100) / 2 = 62.5
    assert body["avg_cost_per_wear"] == 62.5
    # Top: a (2 wears) > b (1 wear). Il terzo capo non compare (no wears).
    top_names = [t["item_id"] for t in body["top_worn"]]
    assert top_names == [a["id"], b["id"]]


def test_ghosts_endpoint(client, png) -> None:
    # capo vecchio non indossato → ghost
    long_ago = (date.today() - timedelta(days=60)).isoformat()
    ghost = _create_item(client, png, purchase_date=long_ago)
    # capo vecchio indossato → NON ghost
    worn = _create_item(client, png, purchase_date=long_ago)
    client.post(f"/api/v1/items/{worn['id']}/wear", json={})
    # capo nuovo non indossato → NON ghost (sotto soglia)
    recent = (date.today() - timedelta(days=5)).isoformat()
    _create_item(client, png, purchase_date=recent)

    body = client.get("/api/v1/stats/ghosts", params={"ghost_after_days": 30}).json()
    ids = [g["item_id"] for g in body]
    assert ids == [ghost["id"]]
    assert body[0]["days_owned"] >= 60
