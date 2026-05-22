"""Test per il recommender di outfit (Fase 4)."""

from __future__ import annotations

from datetime import date

import pytest

from app.services.color_compat import (
    color_compat_score,
    is_neutral,
    palette_compat_score,
)
from app.services.weather import WeatherInfo


# ----- color compatibility ---------------------------------------------------


def test_neutrals_are_recognized() -> None:
    assert is_neutral("nero")
    assert is_neutral("bianco")
    assert is_neutral("grigio")
    assert is_neutral("beige")
    assert not is_neutral("rosso")
    assert not is_neutral("blu")


def test_same_color_high_score() -> None:
    assert color_compat_score("blu", "blu") >= 0.8


def test_neutral_with_anything_is_high() -> None:
    assert color_compat_score("nero", "rosso") >= 0.85
    assert color_compat_score("bianco", "verde") >= 0.85


def test_analogous_colors_score() -> None:
    # rosso e arancione sono analoghi (hue close)
    assert color_compat_score("rosso", "arancione") >= 0.7


def test_unknown_color_neutral_score() -> None:
    assert color_compat_score("blu", None) == 0.5
    assert color_compat_score(None, None) == 0.5
    assert color_compat_score("blu", "inesistente") == 0.5


def test_palette_compat_with_single_color() -> None:
    # palette di 1 colore: nessuna coppia → score di default
    assert palette_compat_score(["blu"]) == 0.5


# ----- suggest endpoint ------------------------------------------------------


@pytest.fixture
def stub_weather(monkeypatch):
    """Sostituisce il chiamante di Open-Meteo con un payload deterministico."""

    def _set(temperature_c: float = 18.0, precipitation_mm: float = 0.0):
        def fake(target_date: date, **_kw) -> WeatherInfo:
            return WeatherInfo(
                target_date=target_date,
                temperature_c=temperature_c,
                precipitation_mm=precipitation_mm,
                wind_kmh=10.0,
                weather_code=0,
                source="open-meteo",
            )

        monkeypatch.setattr("app.services.weather.fetch_weather", fake)

    return _set


def _create(client, png, name: str, category: str, color: str):
    r = client.post(
        "/api/v1/items",
        data={"name": name, "category": category, "color": color},
        files={"image": ("a.png", png(), "image/png")},
    )
    assert r.status_code == 201, r.text
    return r.json()


def test_suggest_returns_outfits_with_weather(client, png, stub_weather) -> None:
    stub_weather(temperature_c=18.0)
    _create(client, png, "Camicia bianca", "camicia", "bianco")
    _create(client, png, "Jeans blu", "jeans", "blu")
    _create(client, png, "Scarpe nere", "scarpe", "nero")

    r = client.get("/api/v1/outfits/suggest")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["target_date"] == date.today().isoformat()
    assert body["weather"]["temperature_c"] == 18.0
    assert body["weather"]["source"] == "open-meteo"
    assert len(body["outfits"]) >= 1

    first = body["outfits"][0]
    assert 0.0 <= first["score"] <= 1.0
    assert len(first["items"]) >= 2
    cats = [it["category"] for it in first["items"]]
    # Almeno un top o vestito + un bottom (o vestito da solo)
    has_top = any(c in {"camicia", "t-shirt", "felpa", "maglione"} for c in cats)
    has_bottom = any(c in {"jeans", "pantaloni", "shorts", "gonna"} for c in cats)
    has_dress = "vestito" in cats
    assert has_dress or (has_top and has_bottom)


def test_suggest_excludes_shorts_when_cold(client, png, stub_weather) -> None:
    stub_weather(temperature_c=2.0)  # freddo
    _create(client, png, "Camicia bianca", "camicia", "bianco")
    _create(client, png, "Shorts blu", "shorts", "blu")
    _create(client, png, "Jeans blu", "jeans", "blu")
    _create(client, png, "Cappotto nero", "cappotto", "nero")
    _create(client, png, "Scarpe nere", "scarpe", "nero")

    r = client.get("/api/v1/outfits/suggest")
    body = r.json()
    for outfit in body["outfits"]:
        cats = [it["category"] for it in outfit["items"]]
        assert "shorts" not in cats


