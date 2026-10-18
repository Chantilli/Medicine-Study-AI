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

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
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
from auditoria import obtener_resumen_auditoria, registrar_evento
from citas_evidencia import (
    construir_contexto_para_juez,
    construir_lista_fuentes,
    detectar_citas_alucinadas,
    detectar_citas_fuera_de_rango,
    evaluar_factualidad,
    formatear_contexto_papers,
    normalizar_citas_pmid,
    resumen_evidencia_citada,
    revisar_respuesta_con_ia,
    sincronizar_referencias_con_papers,
    verificar_consistencia_fisiologica,
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
    eliminar_chat_db,
    guardar_chat_db,
    inicializar_db,
    obtener_mensajes_chat,
    obtener_todos_los_chats,
    obtener_usuario_por_nombre,
    verificar_password,
)
from examenes import (
    generar_examen_con_ia,
    obtener_preguntas_examen,
    registrar_intento,
)
from flashcards import (
    contar_flashcards_pendientes,
    generar_flashcards_con_ia,
    obtener_flashcards_pendientes,
    registrar_repaso,
)
from interacciones_farmacologicas import verificar_interacciones
from interacciones_farmacologicas import analizar_interaccion_con_ia
from icd11_terminologia import construir_glosario_icd11
from extraccion_tablas import extraer_tablas_pdf
from feedback import registrar_feedback, resumen_feedback
from limite_uso import LIMITES, registrar_solicitud, verificar_limite
from memoria_estudiante import evaluar_nivel_por_tema, resumen_progreso
from ocr_pdf import extraer_texto_pdf_con_ocr
from pubmed_search import (
    buscar_pubmed_estructurado,
    buscar_europepmc,
    buscar_semantic_scholar,
    filtrar_papers_por_evidencia,
)
from rag_embeddings import guardar_fragmentos_pdf
from seguridad_prompt_injection import sanitizar_texto_pdf
from seguridad_prompt_injection import resumir_alertas
from config import IDIOMAS, MAX_PDF_BYTES, MAX_PDF_PAGINAS, UPLOAD_DIR

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
    buscar_pubmed: bool | None = None
    verificar_factualidad: bool = True
    modo_evidencia: str = "todo"
    historial: list[dict[str, str]] = Field(default_factory=list)


class CalculatorRequest(BaseModel):
    operacion: str
    parametros: dict[str, Any] = Field(default_factory=dict)


class UserRequest(BaseModel):
    usuario_id: int


class GenerateRequest(UserRequest):
    texto_fuente: str = Field(min_length=1, max_length=12000)
    tema: str | None = None
    fuente: str | None = None
    n: int = Field(default=5, ge=1, le=20)
    idioma: str = Field(default="es", pattern="^(es|en|fr|de|zh)$")


class ReviewRequest(UserRequest):
    flashcard_id: int
    boton: str


class ExamAttemptRequest(UserRequest):
    pregunta_id: int
    correcta: bool


class ChatSaveRequest(UserRequest):
    titulo: str = Field(default="Nuevo chat", max_length=120)
    mensajes: list[dict[str, str]] = Field(default_factory=list)


class InteractionRequest(BaseModel):
    farmacos: list[str] = Field(min_length=1, max_length=20)
    idioma: str = Field(default="es", pattern="^(es|en|fr|de|zh)$")


class InteractionAiRequest(BaseModel):
    farmaco_a: str = Field(min_length=1, max_length=120)
    farmaco_b: str = Field(min_length=1, max_length=120)
    idioma: str = Field(default="es", pattern="^(es|en|fr|de|zh)$")


class FeedbackRequest(BaseModel):
    usuario_id: int
    chat_id: str | None = None
    pregunta: str = Field(min_length=1, max_length=12000)
    respuesta: str = Field(min_length=1, max_length=50000)
    valoracion: int = Field(ge=-1, le=1)
    fuentes: list[dict[str, Any]] | None = None
    idioma: str = Field(default="es", pattern="^(es|en|fr|de|zh)$")


class SearchRequest(BaseModel):
    consulta: str = Field(min_length=2, max_length=500)
    usuario_id: int
    idioma: str = Field(default="es", pattern="^(es|en|fr|de|zh)$")
    modo_evidencia: str = "todo"
    limite: int = Field(default=10, ge=1, le=30)
    rango_anios: tuple[int, int] | None = None


