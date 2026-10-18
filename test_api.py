import uuid
from types import SimpleNamespace

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
    monkeypatch.setattr(api, "verificar_limite", lambda *args, **kwargs: {"permitido": True})

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
    monkeypatch.setattr(api, "verificar_limite", lambda *args, **kwargs: {"permitido": True})
    monkeypatch.setattr(api, "registrar_solicitud", lambda *args, **kwargs: None)
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


def test_options_exposes_legacy_controls(client):
    result = client.get("/api/options")
    assert result.status_code == 200
    body = result.json()
    assert {item["codigo"] for item in body["idiomas"]} == {"es", "en", "fr", "de", "zh"}
    assert "todo" in body["modos_evidencia"]
    assert "chat" in body["limites"]


def test_interaction_ai_route_delegates(client, monkeypatch):
    monkeypatch.setattr(api, "analizar_interaccion_con_ia", lambda *args, **kwargs: {"disponible": True, "texto": "ok"})
    response = client.post(
        "/api/interacciones/ia",
        json={"farmaco_a": "warfarina", "farmaco_b": "ibuprofeno", "idioma": "es"},
    )
    assert response.status_code == 200
    assert response.json()["disponible"] is True


def test_feedback_and_audit_routes(client, monkeypatch):
    monkeypatch.setattr(api, "registrar_feedback", lambda *args, **kwargs: True)
    feedback = client.post(
        "/api/feedback",
        json={
            "usuario_id": 1,
            "chat_id": "chat",
            "pregunta": "IMC",
            "respuesta": "Respuesta educativa",
            "valoracion": 1,
        },
    )
    assert feedback.status_code == 200
    assert feedback.json()["saved"] is True
    assert client.get("/api/auditoria?usuario_id=1").status_code == 200
    assert client.get("/api/feedback/summary").status_code == 200


def test_feedback_route_persists_real_vote(client):
    chat_id = f"feedback-{uuid.uuid4().hex}"
    response = client.post(
        "/api/feedback",
        json={
            "usuario_id": 1,
            "chat_id": chat_id,
            "pregunta": "¿Qué es el IMC?",
            "respuesta": "Es una relación entre peso y talla.",
            "valoracion": -1,
            "fuentes": [{"titulo": "Fuente educativa"}],
            "idioma": "es",
        },
    )
    assert response.status_code == 200
    assert response.json()["saved"] is True
    rows = api.resumen_feedback(365)
    assert rows["negativos"] >= 1


def test_icd_route_enforces_user_limit_and_delegates(client, monkeypatch):
    monkeypatch.setattr(api, "verificar_limite", lambda *args, **kwargs: {"permitido": True})
    monkeypatch.setattr(api, "registrar_solicitud", lambda *args, **kwargs: None)
    monkeypatch.setattr(api, "construir_glosario_icd11", lambda *args: {"estado": "ok", "terminos_encontrados": []})
    response = client.post(
        "/api/icd11",
        json={"usuario_id": 1, "pregunta": "diabetes mellitus", "idioma": "es"},
    )
    assert response.status_code == 200
    assert response.json()["estado"] == "ok"


def test_pubmed_route_delegates_and_filters(client, monkeypatch):
    monkeypatch.setattr(api, "verificar_limite", lambda *args, **kwargs: {"permitido": True})
    monkeypatch.setattr(api, "registrar_solicitud", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        api,
        "buscar_pubmed_estructurado",
        lambda *args: ([{"titulo": "Paper", "tipos_publicacion": ["Randomized Controlled Trial"]}], 1, 1, [], {"estado": "ok"}),
    )
    response = client.post(
        "/api/search/pubmed",
        json={"usuario_id": 1, "consulta": "diabetes"},
    )
    assert response.status_code == 200
    assert response.json()["papers"][0]["titulo"] == "Paper"


def test_chat_stream_uses_groq_and_persists_legacy_history(client, monkeypatch):
    username = f"stream_{uuid.uuid4().hex[:10]}"
    user_id = client.post(
        "/api/auth/register", json={"usuario": username, "password": "test1234"}
    ).json()["usuario_id"]
    monkeypatch.setattr(api, "client", object())
    monkeypatch.setattr(api, "buscar_pubmed_estructurado", lambda *args: ([], 0, 0, [], {"estado": "ok"}))
    monkeypatch.setattr(api, "buscar_fragmentos_relevantes", lambda *args: [])
    monkeypatch.setattr(api, "construir_glosario_icd11", lambda *args: {"terminos_encontrados": [], "bloque_contexto": ""})
    monkeypatch.setattr(api, "generar_titulo_con_ia", lambda *args, **kwargs: "Consulta de estudio")
    monkeypatch.setattr(
        api,
        "crear_completions_streaming",
        lambda *args, **kwargs: iter([
            SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="Respuesta "))]),
            SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="real"))]),
        ]),
    )
    response = client.post(
        "/api/chat/stream",
        json={
            "usuario_id": user_id,
            "chat_id": "persisted-stream-chat",
            "mensaje": "Explica el ciclo cardiaco",
            "buscar_pubmed": False,
        },
    )
    assert response.status_code == 200
    assert "event: token" in response.text
    assert '"content": "Respuesta real"' in response.text
    assert "event: persistence" in response.text
    saved = client.get(
        "/api/chats/persisted-stream-chat", params={"usuario_id": user_id}
    )
    assert saved.status_code == 200
    assert saved.json()["mensajes"][-1]["content"] == "Respuesta real"


def test_missing_chat_is_not_reported_as_empty_success(client):
    response = client.get("/api/chats/does-not-exist", params={"usuario_id": 1})
    assert response.status_code == 404
