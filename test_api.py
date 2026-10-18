import uuid

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


def test_auth_and_chat_persistence(client):
    username = f"api_test_{uuid.uuid4().hex[:10]}"
    registered = client.post("/api/auth/register", json={"usuario": username, "password": "test1234"})
    assert registered.status_code == 200
    user_id = registered.json()["usuario_id"]
    logged = client.post("/api/auth/login", json={"usuario": username, "password": "test1234"})
    assert logged.json()["usuario_id"] == user_id
    saved = client.post(
        "/api/chats/chat-api",
        json={"usuario_id": user_id, "titulo": "Repaso", "mensajes": [{"role": "user", "content": "IMC"}]},
    )
    assert saved.status_code == 200
    loaded = client.get("/api/chats/chat-api", params={"usuario_id": user_id})
    assert loaded.json()["mensajes"][0]["content"] == "IMC"


def test_material_and_interactions_routes(client, monkeypatch):
    monkeypatch.setattr(api, "generar_flashcards_con_ia", lambda *args: ([{"id": 1}], None))
    monkeypatch.setattr(api, "generar_examen_con_ia", lambda *args: ([{"id": 1}], None))
    cards = client.post(
        "/api/flashcards/generate",
        json={"usuario_id": 1, "texto_fuente": "farmacología"},
    )
    exam = client.post(
        "/api/examenes/generate",
        json={"usuario_id": 1, "texto_fuente": "farmacología"},
    )
    assert cards.json()["flashcards"] == [{"id": 1}]
    assert exam.json()["preguntas"] == [{"id": 1}]
    interaction = client.post("/api/interacciones", json={"farmacos": ["warfarina", "ibuprofeno"]})
    assert interaction.status_code == 200


def test_upload_rejects_non_pdf(client):
    response = client.post(
        "/api/uploads/pdf",
        data={"usuario_id": "1"},
        files={"archivo": ("notes.txt", b"not a pdf", "text/plain")},
    )
    assert response.status_code == 415
