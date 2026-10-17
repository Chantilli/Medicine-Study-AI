import json

import pytest
from fastapi.testclient import TestClient

import api


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(api, "STATIC_DIR", tmp_path / "dist")
    with TestClient(api.app) as test_client:
        yield test_client


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_calculator_delegates_to_existing_module(client):
    response = client.post(
        "/api/calculadoras",
        json={"operacion": "imc", "parametros": {"peso_kg": 70, "altura_cm": 175}},
    )
    assert response.status_code == 200
    assert response.json()["valor"] == 22.9


def test_sse_blocks_emergency_before_groq(client, monkeypatch):
    called = {"value": False}

    def fail_if_called(*args, **kwargs):
        called["value"] = True
        raise AssertionError("Groq no debe recibir emergencias")

    monkeypatch.setattr(api, "crear_completions_streaming", fail_if_called)
    response = client.post(
        "/api/chat/stream",
        json={"mensaje": "Yo tengo dolor toracico y no puedo respirar"},
    )
    assert response.status_code == 200
    assert "event: emergency" in response.text
    assert called["value"] is False