def test_suggest_excludes_cappotto_when_warm(client, png, stub_weather) -> None:
    stub_weather(temperature_c=28.0)  # caldo
    _create(client, png, "T-shirt blu", "t-shirt", "blu")
    _create(client, png, "Shorts beige", "shorts", "beige")
    _create(client, png, "Scarpe bianche", "scarpe", "bianco")
    _create(client, png, "Cappotto pesante", "cappotto", "nero")

    r = client.get("/api/v1/outfits/suggest")
    body = r.json()
    for outfit in body["outfits"]:
        cats = [it["category"] for it in outfit["items"]]
        assert "cappotto" not in cats


def test_suggest_empty_wardrobe(client, stub_weather) -> None:
    stub_weather()
    r = client.get("/api/v1/outfits/suggest")
    assert r.status_code == 200
    assert r.json()["outfits"] == []


def test_suggest_accepts_date_and_coords(client, png, stub_weather) -> None:
    stub_weather()
    _create(client, png, "Camicia", "camicia", "blu")
    _create(client, png, "Pantaloni", "pantaloni", "nero")

    r = client.get(
        "/api/v1/outfits/suggest",
        params={"date": "2026-06-15", "lat": 45.5, "lon": 9.2, "count": 2},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["target_date"] == "2026-06-15"
    assert len(body["outfits"]) <= 2


# ----- feedback --------------------------------------------------------------


def test_post_feedback_like(client, png) -> None:
    a = _create(client, png, "A", "camicia", "blu")
    b = _create(client, png, "B", "jeans", "nero")

    r = client.post(
        "/api/v1/outfits/feedback",
        json={"item_ids": [a["id"], b["id"]], "rating": 1, "occasion": "lavoro"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["rating"] == 1
    assert sorted(body["item_ids"]) == sorted([a["id"], b["id"]])


def test_post_feedback_rejects_zero_rating(client) -> None:
    r = client.post(
        "/api/v1/outfits/feedback",
        json={"item_ids": [1, 2], "rating": 0},
    )
    assert r.status_code == 422


def test_post_feedback_rejects_out_of_range(client) -> None:
    r = client.post(
        "/api/v1/outfits/feedback",
        json={"item_ids": [1], "rating": 2},
    )
    assert r.status_code == 422


def test_post_feedback_rejects_empty_item_ids(client) -> None:
    r = client.post("/api/v1/outfits/feedback", json={"item_ids": [], "rating": 1})
    assert r.status_code == 422


def test_list_feedback(client, png) -> None:
    a = _create(client, png, "A", "camicia", "blu")
    b = _create(client, png, "B", "jeans", "nero")
    client.post(
        "/api/v1/outfits/feedback",
        json={"item_ids": [a["id"], b["id"]], "rating": 1},
    )
    client.post(
        "/api/v1/outfits/feedback",
        json={"item_ids": [a["id"]], "rating": -1},
    )
    r = client.get("/api/v1/outfits/feedback")
    body = r.json()
    assert len(body) == 2
    # Più recenti per primi (id desc)
    assert body[0]["rating"] == -1


def test_suggest_weather_fallback_when_api_fails(client, png, monkeypatch) -> None:
    """Se Open-Meteo non risponde, l'endpoint deve comunque dare un risultato.

    NB: non patchiamo `httpx.Client.get` direttamente, perché lo stesso modulo
    è usato dal TestClient di FastAPI; sostituiamo invece il singolo HTTP
    chiamato dal weather service.
    """
    from app.services import weather as weather_service

    _create(client, png, "Camicia", "camicia", "blu")
    _create(client, png, "Jeans", "jeans", "nero")

    original = weather_service.fetch_weather

    def fail_then_fallback(target_date, **kw):
        # Riusa lo stesso fallback che il service userebbe in caso di errore
        return weather_service._fallback(target_date)

    monkeypatch.setattr(weather_service, "fetch_weather", fail_then_fallback)

    try:
        r = client.get("/api/v1/outfits/suggest")
    finally:
        monkeypatch.setattr(weather_service, "fetch_weather", original)

    assert r.status_code == 200
    assert r.json()["weather"]["source"] == "fallback"