class IcdRequest(BaseModel):
    pregunta: str = Field(min_length=2, max_length=12000)
    usuario_id: int
    idioma: str = Field(default="es", pattern="^(es|en|fr|de|zh)$")


class UsageRequest(BaseModel):
    usuario_id: int
    tipo: str
    idioma: str = Field(default="es", pattern="^(es|en|fr|de|zh)$")


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


@app.get("/api/chats")
def list_chats(usuario_id: int) -> list[dict[str, Any]]:
    return [
        {"id": chat[0], "titulo": chat[1]}
        for chat in obtener_todos_los_chats(usuario_id)
    ]


@app.get("/api/chats/{chat_id}")
def get_chat(chat_id: str, usuario_id: int) -> dict[str, Any]:
    mensajes = obtener_mensajes_chat(chat_id, usuario_id)
    if mensajes is None:
        raise HTTPException(status_code=404, detail="Chat no encontrado")
    return {"id": chat_id, "mensajes": mensajes}


@app.post("/api/chats/{chat_id}")
def save_chat(chat_id: str, payload: ChatSaveRequest) -> dict[str, Any]:
    guardar_chat_db(chat_id, payload.titulo[:120], payload.mensajes, payload.usuario_id)
    return {"id": chat_id, "saved": True}


@app.delete("/api/chats/{chat_id}")
def delete_chat(chat_id: str, usuario_id: int) -> dict[str, bool]:
    eliminar_chat_db(chat_id, usuario_id)
    return {"deleted": True}


