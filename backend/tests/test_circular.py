"""Test per il modulo circolare (Fase 5)."""

from __future__ import annotations

from datetime import date, timedelta


def _create(client, png, **extra):
    data = {"name": extra.pop("name", "X"), **{k: str(v) for k, v in extra.items()}}
    r = client.post(
        "/api/v1/items",
        data=data,
        files={"image": ("a.png", png(), "image/png")},
    )
    assert r.status_code == 201, r.text
    return r.json()


# ----- service: circular ---------------------------------------------------


def test_estimate_co2_by_category_and_action() -> None:
    from app.services.circular import estimate_co2_saved

    # jeans (32 kg) * vendita (1.0) = 32
    assert estimate_co2_saved("jeans", "vendita") == 32.0
    # cappotto (40 kg) * riparazione (0.7) = 28
    assert estimate_co2_saved("cappotto", "riparazione") == 28.0
    # categoria sconosciuta usa default (15) * riciclo (0.3) = 4.5
    assert estimate_co2_saved("alieno", "riciclo") == 4.5
    # action sconosciuta usa pct 0.5
    assert estimate_co2_saved("t-shirt", "boh") == 3.5  # 7 * 0.5


def test_suggest_actions_ordered_by_priority() -> None:
    from app.services.circular import suggest_actions

    out = suggest_actions("jeans", "danneggiato")
    assert out, "deve restituire almeno una proposta"
    # priorità monotona crescente
    priorities = [a.priority for a in out]
    assert priorities == sorted(priorities)
    # per "danneggiato" la riparazione è la prima opzione
    assert out[0].action_type == "riparazione"


def test_retiring_actions_set() -> None:
    from app.services.circular import is_retiring

    for a in ("swap", "vendita", "donazione", "riciclo"):
        assert is_retiring(a), a
    assert not is_retiring("riparazione")


# ----- service: condition heuristic ----------------------------------------


def test_diagnose_new_item_recently_added(client, png) -> None:
    item = _create(client, png, category="t-shirt")
    r = client.post(f"/api/v1/items/{item['id']}/diagnose")
    assert r.status_code == 200
    body = r.json()
    assert body["condition"] == "buono"  # "nuovo" fuso in "buono"
    assert body["wear_count"] == 0
    # persistita su Item
    assert client.get(f"/api/v1/items/{item['id']}").json()["condition"] == "buono"


def test_diagnose_marks_old_unused_as_usurato_or_worse(client, png) -> None:
    long_ago = (date.today() - timedelta(days=800)).isoformat()
    item = _create(client, png, category="t-shirt", purchase_date=long_ago)
    body = client.post(f"/api/v1/items/{item['id']}/diagnose").json()
    assert body["condition"] in ("usurato", "danneggiato")


def test_diagnose_does_not_overwrite_manual_condition(client, png) -> None:
    item = _create(client, png, category="t-shirt")
    # Override manuale prima della diagnosi
    r = client.put(
        f"/api/v1/items/{item['id']}/condition",
        json={"condition": "danneggiato"},
    )
    assert r.status_code == 200
    # La diagnosi successiva non sovrascrive una condition già settata
    body = client.post(f"/api/v1/items/{item['id']}/diagnose").json()
    assert body["condition"] == "danneggiato"


def test_diagnose_404(client) -> None:
    assert client.post("/api/v1/items/9999/diagnose").status_code == 404


# ----- actions CRUD --------------------------------------------------------


