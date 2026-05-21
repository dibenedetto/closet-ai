"""Test per l'endpoint di health check."""

from __future__ import annotations

from datetime import datetime


def test_health_returns_ok(client) -> None:
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["service"] == "closetai-backend"
    # time è ISO-8601 valido
    datetime.fromisoformat(body["time"].replace("Z", "+00:00"))