def _prepare_chat(payload: ChatRequest) -> tuple[dict[str, Any], Iterator[str]]:
    usuario_id = payload.usuario_id or _anonymous_user_id()
    usar_pubmed = payload.buscar_evidencia if payload.buscar_pubmed is None else payload.buscar_pubmed
    limite_chat = verificar_limite(usuario_id, "chat", payload.idioma)
    if not limite_chat["permitido"]:
        return {"limit": limite_chat}, iter(())
    registrar_solicitud(usuario_id, "chat")
    clasificacion = clasificar_consulta(payload.mensaje)
    if clasificacion["categoria"] == "emergencia":
        subtipo = clasificacion.get("subtipo")
        texto = (
            mensaje_emergencia_salud_mental(payload.idioma)
            if subtipo == "salud_mental"
            else mensaje_emergencia_medica(payload.idioma)
        )
        registrar_evento(
            usuario_id, f"chat_emergencia_{clasificacion.get('subtipo') or 'medica'}",
            estado="bloqueado", texto_consulta=payload.mensaje,
        )
        return {"clasificacion": clasificacion, "emergencia": texto}, iter(())

    def stream() -> Iterator[str]:
        yield _sse("meta", {"clasificacion": clasificacion})
        if clasificacion["categoria"] == "riesgo_personal":
            yield _sse("risk", {"message": aviso_riesgo_personal(payload.idioma)})
        contexto_pubmed = ""
        papers = []
        fragmentos = []
        if usar_pubmed:
            limite_pubmed = verificar_limite(usuario_id, "pubmed", payload.idioma)
            if not limite_pubmed["permitido"]:
                yield _sse("warning", {"message": limite_pubmed["motivo"], "tipo": "pubmed"})
            else:
                registrar_solicitud(usuario_id, "pubmed")
                try:
                    papers, _, total, debug, estado = buscar_pubmed_estructurado(
                        payload.mensaje, usuario_id
                    )
                    papers = filtrar_papers_por_evidencia(papers, payload.modo_evidencia)
                    contexto_pubmed = formatear_contexto_papers(papers, payload.idioma)
                    yield _sse(
                        "evidence",
                        {"papers": papers, "total": total, "debug": debug, "estado": estado},
                    )
                except Exception as exc:
                    yield _sse("warning", {"message": f"No se pudo consultar evidencia: {exc}", "tipo": "pubmed"})

        bloque_pdf = ""
        if client is not None and buscar_fragmentos_relevantes is not None:
            try:
                fragmentos = buscar_fragmentos_relevantes(usuario_id, payload.mensaje)
                bloque_pdf = "\n\n".join(
                    f"[F{i}] {fuente}\n{texto}"
                    for i, (_, fuente, texto, _) in enumerate(fragmentos, start=1)
                )
                if fragmentos:
                    yield _sse("retrieval", {"fragmentos": len(fragmentos)})
            except Exception as exc:
                yield _sse("warning", {"message": f"No se pudo consultar el PDF: {exc}"})

        if client is None:
            yield _sse("error", {"message": "GROQ_API_KEY no está configurada."})
            return

        bloque_icd11 = ""
        if payload.idioma != "en":
            limite_icd = verificar_limite(usuario_id, "icd11", payload.idioma)
            if limite_icd["permitido"]:
                registrar_solicitud(usuario_id, "icd11")
                try:
                    glosario = construir_glosario_icd11(payload.mensaje, payload.idioma)
                    bloque_icd11 = glosario.get("bloque_contexto", "")
                    yield _sse("icd11", glosario)
                except Exception as exc:
                    yield _sse("warning", {"message": f"No se pudo consultar ICD-11: {exc}", "tipo": "icd11"})

        sufijo = (
            instruccion_refuerzo_riesgo_personal(payload.idioma)
            if clasificacion["categoria"] == "riesgo_personal"
            else ""
        )
        contexto = f"{bloque_pdf}\n{contexto_pubmed}\n{bloque_icd11}".strip()
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
        started = time.time()
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
            respuesta_final = texto_completo
            if papers or fragmentos:
                contexto_revision = construir_contexto_para_juez(contexto_pubmed, bloque_pdf)
                try:
                    respuesta_final = revisar_respuesta_con_ia(
                        respuesta_final, contexto_revision, payload.idioma
                    )
                    respuesta_final = normalizar_citas_pmid(respuesta_final, papers)
                    respuesta_final = sincronizar_referencias_con_papers(
                        respuesta_final, papers, payload.idioma
                    )
                except Exception as exc:
                    yield _sse("warning", {"message": f"No se pudo verificar citas: {exc}", "tipo": "citas"})
                fuera = detectar_citas_fuera_de_rango(
                    respuesta_final, len(papers), len(fragmentos)
                )
                if fuera["papers_invalidos"] or fuera["fragmentos_invalidos"]:
                    yield _sse("warning", {"message": "La respuesta contiene citas fuera de rango.", "citas": fuera})
                if detectar_citas_alucinadas(respuesta_final, len(papers), len(fragmentos)):
                    yield _sse("warning", {"message": "La respuesta contiene referencias no verificables.", "tipo": "citas"})
                contradicciones = verificar_consistencia_fisiologica(
                    payload.mensaje, respuesta_final
                )
                if contradicciones:
                    yield _sse("physiology", {"contradicciones": contradicciones})
                fuentes = construir_lista_fuentes(papers, fragmentos, respuesta_final)
                yield _sse("sources", {"fuentes": fuentes, "resumen": resumen_evidencia_citada(fuentes)})
                if payload.verificar_factualidad and fuentes:
                    try:
                        fact = evaluar_factualidad(
                            respuesta_final,
                            construir_contexto_para_juez(contexto_pubmed, bloque_pdf),
                        )
                        yield _sse("factuality", fact)
                    except Exception as exc:
                        yield _sse("warning", {"message": f"No se pudo verificar factualidad: {exc}", "tipo": "factualidad"})
            registrar_evento(
                usuario_id, "chat", modelo=modelo, estado="ok",
                latencia_ms=int((time.time() - started) * 1000),
                n_fuentes=len(papers) + len(fragmentos),
                texto_consulta=payload.mensaje,
            )
            yield _sse("done", {"content": respuesta_final, "modelo": modelo})
        except Exception as exc:
            registrar_evento(
                usuario_id, "chat", modelo=modelo, estado="error",
                latencia_ms=int((time.time() - started) * 1000),
                texto_consulta=payload.mensaje,
            )
            yield _sse("error", {"message": f"Error al consultar Groq: {exc}"})

    return {"clasificacion": clasificacion}, stream()


@app.post("/api/chat/stream")
def chat_stream(payload: ChatRequest):
    initial, stream = _prepare_chat(payload)
    if "limit" in initial:
        content = iter([_sse("warning", initial["limit"]), _sse("done", {"content": ""})])
        return StreamingResponse(content, media_type="text/event-stream")
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


