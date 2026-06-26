"""Test dell'integrazione del backend VLM e del routing a cascata.

Il VLM vero richiede GPU + adapter addestrato: qui montiamo un fake che
restituisce {stato, difetto, tutorial}, e verifichiamo routing/fallback.
"""

from __future__ import annotations

import pytest


def _create(client, png, **extra):
    data = {"name": extra.pop("name", "X"), **{k: str(v) for k, v in extra.items()}}
    r = client.post(
        "/api/v1/items",
        data=data,
        files={"image": ("a.png", png(), "image/png")},
    )
    assert r.status_code == 201, r.text
    return r.json()


# ----- parsing / validazione output VLM ------------------------------------


def test_vlm_parse_valid_json() -> None:
    from app.ml.condition_vlm import _parse

    raw = '{"stato": "danneggiato", "difetto": "strappo", "tutorial": "Cuci..."}'
    d = _parse(raw)
    assert d.condition == "danneggiato"
    assert d.defect == "strappo"
    assert d.tutorial == "Cuci..."


def test_vlm_parse_with_preamble_and_fence() -> None:
    from app.ml.condition_vlm import _parse

    raw = 'Ecco la valutazione:\n```json\n{"stato": "usurato", "difetto": null, "tutorial": null}\n```'
    d = _parse(raw)
    assert d.condition == "usurato"
    assert d.defect is None
    assert d.tutorial is None


def test_vlm_parse_normalizes_synonyms() -> None:
    from app.ml.condition_vlm import _parse

    assert _parse('{"stato": "ROVINATO"}').condition == "danneggiato"
    assert _parse('{"stato": "Come nuovo"}').condition == "nuovo"


def test_vlm_parse_invalid_condition_returns_none() -> None:
    from app.ml.condition_vlm import _parse

    # stato non riconoscibile -> condition None (il chiamante farà fallback)
    assert _parse('{"stato": "boh"}').condition is None
    assert _parse("non è json").condition is None


def test_vlm_factory_none_without_adapter() -> None:
    from app.ml.condition_vlm import get_condition_vlm

    assert get_condition_vlm() is None


# ----- routing a cascata ---------------------------------------------------


class _FakeVlm:
    def __init__(self, condition, defect=None, tutorial=None):
        from app.ml.condition_vlm import VlmDiagnosis

        self._diag = VlmDiagnosis(
            condition=condition, defect=defect, tutorial=tutorial, raw="{}"
        )

    def is_available(self) -> bool:
        return True

    def diagnose(self, image_path):
        _ = image_path
        return self._diag


def test_auto_prefers_vlm_over_mlp_and_heuristic(client, png, monkeypatch) -> None:
    from app.ml import condition_vlm

    monkeypatch.setattr(
        condition_vlm, "get_condition_vlm",
        lambda: _FakeVlm("danneggiato", defect="strappo netto sul ginocchio",
                         tutorial="Applica una toppa termoadesiva, poi cuci a punto scala."),
    )

    item = _create(client, png, category="jeans")
    body = client.post(f"/api/v1/items/{item['id']}/diagnose").json()
    assert body["source"] == "vlm-lora"
    assert body["condition"] == "danneggiato"
    assert body["defect"] == "strappo netto sul ginocchio"
    assert "toppa termoadesiva" in body["tutorial"]


def test_vlm_invalid_output_falls_back_to_heuristic(client, png, monkeypatch) -> None:
    from app.ml import condition_vlm

    # Il VLM "risponde" ma con stato non valido → condition None → fallback.
    monkeypatch.setattr(
        condition_vlm, "get_condition_vlm", lambda: _FakeVlm(None)
    )
    item = _create(client, png, category="t-shirt")
    body = client.post(f"/api/v1/items/{item['id']}/diagnose").json()
    assert body["source"] == "heuristic"
    assert body["tutorial"] is None


def test_forced_heuristic_ignores_vlm(client, png, monkeypatch) -> None:
    from app.ml import condition_vlm
    from app.services import condition as condition_service

    monkeypatch.setattr(condition_service, "CONDITION_BACKEND", "heuristic")
    monkeypatch.setattr(
        condition_vlm, "get_condition_vlm", lambda: _FakeVlm("danneggiato")
    )
    item = _create(client, png, category="t-shirt")
    body = client.post(f"/api/v1/items/{item['id']}/diagnose").json()
    assert body["source"] == "heuristic"


def test_forced_vlm_falls_back_when_unavailable(client, png, monkeypatch) -> None:
    from app.services import condition as condition_service

    # backend forzato a vlm-lora ma nessun adapter → fallback euristica.
    monkeypatch.setattr(condition_service, "CONDITION_BACKEND", "vlm-lora")
    item = _create(client, png, category="t-shirt")
    body = client.post(f"/api/v1/items/{item['id']}/diagnose").json()
    assert body["source"] == "heuristic"


@pytest.mark.parametrize("backend", ["auto", "clip-mlp", "vlm-lora", "heuristic"])
def test_all_backends_return_valid_diagnosis(client, png, monkeypatch, backend) -> None:
    """Qualunque backend configurato deve sempre restituire una diagnosi valida
    (grazie al fallback), senza errori."""
    from app.services import condition as condition_service

    monkeypatch.setattr(condition_service, "CONDITION_BACKEND", backend)
    item = _create(client, png, category="t-shirt")
    body = client.post(f"/api/v1/items/{item['id']}/diagnose").json()
    assert body["condition"] in ("nuovo", "buono", "usurato", "danneggiato")
    assert body["source"] in ("vlm-lora", "clip-mlp", "heuristic")
