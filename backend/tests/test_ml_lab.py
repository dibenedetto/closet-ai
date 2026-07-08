"""Test per gli endpoint della pagina tecnica ML Lab."""

from __future__ import annotations


def test_models_status_lists_two_models(client) -> None:
    body = client.get("/api/v1/ml/models").json()
    keys = {m["key"] for m in body["models"]}
    assert keys == {"condition-mlp", "gap-mlp"}
    # Nei test i pesi puntano a path inesistenti → tutto non disponibile.
    assert all(m["available"] is False for m in body["models"])
    # Ogni modello dichiara natura e comando di training.
    for m in body["models"]:
        assert m["nature"] == "own"
        assert m["train_command"].startswith("uv run")


def test_models_status_includes_datasets(client) -> None:
    body = client.get("/api/v1/ml/models").json()
    keys = {d["key"] for d in body["datasets"]}
    assert keys == {"garment_condition", "wardrobe"}
    for d in body["datasets"]:
        assert d["build_command"].startswith("uv run")


def test_condition_predict_503_when_not_trained(client, png) -> None:
    r = client.post(
        "/api/v1/ml/condition/predict",
        files={"image": ("a.png", png(), "image/png")},
    )
    assert r.status_code == 503
    assert "train_condition_model" in r.json()["detail"]


def test_condition_predict_with_fake_classifier(client, png, monkeypatch) -> None:
    from app.ml import condition_model
    from app.ml.condition_model import ConditionPrediction

    class FakeClf:
        def predict_from_image(self, image_path):
            _ = image_path
            return ConditionPrediction(
                condition="usurato",
                confidence=0.77,
                probabilities={"buono": 0.2, "usurato": 0.77, "danneggiato": 0.03},
            )

    monkeypatch.setattr(condition_model, "get_condition_classifier", lambda: FakeClf())

    r = client.post(
        "/api/v1/ml/condition/predict",
        files={"image": ("a.png", png(), "image/png")},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["condition"] == "usurato"
    assert body["confidence"] == 0.77
    assert set(body["probabilities"]) == {"buono", "usurato", "danneggiato"}


def test_condition_predict_rejects_bad_mime(client, monkeypatch) -> None:
    from app.ml import condition_model

    class FakeClf:
        def predict_from_image(self, image_path): ...

    monkeypatch.setattr(condition_model, "get_condition_classifier", lambda: FakeClf())
    r = client.post(
        "/api/v1/ml/condition/predict",
        files={"image": ("a.pdf", b"%PDF", "application/pdf")},
    )
    assert r.status_code == 400


def test_gap_predict_rules_fallback(client) -> None:
    r = client.post(
        "/api/v1/ml/gap/predict",
        json={"counts": {"t-shirt": 12, "jeans": 1}, "n_colors": 1,
              "has_neutral": False, "ghost_ratio": 0.1},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["source"] == "rules"  # niente pesi nei test
    assert "manca_capospalla" in body["gaps"]
    assert "troppe_tshirt" in body["gaps"]
    # Le label leggibili accompagnano i codici
    assert body["labels"]["manca_capospalla"].startswith("Manca")


def test_gap_predict_balanced_wardrobe(client) -> None:
    counts = {
        "t-shirt": 4, "camicia": 3, "maglione": 3, "giacca": 2, "cappotto": 1,
        "jeans": 3, "pantaloni": 3, "scarpe": 4, "vestito": 2, "sciarpa": 2,
    }
    r = client.post(
        "/api/v1/ml/gap/predict",
        json={"counts": counts, "n_colors": 5, "has_neutral": True, "ghost_ratio": 0.15},
    )
    body = r.json()
    assert body["balanced"] is True
    assert body["gaps"] == []


def test_confusion_matrix_404_when_missing(client, monkeypatch, tmp_path) -> None:
    from app.routers import ml_lab

    monkeypatch.setattr(ml_lab, "CONFUSION_MATRIX_PNG", tmp_path / "nope.png")
    r = client.get("/api/v1/ml/condition/confusion-matrix")
    assert r.status_code == 404
