"""API HTTP de Medicine Study AI.

La lógica clínica y de recuperación sigue viviendo en los módulos existentes;
este archivo solo adapta esas funciones a HTTP y SSE para el frontend React.
"""
from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any, Iterator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from calculadoras_clinicas import (
    calcular_aclaramiento_creatinina,
    calcular_dosis_por_peso,
    calcular_egfr_ckd_epi,
    calcular_imc,
    calcular_superficie_corporal,
    obtener_ajuste_renal,
)
from clasificador_riesgo_clinico import (
    aviso_riesgo_personal,
    clasificar_consulta,
    instruccion_refuerzo_riesgo_personal,
    mensaje_emergencia_medica,
    mensaje_emergencia_salud_mental,
)
from config import (
    MAX_TOKENS_RESPUESTA,
    construir_system_prompt,
    crear_completions_streaming,
    seleccionar_modelo_chat,
)
from historial_utils import construir_mensajes_con_contexto_actual
from database import (
    crear_usuario,
    inicializar_db,
    obtener_usuario_por_nombre,
    verificar_password,
)
from pubmed_search import (
    buscar_pubmed_estructurado,
    filtrar_papers_por_evidencia,
)

try:
    from config import client
except Exception:
    client = None

try:
    from rag_embeddings import buscar_fragmentos_relevantes
except Exception:
    buscar_fragmentos_relevantes = None


BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / "frontend" / "dist"
ANONYMOUS_USER = "_api_anonymous"

app = FastAPI(title="Medicine Study AI API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AuthRequest(BaseModel):
    usuario: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=4, max_length=200)


class ChatRequest(BaseModel):
    mensaje: str = Field(min_length=1, max_length=12000)
    usuario_id: int | None = None
    idioma: str = Field(default="es", pattern="^(es|en|fr|de|zh)$")
    buscar_evidencia: bool = True
    modo_evidencia: str = "todos"
    historial: list[dict[str, str]] = Field(default_factory=list)


class CalculatorRequest(BaseModel):
    operacion: str
    parametros: dict[str, Any] = Field(default_factory=dict)


@app.on_event("startup")
def startup() -> None:
    inicializar_db()
    crear_usuario(ANONYMOUS_USER, uuid.uuid4().hex)


def _anonymous_user_id() -> int:
    fila = obtener_usuario_por_nombre(ANONYMOUS_USER)
    if fila:
        return int(fila[0])
    inicializar_db()
    usuario_id, error = crear_usuario(ANONYMOUS_USER, uuid.uuid4().hex)
    if error or usuario_id is None:
        raise HTTPException(status_code=500, detail="No se pudo inicializar el usuario API")
    return int(usuario_id)


def _sse(event: str, data: Any) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "groq_configurado": client is not None}


@app.post("/api/auth/register")
def register(payload: AuthRequest) -> dict[str, Any]:
    usuario_id, error = crear_usuario(payload.usuario.strip(), payload.password)
    if error:
        raise HTTPException(status_code=409, detail=error)
    return {"usuario_id": usuario_id, "usuario": payload.usuario.strip()}


@app.post("/api/auth/login")
def login(payload: AuthRequest) -> dict[str, Any]:
    fila = obtener_usuario_por_nombre(payload.usuario.strip())
    if not fila or not verificar_password(payload.password, fila[1]):
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")
    return {"usuario_id": int(fila[0]), "usuario": payload.usuario.strip()}


