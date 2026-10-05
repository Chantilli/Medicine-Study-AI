from types import SimpleNamespace

import citas_evidencia
import config
import historial_utils


def test_historial_no_reinyecta_contexto_y_migra_historial_viejo():
    historial = [
        {"role": "system", "content": "sistema"},
        {"role": "user", "content": "PDF enorme\nPregunta: ¿Qué es la anemia?"},
        {"role": "assistant", "content": "Respuesta limpia"},
    ]

    mensajes = historial_utils.construir_mensajes_con_contexto_actual(
        historial, "¿Y cómo se clasifica?", "PAPER ACTUAL"
    )

    assert "PDF enorme" not in mensajes[1]["content"]
    assert "PAPER ACTUAL" in mensajes[-1]["content"]
    assert mensajes[-1]["content"].endswith("¿Y cómo se clasifica?")
    assert historial_utils.preparar_historial_para_guardar(historial) == [
        {"role": "user", "content": "¿Qué es la anemia?"},
        {"role": "assistant", "content": "Respuesta limpia"},
    ]


def test_revision_consolida_auditoria_en_una_llamada(monkeypatch):
    llamadas = []

    def fake_call(*args, **kwargs):
        llamadas.append(kwargs)
        return SimpleNamespace(
            usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            choices=[SimpleNamespace(message=SimpleNamespace(content='{"problemas": [], "respuesta_corregida": "igual"}'))],
        )

    monkeypatch.setattr(citas_evidencia, "llamar_modelo_auxiliar", fake_call)
    respuesta = citas_evidencia.revisar_respuesta_con_ia("Respuesta", "Fuente")
    assert respuesta == "Respuesta"
    assert len(llamadas) == 1


def test_usage_registra_prompt_completion_total(monkeypatch):
    registrados = []
    monkeypatch.setattr(
        citas_evidencia,
        "client",
        None,
    )
    import auditoria
    monkeypatch.setattr(
        auditoria,
        "registrar_evento",
        lambda *args, **kwargs: registrados.append((args, kwargs)),
    )

    auditoria.registrar_uso_respuesta(
        7,
        "revision_evidencia",
        SimpleNamespace(
            usage=SimpleNamespace(prompt_tokens=11, completion_tokens=4, total_tokens=15)
        ),
        modelo="modelo-prueba",
    )

    assert registrados[0][1]["tokens_entrada"] == 11
    assert registrados[0][1]["tokens_salida"] == 4
    assert registrados[0][1]["tokens_total"] == 15


def test_seleccion_modelo_chat_sin_evidencia_usa_20b():
    modelo = config.seleccionar_modelo_chat(tiene_evidencia=False)
    assert modelo == config.MODELO_CHAT_RAPIDO
    assert modelo != config.MODELO_CHAT


def test_seleccion_modelo_chat_con_evidencia_y_riesgo_conserva_120b():
    assert config.seleccionar_modelo_chat(tiene_evidencia=True) == config.MODELO_CHAT
    assert config.seleccionar_modelo_chat(
        tiene_evidencia=False, categoria_riesgo="riesgo_personal"
    ) == config.MODELO_CHAT
    assert config.MODELO_CHAT == "openai/gpt-oss-120b"


class _FakeCompletions:
    def __init__(self, acepta_stream_options):
        self.llamadas = []
        self.acepta_stream_options = acepta_stream_options

    def create(self, **kwargs):
        self.llamadas.append(kwargs)
        if not self.acepta_stream_options and "stream_options" in kwargs:
            raise TypeError("got an unexpected keyword argument 'stream_options'")
        return "stream"


class _FakeClient:
    def __init__(self, acepta_stream_options):
        completions = _FakeCompletions(acepta_stream_options)
        self.chat = SimpleNamespace(completions=completions)
        self.completions = completions


def test_streaming_omite_stream_options_en_cliente_antiguo():
    cliente = _FakeClient(False)
    respuesta = config.crear_completions_streaming(
        cliente, model="modelo", messages=[], stream=True
    )
    assert respuesta == "stream"
    assert "stream_options" not in cliente.completions.llamadas[-1]


def test_streaming_incluye_usage_en_cliente_compatible():
    cliente = _FakeClient(True)
    respuesta = config.crear_completions_streaming(
        cliente, model="modelo", messages=[], stream=True
    )
    assert respuesta == "stream"
    assert cliente.completions.llamadas[-1]["stream_options"] == {"include_usage": True}
