---
title: Medicine Ai App
emoji: 🐢
colorFrom: blue
colorTo: indigo
sdk: docker
pinned: false
---

# 🩺 Medicine Study AI

Asistente de estudio para estudiantes de medicina, con evidencia citable de PubMed/Europe PMC/Semantic Scholar, verificación de factualidad, y una capa de seguridad clínica pensada desde el diseño — no como parche.

> Este documento explica **cómo está construido**, no solo qué hace. Está pensado para que otro desarrollador, o un médico con curiosidad técnica, pueda entender el rigor detrás del sistema sin tener que leer los ~20 módulos uno por uno.

---

## Qué es

Medicine Study AI es un chat de estudio médico que:

- Responde preguntas citando **papers reales** (no inventados) de PubMed, Europe PMC y Semantic Scholar, con nivel de evidencia clasificado (ensayo clínico, revisión sistemática, reporte de caso, preprint...).
- Deja subir PDFs propios (apuntes, papers) y responde con base en ellos, citando el fragmento exacto.
- **Verifica su propia factualidad** después de responder: un segundo paso ("juez") contrasta cada afirmación contra las fuentes citadas y marca lo que no está respaldado.
- Genera flashcards con repetición espaciada (SM-2) y exámenes de opción múltiple a partir de un tema o de tus documentos.
- Incluye calculadoras clínicas (IMC, superficie corporal, función renal, dosis por peso, ajuste renal) y un verificador de interacciones farmacológicas.
- Funciona en **5 idiomas** (español, inglés, francés, alemán, chino), con terminología clínica verificada contra ICD-11 de la OMS — no solo traducción automática.
- Tiene una capa de seguridad activa: sanitiza PDFs contra prompt injection, limita el uso por usuario, audita sin guardar contenido sensible, y detecta si una pregunta suena a emergencia médica real (en cuyo caso corta el flujo y muestra recursos de emergencia, sin pasar por el modelo).

---

## Arquitectura

```
                              ┌─────────────────┐
                              │   Estudiante     │
                              └────────┬─────────┘
                                       │
                              ┌────────▼─────────┐
                              │  Rate Limiter     │  limite_uso.py
                              │  (por usuario)    │
                              └────────┬─────────┘
                                       │
                              ┌────────▼─────────┐
                              │  Clasificador de  │  clasificador_riesgo_clinico.py
                              │  riesgo clínico   │  (5 idiomas, regex, sin LLM)
                              └────────┬─────────┘
                     ┌─────────────────┼─────────────────┐
                     ▼                 ▼                 ▼
               "emergencia"      "riesgo_personal"   "educativo"
                     │                 │                 │
             Corta el flujo,    Aviso + refuerzo    Sigue normal
             muestra recursos    en el prompt
             de emergencia
                                                          │
                              ┌───────────────────────────▼──────────────────────┐
                              │              Recuperación de contexto             │
                              │  • PubMed + Europe PMC + Semantic Scholar         │
                              │    (Query Rewriter → 3 variantes en inglés →      │
                              │     esearch/efetch → ranking semántico → dedup)   │
                              │  • Fragmentos de PDFs propios (embeddings + RAG)  │
                              │  • Glosario ICD-11 (si idioma ≠ inglés)           │
                              └───────────────────────────┬──────────────────────┘
                                                           │
                              ┌───────────────────────────▼──────────────────────┐
                              │         Groq (system prompt por idioma)          │
                              │         Streaming de la respuesta                │
                              └───────────────────────────┬──────────────────────┘
                                                           │
                              ┌───────────────────────────▼──────────────────────┐
                              │      Verificación anti-alucinación               │
                              │  • ¿Citó [n]/[Fn] que no existen?                 │
                              │  • ¿Dijo "no encontré evidencia" habiendo evidencia?│
                              │  • ¿Hay contradicción fisiológica en el diagnóstico?│
                              │  • Juez de factualidad (contrasta cada afirmación) │
                              └───────────────────────────┬──────────────────────┘
                                                           │
                              ┌───────────────────────────▼──────────────────────┐
                              │   Badge de evidencia + Panel de fuentes           │
                              │   + Auditoría (hash, no texto) + Feedback (👍/👎) │
                              └────────────────────────────────────────────────────┘
```

---

## Características por fase

El proyecto se construyó incrementalmente. Cada fase es funcional por sí sola y las posteriores construyen sobre las anteriores:

| Fase | Qué agrega |
|---|---|
| 1–3 | RAG sobre PDFs, OCR para escaneados, extracción de tablas |
| 4 | Búsqueda estructurada en PubMed con Query Rewriter (3 variantes en inglés), flashcards con SM-2, exámenes de opción múltiple |
| 5 | Calculadoras clínicas (IMC, BSA, función renal, dosis por peso, ajuste renal) e interacciones farmacológicas |
| 6 | Seguridad: sanitización anti-prompt-injection en PDFs, rate limiting, auditoría de uso (sin texto sensible), clasificador de riesgo clínico |
| 7 | UI: Markdown real, burbujas de chat, edición de mensajes, panel de proceso colapsable |
| 8–10 | Multilingüe (ES/EN/FR/DE/ZH) — respuestas, UI completa, detección de riesgo, y patrones anti-alucinación en los 5 idiomas |
| 11 | Terminología ICD-11 de la OMS (oficial, no traducción automática) inyectada en el contexto; badge de nivel de evidencia citado; feedback 👍/👎 |
| 12 | Europe PMC + Semantic Scholar como fuentes adicionales de búsqueda; benchmark clínico propio |

