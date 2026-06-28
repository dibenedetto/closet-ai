"""Test della gap analysis del guardaroba (rete + fallback regole + endpoint)."""

from __future__ import annotations


def _create(client, png, **extra):
    data = {"name": extra.pop("name", "X"), **{k: str(v) for k, v in extra.items()}}
    r = client.post(
        "/api/v1/items",
        data=data,
        files={"image": ("a.png", png(), "image/png")},
    )
    assert r.status_code == 201, r.text
    return r.json()


# ----- feature engineering & regole (unit) ---------------------------------


def test_features_from_counts_basic() -> None:
    from app.ml.gap_model import FEATURE_NAMES, features_from_counts

    counts = {"t-shirt": 4, "jeans": 2, "giacca": 1, "scarpe": 3}
    feats = features_from_counts(counts, n_colors=4, has_neutral=True, ghost_ratio=0.2)
    assert set(feats.keys()) == set(FEATURE_NAMES)
    assert feats["n_total"] == 10
    assert feats["n_top"] == 4  # solo t-shirt è "top" qui
    assert feats["n_outerwear"] == 1
    assert abs(feats["frac_tshirt"] - 0.4) < 1e-6
    assert feats["has_neutral"] == 1.0


def test_build_mlp_multilabel_shape() -> None:
    import torch

    from app.ml.gap_model import GAP_LABELS, FEATURE_NAMES, build_mlp

    model = build_mlp()
    out = model(torch.zeros(2, len(FEATURE_NAMES)))
    assert out.shape == (2, len(GAP_LABELS))


def test_rules_flag_unbalanced_wardrobe() -> None:
    from app.ml.gap_model import rule_based_gaps

    # tante t-shirt, niente capospalla/scarpe/formale, monocromo
    counts = {"t-shirt": 12, "jeans": 1}
    gaps = rule_based_gaps(counts, n_colors=1, has_neutral=False, ghost_ratio=0.1)
    assert "manca_capospalla" in gaps
    assert "manca_scarpe" in gaps
    assert "manca_formale" in gaps
    assert "troppe_tshirt" in gaps
    assert "poca_varieta_colori" in gaps


def test_rules_balanced_wardrobe_has_no_gaps() -> None:
    from app.ml.gap_model import rule_based_gaps

    counts = {
        "t-shirt": 4, "camicia": 3, "maglione": 3, "giacca": 2, "cappotto": 1,
        "jeans": 3, "pantaloni": 3, "scarpe": 4, "vestito": 2, "sciarpa": 2,
    }
    gaps = rule_based_gaps(counts, n_colors=5, has_neutral=True, ghost_ratio=0.15)
    assert gaps == set()


def test_gap_classifier_none_without_weights() -> None:
    from app.ml.gap_model import get_gap_classifier

    assert get_gap_classifier() is None


# ----- endpoint ------------------------------------------------------------


def test_gap_endpoint_empty_wardrobe(client) -> None:
    body = client.get("/api/v1/stats/gap-analysis").json()
    assert body["total_items"] == 0
    assert body["source"] == "rules"  # nessun peso nei test
    # guardaroba vuoto: le regole segnalano comunque i vuoti base
    assert isinstance(body["gaps"], list)


def test_gap_endpoint_detects_gaps_on_unbalanced(client, png) -> None:
    for i in range(12):
        _create(client, png, name=f"tee{i}", category="t-shirt", color="blu")
    _create(client, png, name="jeans", category="jeans", color="blu")

    body = client.get("/api/v1/stats/gap-analysis").json()
    assert body["total_items"] == 13
    assert body["balanced"] is False
    codes = {g["code"] for g in body["gaps"]}
    assert "manca_capospalla" in codes
    assert "troppe_tshirt" in codes
    assert "poca_varieta_colori" in codes
    # ogni vuoto ha un consiglio testuale
    assert all(g["advice"] for g in body["gaps"])


def test_gap_endpoint_excludes_retired_items(client, png) -> None:
    # guardaroba bilanciato, ma "ritiriamo" la giacca → manca_capospalla riappare
    _create(client, png, name="camicia", category="camicia", color="bianco")
    _create(client, png, name="camicia2", category="camicia", color="nero")
    _create(client, png, name="jeans", category="jeans", color="blu")
    _create(client, png, name="scarpe", category="scarpe", color="nero")
    _create(client, png, name="scarpe2", category="scarpe", color="bianco")
    giacca = _create(client, png, name="giacca", category="giacca", color="grigio")

    before = client.get("/api/v1/stats/gap-analysis").json()
    assert "manca_capospalla" not in {g["code"] for g in before["gaps"]}

    client.post(f"/api/v1/items/{giacca['id']}/actions", json={"action_type": "donazione"})

    after = client.get("/api/v1/stats/gap-analysis").json()
    assert after["total_items"] == before["total_items"] - 1
    assert "manca_capospalla" in {g["code"] for g in after["gaps"]}


def test_gap_endpoint_uses_neural_net_when_weights_present(client, png, monkeypatch) -> None:
    """Con un classifier montato, la source diventa 'neural-net' e usa le probabilità."""
    from app.ml.gap_model import GAP_LABELS, GapPrediction
    from app.services import gap_analysis

    class FakeGapClf:
        def predict(self, feats):
            _ = feats
            return GapPrediction(
                gaps=["manca_capospalla"],
                probabilities={lab: (0.9 if lab == "manca_capospalla" else 0.1)
                               for lab in GAP_LABELS},
                balanced=False,
                source="neural-net",
            )

    # `gap_analysis` importa il factory a livello modulo: patchiamo lì.
    monkeypatch.setattr(gap_analysis, "get_gap_classifier", lambda: FakeGapClf())

    _create(client, png, name="tee", category="t-shirt", color="blu")
    body = client.get("/api/v1/stats/gap-analysis").json()
    assert body["source"] == "neural-net"
    cap = next(g for g in body["gaps"] if g["code"] == "manca_capospalla")
    assert cap["probability"] == 0.9