@app.post("/api/flashcards/generate")
def generate_flashcards(payload: GenerateRequest) -> dict[str, Any]:
    limite = verificar_limite(payload.usuario_id, "flashcards", payload.idioma)
    if not limite["permitido"]:
        raise HTTPException(status_code=429, detail=limite["motivo"])
    registrar_solicitud(payload.usuario_id, "flashcards")
    if not payload.fuente:
        try:
            fragments = buscar_fragmentos_relevantes(payload.usuario_id, payload.texto_fuente) if buscar_fragmentos_relevantes else []
        except Exception:
            fragments = []
        if fragments:
            payload.texto_fuente = "\n\n".join(item[2] for item in fragments)
            payload.fuente = "Tus documentos"
    cards, diagnostic = generar_flashcards_con_ia(
        payload.usuario_id, payload.texto_fuente, payload.tema, payload.fuente,
        payload.n, payload.idioma,
    )
    return {"flashcards": cards, "diagnostico": diagnostic}


@app.get("/api/flashcards")
def list_flashcards(usuario_id: int, pendientes: bool = False) -> dict[str, Any]:
    cards = (
        obtener_flashcards_pendientes(usuario_id)
        if pendientes else []
    )
    return {
        "flashcards": cards,
        "pendientes": contar_flashcards_pendientes(usuario_id),
    }


@app.post("/api/flashcards/review")
def review_flashcard(payload: ReviewRequest) -> dict[str, Any]:
    result = registrar_repaso(payload.usuario_id, payload.flashcard_id, payload.boton)
    if result is None:
        raise HTTPException(status_code=404, detail="Flashcard o botón no válido")
    return result


@app.post("/api/examenes/generate")
def generate_exam(payload: GenerateRequest) -> dict[str, Any]:
    limite = verificar_limite(payload.usuario_id, "examen", payload.idioma)
    if not limite["permitido"]:
        raise HTTPException(status_code=429, detail=limite["motivo"])
    registrar_solicitud(payload.usuario_id, "examen")
    if not payload.fuente:
        try:
            fragments = buscar_fragmentos_relevantes(payload.usuario_id, payload.texto_fuente) if buscar_fragmentos_relevantes else []
        except Exception:
            fragments = []
        if fragments:
            payload.texto_fuente = "\n\n".join(item[2] for item in fragments)
            payload.fuente = "Tus documentos"
    questions, diagnostic = generar_examen_con_ia(
        payload.usuario_id, payload.texto_fuente, payload.tema, payload.fuente,
        payload.n, payload.idioma,
    )
    return {"preguntas": questions, "diagnostico": diagnostic}


@app.get("/api/examenes")
def list_exams(usuario_id: int, tema: str | None = None) -> dict[str, Any]:
    return {"preguntas": obtener_preguntas_examen(usuario_id, tema)}


@app.post("/api/examenes/attempt")
def attempt_exam(payload: ExamAttemptRequest) -> dict[str, bool]:
    registrar_intento(payload.usuario_id, payload.pregunta_id, payload.correcta)
    return {"saved": True}


@app.post("/api/interacciones")
def interactions(payload: InteractionRequest) -> dict[str, Any]:
    return verificar_interacciones(payload.farmacos)


@app.post("/api/interacciones/ia")
def interactions_ai(payload: InteractionAiRequest) -> dict[str, Any]:
    return analizar_interaccion_con_ia(
        payload.farmaco_a, payload.farmaco_b, idioma=payload.idioma
    )


@app.post("/api/uploads/pdf")
async def upload_pdf(
    usuario_id: int = Form(...),
    archivo: UploadFile = File(...),
) -> dict[str, Any]:
    nombre = Path(archivo.filename or "documento.pdf").name
    if not nombre.lower().endswith(".pdf"):
        raise HTTPException(status_code=415, detail="Solo se aceptan archivos PDF")
    contenido = await archivo.read(MAX_PDF_BYTES + 1)
    if len(contenido) > MAX_PDF_BYTES:
        raise HTTPException(status_code=413, detail="El PDF supera el límite permitido")
    ruta = UPLOAD_DIR / f"{usuario_id}_{uuid.uuid4().hex}_{nombre}"
    ruta.write_bytes(contenido)
    try:
        extraido = extraer_texto_pdf_con_ocr(ruta, max_paginas=MAX_PDF_PAGINAS)
        texto, alertas = sanitizar_texto_pdf(extraido["texto"])
        fragmentos = guardar_fragmentos_pdf(
            usuario_id, nombre, texto, tipo_texto="ocr" if extraido["via_ocr"] else "normal"
        )
        tablas_indexadas = 0
        tablas = []
        try:
            tablas = extraer_tablas_pdf(ruta)
        except Exception:
            tablas = []
        for tabla in tablas:
            fuente_tabla = f"{nombre} · tabla {tabla['indice_en_pagina']} (pág. {tabla['pagina']})"
            markdown, alertas_tabla = sanitizar_texto_pdf(tabla["markdown"])
            alertas.extend(alertas_tabla)
            if guardar_fragmentos_pdf(usuario_id, fuente_tabla, markdown, tipo_texto="tabla") > 0:
                tablas_indexadas += 1
        return {
            "nombre": nombre,
            "fragmentos": fragmentos,
            "via_ocr": extraido["via_ocr"],
            "alertas_seguridad": alertas,
            "resumen_alertas": resumir_alertas(alertas) if alertas else None,
            "tablas": len(tablas),
            "tablas_indexadas": tablas_indexadas,
            "caracteres": len(texto),
        }
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        ruta.unlink(missing_ok=True)


