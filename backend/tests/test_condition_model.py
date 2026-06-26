"""Test del modello visivo di diagnosi condizione (Approccio A) e del
fallback all'euristica."""

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


# ----- MLP unit ------------------------------------------------------------


def test_build_mlp_output_shape() -> None:
    import torch

    from app.ml.condition_model import CONDITION_LABELS, build_mlp

    model = build_mlp()
    out = model(torch.zeros(3, 512))
    assert out.shape == (3, len(CONDITION_LABELS))


def test_condition_classifier_none_without_weights() -> None:
    """Senza pesi addestrati, il factory ritorna None (→ fallback euristica)."""
    from app.ml.condition_model import get_condition_classifier

    assert get_condition_classifier() is None


# ----- integrazione nel servizio diagnose ----------------------------------


def test_diagnose_falls_back_to_heuristic(client, png) -> None:
    """Senza modello vision, la diagnosi resta euristica (deterministica)."""
    item = _create(client, png, category="t-shirt")
    body = client.post(f"/api/v1/items/{item['id']}/diagnose").json()
    assert body["source"] == "heuristic"
    assert body["condition"] == "nuovo"
    assert body["confidence"] is None


def test_diagnose_uses_vision_model_when_available(client, png, monkeypatch) -> None:
    """Con un classifier di condizione montato, la diagnosi viene dalla foto."""
    from app.ml import condition_model
    from app.ml.condition_model import ConditionPrediction

    class FakeConditionClassifier:
        def is_available(self) -> bool:
            return True

        def predict_from_image(self, image_path):
            _ = image_path
            return ConditionPrediction(
                condition="danneggiato",
                confidence=0.91,
                probabilities={"nuovo": 0.02, "buono": 0.03, "usurato": 0.04, "danneggiato": 0.91},
            )

    # `condition.py` importa il factory lazy dentro la funzione: patchando il
    # modulo sorgente, la prossima chiamata vede il fake.
    monkeypatch.setattr(
        condition_model, "get_condition_classifier", lambda: FakeConditionClassifier()
    )

    # capo nuovo per l'euristica, ma la foto dice "danneggiato"
    item = _create(client, png, category="t-shirt")
    body = client.post(f"/api/v1/items/{item['id']}/diagnose").json()
    assert body["source"] == "clip-mlp"
    assert body["condition"] == "danneggiato"
    assert 0.9 <= body["confidence"] <= 1.0


def test_vision_diagnosis_skipped_when_file_missing(client, png, items_dir, monkeypatch) -> None:
    """Se il file immagine non c'è sul disco, si torna all'euristica."""
    from app.ml import condition_model
    from app.ml.condition_model import ConditionPrediction

    class FakeConditionClassifier:
        def is_available(self) -> bool:
            return True

        def predict_from_image(self, image_path):
            _ = image_path
            return ConditionPrediction("usurato", 0.8, {})

    monkeypatch.setattr(
        condition_model, "get_condition_classifier", lambda: FakeConditionClassifier()
    )

    old = (date.today() - timedelta(days=800)).isoformat()
    item = _create(client, png, category="t-shirt", purchase_date=old)
    # Cancella il file fisico
    (items_dir / item["image_path"]).unlink()

    body = client.post(f"/api/v1/items/{item['id']}/diagnose").json()
    assert body["source"] == "heuristic"