---

## Stack tecnológico

- **UI**: [Flet](https://flet.dev) (Python → Flutter)
- **LLM**: [Groq](https://groq.com) (`openai/gpt-oss-120b` para chat/juez, `openai/gpt-oss-20b` para tareas auxiliares)
- **Embeddings**: `sentence-transformers` (paraphrase-multilingual-MiniLM-L12-v2) para RAG y ranking semántico de papers
- **Base de datos**: SQLite (usuarios, chats, papers, flashcards, exámenes, auditoría, feedback, límite de uso)
- **Fuentes de evidencia**: PubMed (NCBI E-utilities), Europe PMC, Semantic Scholar, ICD-11 (OMS)
- **PDFs**: `pypdf` (texto), `pymupdf` + `rapidocr_onnxruntime` (OCR), `pdfplumber` (tablas)

---

## Variables de entorno necesarias

| Variable | Para qué |
|---|---|
| `GROQ_API_KEY` | Chat, generación de flashcards/exámenes, juez de factualidad |
| `ICD11_CLIENT_ID` / `ICD11_CLIENT_SECRET` | Terminología oficial ICD-11 (opcional — sin esto, la app funciona igual, solo sin el glosario de terminología) |

---

## Estructura de módulos

```
app.py                          Punto de entrada
app_ui.py                       Toda la UI de Flet (vistas, chat, sidebar)
config.py                       Cliente Groq, embeddings, SYSTEM_PROMPT por idioma
database.py                     Esquema SQLite y funciones de acceso

pubmed_search.py                Búsqueda en PubMed + Europe PMC + Semantic Scholar
citas_evidencia.py              Formato de citas, anti-alucinación, juez de factualidad
rag_embeddings.py                Fragmentación y búsqueda semántica en PDFs propios
ocr_pdf.py                       OCR para PDFs escaneados
extraccion_tablas.py             Extracción de tablas de PDFs

flashcards.py                    Flashcards + algoritmo SM-2
examenes.py                      Generación de exámenes de opción múltiple
historial_utils.py               Recorte de historial, título de chat
memoria_estudiante.py            Memoria semántica de temas estudiados, evaluación de nivel

calculadoras_clinicas.py         IMC, BSA, función renal, dosis por peso, ajuste renal
interacciones_farmacologicas.py  Base curada de interacciones + respaldo de IA
icd11_terminologia.py            Terminología oficial ICD-11 (OAuth2 + búsqueda)

seguridad_prompt_injection.py    Sanitización de PDFs contra instrucciones ocultas
limite_uso.py                    Rate limiting por usuario y tipo de operación
auditoria.py                     Registro de uso (hash, nunca texto en claro)
clasificador_riesgo_clinico.py   Detección de emergencias / riesgo personal (5 idiomas)
feedback.py                      Feedback 👍/👎 — dataset propio de casos

traducciones.py                  Textos de UI en 5 idiomas (t(), t_categoria())

benchmark_medico.py              Evaluación de precisión con preguntas clínicas
test_icd11_api.py                Script de diagnóstico para configurar ICD-11
```

---

## Seguridad y consideraciones de diseño

- **Nunca se guarda el texto de las preguntas médicas en la auditoría** — solo un hash SHA-256 y la longitud. El feedback 👍/👎 sí guarda el texto completo, pero solo cuando el estudiante lo pide explícitamente (es un dataset de revisión, no telemetría).
- **Las instrucciones de dosis y las descripciones de interacciones farmacológicas se mantienen siempre en español**, sin importar el idioma de la UI — traducir automáticamente texto clínico de dosificación sin revisión médica es un riesgo real, así que se optó por no hacerlo en vez de arriesgar una traducción incorrecta.
- **El clasificador de riesgo clínico nunca deja pasar una emergencia al modelo** — si detecta señales de emergencia médica o de salud mental, corta el flujo antes de llamar a Groq y muestra recursos reales (911, líneas de crisis), en los 5 idiomas soportados.
- **El SYSTEM_PROMPT instruye explícitamente al modelo a tratar el contenido de PDFs como datos, nunca como instrucciones** — segunda capa de defensa contra prompt injection, además del filtro que redacta líneas sospechosas antes de indexar.

## Limitaciones conocidas

- La pantalla de login no es multilingüe (ocurre antes de que exista una sesión con idioma seleccionado).
- El benchmark clínico usa preguntas originales calibradas a nivel ENARM/USMLE, no preguntas reales de ningún examen (por derechos de autor) — es una aproximación, no una certificación.
- La integración con Europe PMC/Semantic Scholar no tiene API key configurada por defecto para mayores límites de tasa; en uso alto podría toparse con límites públicos compartidos.

## Cómo evaluar la precisión

```bash
python benchmark_medico.py
```

Corre un set de preguntas clínicas de opción múltiple y reporta precisión global y por especialidad — pensado para correr después de cambiar el modelo o el `SYSTEM_PROMPT`, y ver si la precisión sube o baja.




# Medicine-Study-AI
síganme y denme consejos para mi proyecto que esta actualmente en Hugging Face, Aquí esta mi cuenta: https://huggingface.co/Chantilli