@app.get("/api/progreso")
def progress(usuario_id: int | None = None) -> dict[str, Any]:
    resolved_id = usuario_id or _anonymous_user_id()
    return {
        "usuario_id": resolved_id,
        "resumen": resumen_progreso(resolved_id),
        "temas": evaluar_nivel_por_tema(resolved_id),
    }


@app.get("/api/options")
def options() -> dict[str, Any]:
    from pubmed_search import MODOS_EVIDENCIA
    return {
        "idiomas": [{"codigo": codigo, "nombre": config["nombre"]} for codigo, config in IDIOMAS.items()],
        "modos_evidencia": list(MODOS_EVIDENCIA.keys()),
        "limites": LIMITES,
    }


@app.post("/api/search/pubmed")
def search_pubmed(payload: SearchRequest) -> dict[str, Any]:
    limite = verificar_limite(payload.usuario_id, "pubmed", payload.idioma)
    if not limite["permitido"]:
        raise HTTPException(status_code=429, detail=limite["motivo"])
    registrar_solicitud(payload.usuario_id, "pubmed")
    papers, nuevos, total, debug, estado = buscar_pubmed_estructurado(
        payload.consulta, payload.usuario_id
    )
    papers = filtrar_papers_por_evidencia(papers, payload.modo_evidencia)
    return {
        "papers": papers,
        "nuevos": nuevos,
        "total": total,
        "debug": debug,
        "estado": estado,
    }


@app.post("/api/search/europepmc")
def search_europepmc(payload: SearchRequest) -> dict[str, Any]:
    papers, debug = buscar_europepmc(
        payload.consulta, retmax=payload.limite, rango_anios=payload.rango_anios
    )
    return {"papers": papers, "debug": debug}


@app.post("/api/search/semantic-scholar")
def search_semantic_scholar(payload: SearchRequest) -> dict[str, Any]:
    papers, debug = buscar_semantic_scholar(
        payload.consulta, limit=payload.limite, rango_anios=payload.rango_anios
    )
    return {"papers": papers, "debug": debug}


@app.post("/api/icd11")
def icd11(payload: IcdRequest) -> dict[str, Any]:
    limite = verificar_limite(payload.usuario_id, "icd11", payload.idioma)
    if not limite["permitido"]:
        raise HTTPException(status_code=429, detail=limite["motivo"])
    registrar_solicitud(payload.usuario_id, "icd11")
    return construir_glosario_icd11(payload.pregunta, payload.idioma)


@app.post("/api/feedback")
def feedback(payload: FeedbackRequest) -> dict[str, bool]:
    if payload.valoracion not in (-1, 1):
        raise HTTPException(status_code=422, detail="La valoración debe ser -1 o 1")
    saved = registrar_feedback(
        payload.usuario_id, payload.chat_id, payload.pregunta, payload.respuesta,
        payload.valoracion, payload.fuentes, payload.idioma,
    )
    if not saved:
        raise HTTPException(status_code=500, detail="No se pudo guardar el feedback")
    return {"saved": True}


@app.get("/api/feedback/summary")
def feedback_summary(dias: int = 30) -> dict[str, Any]:
    return resumen_feedback(max(1, min(dias, 365)))


@app.get("/api/auditoria")
def audit_summary(usuario_id: int | None = None, dias: int = 7) -> list[dict[str, Any]]:
    return obtener_resumen_auditoria(usuario_id, max(1, min(dias, 365)))


@app.post("/api/uso")
def usage_limit(payload: UsageRequest) -> dict[str, Any]:
    return verificar_limite(payload.usuario_id, payload.tipo, payload.idioma)


if (STATIC_DIR / "assets").exists():
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