def test_register_repairing_action_does_not_retire(client, png) -> None:
    item = _create(client, png, category="jeans")
    r = client.post(
        f"/api/v1/items/{item['id']}/actions",
        json={"action_type": "riparazione", "notes": "rammendo cucitura"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["action_type"] == "riparazione"
    # CO₂ stimato automaticamente per jeans = 32 * 0.7 = 22.4
    assert body["co2_saved_kg"] == 22.4
    # Capo NON ritirato dopo riparazione
    assert client.get(f"/api/v1/items/{item['id']}").json()["retired_at"] is None


def test_register_retiring_action_marks_item_retired(client, png) -> None:
    item = _create(client, png, category="t-shirt")
    r = client.post(
        f"/api/v1/items/{item['id']}/actions",
        json={"action_type": "donazione"},
    )
    assert r.status_code == 201
    # 7 * 1.0 = 7.0
    assert r.json()["co2_saved_kg"] == 7.0
    # Capo ritirato
    detail = client.get(f"/api/v1/items/{item['id']}").json()
    assert detail["retired_at"] is not None


def test_retired_item_rejects_duplicate_retiring_action(client, png) -> None:
    item = _create(client, png, category="cappotto")
    first = client.post(
        f"/api/v1/items/{item['id']}/actions",
        json={"action_type": "donazione"},
    )
    assert first.status_code == 201

    duplicate = client.post(
        f"/api/v1/items/{item['id']}/actions",
        json={"action_type": "vendita"},
    )
    assert duplicate.status_code == 409
    assert "già in seconda vita" in duplicate.json()["detail"]


def test_register_action_with_explicit_co2(client, png) -> None:
    item = _create(client, png, category="t-shirt")
    r = client.post(
        f"/api/v1/items/{item['id']}/actions",
        json={"action_type": "swap", "co2_saved_kg": 12.5},
    )
    body = r.json()
    assert body["co2_saved_kg"] == 12.5


def test_register_action_rejects_invalid_type(client, png) -> None:
    item = _create(client, png)
    r = client.post(
        f"/api/v1/items/{item['id']}/actions",
        json={"action_type": "invalid"},
    )
    assert r.status_code == 422


def test_list_actions_desc_order(client, png) -> None:
    item = _create(client, png, category="t-shirt")
    client.post(
        f"/api/v1/items/{item['id']}/actions",
        json={"action_type": "riparazione"},
    )
    client.post(
        f"/api/v1/items/{item['id']}/actions",
        json={"action_type": "riparazione", "notes": "seconda"},
    )
    body = client.get(f"/api/v1/items/{item['id']}/actions").json()
    assert len(body) == 2
    # Più recente per primo
    assert body[0]["notes"] == "seconda"


def test_delete_retiring_action_reactivates_item(client, png) -> None:
    item = _create(client, png, category="t-shirt")
    created = client.post(
        f"/api/v1/items/{item['id']}/actions",
        json={"action_type": "donazione"},
    ).json()
    assert client.get(f"/api/v1/items/{item['id']}").json()["retired_at"] is not None

    assert client.delete(f"/api/v1/actions/{created['id']}").status_code == 204
    # Capo riattivato
    assert client.get(f"/api/v1/items/{item['id']}").json()["retired_at"] is None


def test_delete_action_404(client) -> None:
    assert client.delete("/api/v1/actions/9999").status_code == 404


# ----- retired exclusion da stats ------------------------------------------


def test_retired_items_excluded_from_wardrobe_stats(client, png) -> None:
    a = _create(client, png, name="A", category="t-shirt", price=50)
    b = _create(client, png, name="B", category="jeans", price=100)
    client.post(f"/api/v1/items/{a['id']}/wear", json={})
    client.post(f"/api/v1/items/{b['id']}/wear", json={})
    client.post(f"/api/v1/items/{b['id']}/wear", json={})
    # Ritiro b via donazione
    client.post(
        f"/api/v1/items/{b['id']}/actions",
        json={"action_type": "donazione"},
    )

    body = client.get("/api/v1/stats/wardrobe").json()
    # Tutte le metriche descrivono il guardaroba attivo: solo A.
    assert body["total_items"] == 1
    assert body["total_wears"] == 1
    assert body["total_investment"] == 50.0
    assert body["avg_cost_per_wear"] == 50.0
    assert [item["item_id"] for item in body["top_worn"]] == [a["id"]]


def test_retired_items_excluded_from_ghosts(client, png) -> None:
    long_ago = (date.today() - timedelta(days=120)).isoformat()
    a = _create(client, png, name="A", category="t-shirt", purchase_date=long_ago)
    b = _create(client, png, name="B", category="jeans", purchase_date=long_ago)
    # b ritirato non è più ghost
    client.post(
        f"/api/v1/items/{b['id']}/actions",
        json={"action_type": "donazione"},
    )

    body = client.get("/api/v1/stats/ghosts").json()
    ids = [g["item_id"] for g in body]
    assert ids == [a["id"]]


# ----- impact stats --------------------------------------------------------


def test_impact_stats_aggregates(client, png) -> None:
    a = _create(client, png, name="A", category="t-shirt")  # 7 kg base
    b = _create(client, png, name="B", category="jeans")  # 32 kg base
    client.post(
        f"/api/v1/items/{a['id']}/actions",
        json={"action_type": "donazione"},  # 7 kg
    )
    client.post(
        f"/api/v1/items/{b['id']}/actions",
        json={"action_type": "riparazione"},  # 22.4 kg
    )
    client.post(
        f"/api/v1/items/{b['id']}/actions",
        json={"action_type": "riparazione"},  # 22.4 kg
    )

    body = client.get("/api/v1/stats/impact").json()
    assert body["total_actions"] == 3
    assert body["total_co2_saved_kg"] == round(7 + 22.4 + 22.4, 2)
    assert body["actions_by_type"]["donazione"] == 1
    assert body["actions_by_type"]["riparazione"] == 2
    assert body["retired_items_count"] == 1  # solo a
    assert body["repaired_items_count"] == 1  # solo b