def _prepare_chat(payload: ChatRequest) -> tuple[dict[str, Any], Iterator[str]]:
    usuario_id = payload.usuario_id or _anonymous_user_id()
    clasificacion = clasificar_consulta(payload.mensaje)
    if clasificacion["categoria"] == "emergencia":
        subtipo = clasificacion.get("subtipo")
        texto = (
            mensaje_emergencia_salud_mental(payload.idioma)
            if subtipo == "salud_mental"
            else mensaje_emergencia_medica(payload.idioma)
        )
        return {"clasificacion": clasificacion, "emergencia": texto}, iter(())

    def stream() -> Iterator[str]:
        yield _sse("meta", {"clasificacion": clasificacion})
        contexto_pubmed = ""
        papers = []
        if payload.buscar_evidencia:
            try:
                papers, _, total, debug, estado = buscar_pubmed_estructurado(
                    payload.mensaje, usuario_id
                )
                papers = filtrar_papers_por_evidencia(papers, payload.modo_evidencia)
                contexto_pubmed = "\n\n".join(
                    f"[{index}] {paper.get('titulo', '')}\n{paper.get('resumen', '')}"
                    for index, paper in enumerate(papers, start=1)
                )
                yield _sse(
                    "evidence",
                    {"papers": papers, "total": total, "debug": debug, "estado": estado},
                )
            except Exception as exc:
                yield _sse("warning", {"message": f"No se pudo consultar evidencia: {exc}"})

        bloque_pdf = ""
        if client is not None and buscar_fragmentos_relevantes is not None:
            try:
                fragmentos = buscar_fragmentos_relevantes(usuario_id, payload.mensaje)
                bloque_pdf = "\n\n".join(
                    f"[F{i}] {fuente}\n{texto}"
                    for i, (_, fuente, texto, _) in enumerate(fragmentos, start=1)
                )
            except Exception as exc:
                yield _sse("warning", {"message": f"No se pudo consultar el PDF: {exc}"})

        if client is None:
            yield _sse("error", {"message": "GROQ_API_KEY no está configurada."})
            return

        sufijo = (
            instruccion_refuerzo_riesgo_personal(payload.idioma)
            if clasificacion["categoria"] == "riesgo_personal"
            else ""
        )
        contexto = f"{bloque_pdf}\n{contexto_pubmed}".strip()
        modelo = seleccionar_modelo_chat(
            tiene_evidencia=bool(contexto),
            categoria_riesgo=clasificacion["categoria"],
        )
        historial = [
            {"role": item["role"], "content": item["content"]}
            for item in payload.historial[-16:]
            if item.get("role") in {"user", "assistant"}
        ]
        messages = construir_mensajes_con_contexto_actual(
            [construir_system_prompt(payload.idioma, payload.mensaje), *historial],
            f"{payload.mensaje}{sufijo}",
            contexto,
        )
        messages[0] = construir_system_prompt(payload.idioma, payload.mensaje)
        try:
            response = crear_completions_streaming(
                client,
                model=modelo,
                messages=messages,
                temperature=0.0,
                max_tokens=MAX_TOKENS_RESPUESTA,
                stream=True,
            )
            texto_completo = ""
            for chunk in response:
                choices = getattr(chunk, "choices", None) or []
                if not choices:
                    continue
                delta = getattr(choices[0].delta, "content", None)
                if delta:
                    texto_completo += delta
                    yield _sse("token", {"content": delta})
            yield _sse("done", {"content": texto_completo, "modelo": modelo})
        except Exception as exc:
            yield _sse("error", {"message": f"Error al consultar Groq: {exc}"})

    return {"clasificacion": clasificacion}, stream()


@app.post("/api/chat/stream")
def chat_stream(payload: ChatRequest):
    initial, stream = _prepare_chat(payload)
    if "emergencia" in initial:
        content = iter(
            [
                _sse("meta", {"clasificacion": initial["clasificacion"]}),
                _sse("emergency", {"content": initial["emergencia"]}),
                _sse("done", {"content": initial["emergencia"]}),
            ]
        )
        return StreamingResponse(content, media_type="text/event-stream")
    return StreamingResponse(stream, media_type="text/event-stream")


@app.post("/api/calculadoras")
def calculator(payload: CalculatorRequest) -> dict[str, Any]:
    p = payload.parametros
    operaciones = {
        "imc": lambda: calcular_imc(p["peso_kg"], p["altura_cm"], p.get("idioma", "es")),
        "superficie_corporal": lambda: calcular_superficie_corporal(
            p["peso_kg"], p["altura_cm"], p.get("formula", "mosteller"), p.get("idioma", "es")
        ),
        "aclaramiento_creatinina": lambda: calcular_aclaramiento_creatinina(
            p["edad"], p["peso_kg"], p["creatinina_mg_dl"], p["sexo"],
            p.get("altura_cm"), p.get("usar_peso_ajustado", False), p.get("idioma", "es"),
        ),
        "egfr": lambda: calcular_egfr_ckd_epi(
            p["edad"], p["creatinina_mg_dl"], p["sexo"], p.get("idioma", "es")
        ),
        "dosis_por_peso": lambda: calcular_dosis_por_peso(
            p["peso_kg"], p["mg_por_kg"], p.get("dosis_max_mg"), p.get("dosis_min_mg"),
            p.get("tomas_por_dia"), p.get("idioma", "es")
        ),
        "ajuste_renal": lambda: obtener_ajuste_renal(
            p["farmaco"], p["aclaramiento_ml_min"], p.get("idioma", "es")
        ),
    }
    if payload.operacion not in operaciones:
        raise HTTPException(status_code=400, detail="Operación no soportada")
    try:
        return operaciones[payload.operacion]()
    except KeyError as exc:
        raise HTTPException(status_code=422, detail=f"Falta el parámetro {exc.args[0]}") from exc
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/progreso")
def progress(usuario_id: int | None = None) -> dict[str, Any]:
    # El frontend puede sustituir este resumen por métricas reales sin cambiar el contrato.
    return {"usuario_id": usuario_id or _anonymous_user_id(), "series": [], "message": "Sin datos aún"}


if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")


@app.get("/{path:path}")
def frontend(path: str):
    requested = STATIC_DIR / path
    if path and requested.is_file():
        return FileResponse(requested)
    index = STATIC_DIR / "index.html"
    if index.exists():
        return FileResponse(index)
    raise HTTPException(status_code=404, detail="Frontend no construido")
