"""
Aplicación principal Flet: login/registro, sidebar, chat, subida de PDF
(con OCR), búsqueda en PubMed/Europe PMC, verificación de factualidad y
consistencia fisiológica. Toda la lógica de negocio vive en los otros
módulos — este archivo solo arma la interfaz y conecta los eventos.
"""
import os
import time
import flet as ft

from config import client, modelo_embeddings, SYSTEM_PROMPT, UPLOAD_DIR, MAX_CARACTERES_BLOQUE, MODELO_CHAT, MODELO_AUXILIAR, construir_system_prompt, IDIOMAS, IDIOMA_POR_DEFECTO
from database import (
    crear_usuario, obtener_usuario_por_nombre, verificar_password,
    guardar_chat_db, obtener_todos_los_chats, obtener_mensajes_chat, eliminar_chat_db,
)
from rag_embeddings import guardar_fragmentos_pdf, buscar_fragmentos_relevantes
from ocr_pdf import extraer_texto_pdf_con_ocr, _disponible_ocr
from extraccion_tablas import extraer_tablas_pdf
from pubmed_search import buscar_pubmed_estructurado, filtrar_papers_por_evidencia, MODOS_EVIDENCIA
from citas_evidencia import (
    formatear_contexto_papers, detectar_citas_alucinadas, detectar_citas_fuera_de_rango,
    detectar_negacion_contradictoria, limpiar_negacion_contradictoria,
    verificar_consistencia_fisiologica, construir_lista_fuentes, construir_contexto_para_juez,
    evaluar_factualidad, resumen_evidencia_citada,
)
from ui_helpers import agregar_papers_a_chat, construir_panel_fuentes, anexar_badge_factualidad
from historial_utils import recortar_historial, generar_titulo_con_ia
from flashcards import (
    generar_flashcards_con_ia, obtener_flashcards_pendientes,
    contar_flashcards_pendientes, registrar_repaso,
)
from examenes import generar_examen_con_ia, registrar_intento as registrar_intento_examen
from memoria_estudiante import (
    registrar_concepto_estudiado, obtener_temas_relacionados,
    evaluar_nivel_por_tema, resumen_progreso,
)
from calculadoras_clinicas import (
    calcular_imc, calcular_superficie_corporal, calcular_aclaramiento_creatinina,
    calcular_egfr_ckd_epi, calcular_dosis_por_peso, obtener_ajuste_renal,
    AJUSTES_RENALES_COMUNES,
)
from interacciones_farmacologicas import verificar_interacciones, analizar_interaccion_con_ia
from seguridad_prompt_injection import sanitizar_texto_pdf, resumir_alertas
from limite_uso import verificar_limite, registrar_solicitud
from icd11_terminologia import construir_glosario_icd11
from feedback import registrar_feedback
from auditoria import registrar_evento
from clasificador_riesgo_clinico import (
    clasificar_consulta, mensaje_emergencia_medica, mensaje_emergencia_salud_mental,
    aviso_riesgo_personal, instruccion_refuerzo_riesgo_personal,
)
from traducciones import t, t_categoria


def main(page: ft.Page):
    page.title = "Medicine Study AI"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#111217"

  
    page.upload_files_dir = str(UPLOAD_DIR)

    chat_actual_id = [str(time.time())]
    idioma_var = [IDIOMA_POR_DEFECTO]
    historial = [construir_system_prompt(idioma_var[0])]
    switch_pubmed_var = False
    switch_factualidad_var = True
    modo_evidencia_var = ["todo"]
    usuario_actual_id = [None]
    usuario_actual_nombre = [None]
    
    procesando_mensaje = [False]
    
    fragmentos_sesion = []

  
    flashcards_sesion = []
    indice_flashcard = [0]
    mostrando_respuesta_flashcard = [False]
    en_modo_repaso = [False]

    txt_estado_flashcards = ft.Text("", size=12, color="#a78bfa", italic=True)
    txt_contador_flashcards = ft.Text("📇 Repasar (0 pendientes)", size=13, color="#e2e8f0")

    
    examen_sesion = []
    indice_pregunta_examen = [0]
    opcion_seleccionada_examen = [None]
    respuesta_revelada_examen = [False]
    aciertos_examen = [0]
    txt_estado_examen = ft.Text("", size=12, color="#a78bfa", italic=True)

    chat_view = ft.ListView(expand=True, spacing=10, auto_scroll=True)
    lista_historial_ui = ft.Column(spacing=5, scroll=ft.ScrollMode.AUTO)
    txt_estado_pdf = ft.Text("", size=12, color="#22c55e", italic=True)

    # =====================================================================
    # Sistema de renderizado del chat (Fase 7 — UI/UX)
    #
    # Antes, cada mensaje se mandaba como ft.Text plano — por eso el
    # markdown que devuelve el modelo (negritas **así**, tablas |a|b|,
    # encabezados ##) se veía crudo, con los símbolos literales. Ahora:
    #
    #   - Los mensajes del ASISTENTE se renderizan con ft.Markdown real
    #     (negritas, tablas, encabezados, listas se ven formateados).
    #   - Todo el texto es seleccionable (selectable=True) para copiar.
    #   - Cada respuesta del asistente trae un botón de copiar.
    #   - Cada mensaje del usuario trae un botón de editar: reescribe el
    #     mensaje, descarta esa pregunta y todo lo posterior, y lo deja
    #     listo en el cuadro de texto para reenviar corregido.
    #   - Los pasos intermedios ("buscando en PubMed...", "generando...",
    #     "verificando...") ya NO se imprimen sueltos en el chat — se
    #     acumulan en un panel plegable "⚙️ Ver proceso" (colapsado por
    #     defecto, igual que el razonamiento colapsado de Claude/Grok),
    #     dejando visible solo la respuesta final y las alertas que sí
    #     importan (citas inventadas, inconsistencias, emergencias).
    # =====================================================================

    def _tarjeta_aviso(contenido, tipo="info"):
        """Tarjeta de aviso reutilizable — reemplaza los Container(...)
        repetidos a mano para alertas de citas inventadas, inconsistencias
        fisiológicas, límites de uso, emergencias, etc. `contenido` puede
        ser un string o ya un ft.Control (para avisos con varias líneas)."""
        estilos = {
            "error": ("#3b1a1a", "#ef4444", "#fca5a5"),
            "warning": ("#3a2f0f", "#f59e0b", "#fde68a"),
            "info": ("#1e293b", "#3b82f6", "#93c5fd"),
        }
        bg, borde, color_texto = estilos.get(tipo, estilos["info"])
        hijo = contenido if isinstance(contenido, ft.Control) else ft.Text(contenido, color=color_texto, size=12)
        return ft.Container(
            content=hijo, bgcolor=bg, border=ft.border.all(1, borde),
            border_radius=8, padding=10,
        )

    def _indicador_carga(texto):
        return ft.Row(
            [ft.ProgressRing(width=13, height=13, stroke_width=2, color="#3b82f6"),
             ft.Text(texto, color="#64748b", italic=True, size=12)],
            spacing=8,
        )

    def _mostrar_snackbar(texto, color_fondo="#1e293b"):
        page.snack_bar = ft.SnackBar(content=ft.Text(texto, color="#f8fafc", size=13), bgcolor=color_fondo, duration=1400)
        page.snack_bar.open = True
        page.update()

    def _copiar_texto(e, texto):
        page.set_clipboard(texto)
        _mostrar_snackbar(t("copiado_portapapeles", idioma_var[0]), color_fondo="#14532d")

    def _burbuja_usuario(texto, indice_historial=None):
        """Burbuja alineada a la derecha. Si se da indice_historial, se
        habilita el botón de editar (corta el historial ahí y reabre el
        texto en el cuadro de mensaje)."""
        acciones = []
        if indice_historial is not None:
            def click_editar(e, texto=texto, idx=indice_historial):
                nonlocal historial
                entrada.value = texto
                historial = historial[:idx]
                if len(historial) <= 1:
                    mostrar_pantalla_bienvenida()
                else:
                    _renderizar_historial_en_chat()
                page.update()
            acciones.append(
                ft.IconButton(
                    icon=ft.Icons.EDIT_OUTLINED, icon_size=14, icon_color="#64748b",
                    tooltip="Editar y reenviar", on_click=click_editar,
                    style=ft.ButtonStyle(padding=4),
                )
            )
        return ft.Row([
            ft.Container(expand=True),
            ft.Column([
                ft.Container(
                    content=ft.Text(texto, color="#f1f5f9", size=14, selectable=True),
                    bgcolor="#17324d", border=ft.border.all(1, "#2c4a6e"),
                    border_radius=ft.BorderRadius(14, 14, 3, 14), padding=ft.Padding(14, 10, 14, 10),
                ),
                ft.Row(acciones, alignment=ft.MainAxisAlignment.END, spacing=0) if acciones else ft.Container(),
            ], horizontal_alignment=ft.CrossAxisAlignment.END, spacing=2),
        ])

    def _burbuja_ai(texto="", pregunta=None):
        """Burbuja alineada a la izquierda con Markdown real (negritas,
        tablas, listas) en vez de texto plano con símbolos crudos.
        Devuelve (fila, markdown_control) — markdown_control se usa para
        ir actualizando el texto mientras llega el streaming.

        'pregunta' es la pregunta del estudiante que generó esta
        respuesta — se necesita para poder registrar feedback (👍/👎)
        con el par pregunta/respuesta completo. Si no se da (por
        ejemplo, al reconstruir un historial viejo sin esa info), los
        botones de feedback simplemente no aparecen."""
        markdown_control = ft.Markdown(
            value=texto,
            selectable=True,
            extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
            on_tap_link=lambda e: page.launch_url(e.data),
        )

        botones_feedback = []
        if pregunta:
            estado_feedback = {"votado": False}

            def _votar(e, valoracion):
                if estado_feedback["votado"]:
                    return
                estado_feedback["votado"] = True
                registrar_feedback(
                    usuario_actual_id[0], chat_actual_id[0], pregunta, markdown_control.value,
                    valoracion, idioma=idioma_var[0],
                )
                for b in botones_feedback:
                    b.disabled = True
                _mostrar_snackbar(t("feedback_gracias", idioma_var[0]), color_fondo="#14532d")

            btn_util = ft.IconButton(
                icon=ft.Icons.THUMB_UP_OUTLINED, icon_size=13, icon_color="#64748b",
                tooltip=t("feedback_util", idioma_var[0]),
                on_click=lambda e: _votar(e, 1), style=ft.ButtonStyle(padding=4),
            )
            btn_no_util = ft.IconButton(
                icon=ft.Icons.THUMB_DOWN_OUTLINED, icon_size=13, icon_color="#64748b",
                tooltip=t("feedback_no_util", idioma_var[0]),
                on_click=lambda e: _votar(e, -1), style=ft.ButtonStyle(padding=4),
            )
            botones_feedback.extend([btn_util, btn_no_util])

        fila = ft.Row([
            ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Text("🩺 Medicine AI", size=11, weight=ft.FontWeight.BOLD, color="#64748b", expand=True),
                        *botones_feedback,
                        ft.IconButton(
                            icon=ft.Icons.CONTENT_COPY, icon_size=13, icon_color="#64748b",
                            tooltip=t("copiar_respuesta", idioma_var[0]),
                            on_click=lambda e: _copiar_texto(e, markdown_control.value),
                            style=ft.ButtonStyle(padding=4),
                        ),
                    ]),
                    markdown_control,
                ], spacing=2),
                bgcolor="#1a1b23", border=ft.border.all(1, "#2a2b36"),
                border_radius=ft.BorderRadius(14, 14, 14, 3), padding=ft.Padding(14, 10, 14, 12),
                expand=True,
            ),
        ])
        return fila, markdown_control

    def _crear_panel_proceso():
        """Panel plegable donde viven los pasos intermedios de un turno
        (búsquedas, generación, verificación) — colapsado por defecto."""
        columna_pasos = ft.Column([], spacing=6)
        panel = ft.ExpansionTile(
            title=ft.Row([
                ft.Icon(ft.Icons.SETTINGS_SUGGEST_OUTLINED, size=14, color="#64748b"),
                ft.Text(t("ver_proceso", idioma_var[0]), size=12, color="#64748b"),
            ], spacing=6),
            controls=[ft.Container(content=columna_pasos, padding=ft.Padding(14, 2, 14, 10))],
            initially_expanded=False,
            collapsed_bgcolor="#15161c",
            bgcolor="#15161c",
            shape=ft.RoundedRectangleBorder(radius=10),
        )
        return panel, columna_pasos

    def _agregar_paso_proceso(columna_pasos, texto, en_progreso=True):
        icono = (
            ft.ProgressRing(width=12, height=12, stroke_width=2, color="#3b82f6") if en_progreso
            else ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE, size=14, color="#22c55e")
        )
        fila = ft.Row([icono, ft.Text(texto, size=12, color="#94a3b8", italic=True, expand=True)], spacing=8)
        columna_pasos.controls.append(fila)
        page.update()
        return fila

    def _completar_paso_proceso(fila, texto_final=None, error=False):
        fila.controls[0] = ft.Icon(
            ft.Icons.ERROR_OUTLINE if error else ft.Icons.CHECK_CIRCLE_OUTLINE,
            size=14, color="#ef4444" if error else "#22c55e",
        )
        if texto_final is not None:
            fila.controls[1].value = texto_final
        page.update()

    def _renderizar_historial_en_chat():
        """Reconstruye chat_view completo a partir de `historial` (fuente
        de verdad) — se usa al cargar una conversación guardada y al
        editar un mensaje (después de truncar el historial)."""
        chat_view.controls.clear()
        ultima_pregunta_limpia = None
        for idx, msg in enumerate(historial):
            if msg["role"] == "system":
                continue
            if msg["role"] == "user":
                texto_limpio = msg["content"].split("Pregunta:")[-1].strip()
                if "[Nota interna" in texto_limpio:
                    texto_limpio = texto_limpio.split("[Nota interna")[0].strip()
                ultima_pregunta_limpia = texto_limpio
                chat_view.controls.append(_burbuja_usuario(texto_limpio, idx))
            elif msg["role"] == "assistant":
                fila_respuesta, _ = _burbuja_ai(msg["content"], pregunta=ultima_pregunta_limpia)
                chat_view.controls.append(fila_respuesta)
                if msg.get("_fuentes"):
                    chat_view.controls.append(construir_panel_fuentes(msg["_fuentes"]))
                if msg.get("_factualidad"):
                    anexar_badge_factualidad(chat_view, page, msg["_factualidad"])
                if msg.get("_evidencia"):
                    resumen_evidencia = msg["_evidencia"]
                    nivel_traducido = t_categoria(resumen_evidencia["nivel_mas_fuerte"], idioma_var[0])
                    chat_view.controls.append(_tarjeta_aviso(
                        "🏅 " + t(
                            "badge_evidencia_citada", idioma_var[0],
                            nivel=nivel_traducido, n=resumen_evidencia["n_papers_citados"],
                        ),
                        tipo="info",
                    ))
        page.update()

    def _chip_sugerencia(texto):
        def click(e):
            entrada.value = texto
            page.update()
            entrada.focus()
        return ft.Container(
            content=ft.Text(texto, size=12, color="#cbd5e1"),
            bgcolor="#1a1b23", border=ft.border.all(1, "#2a2b36"), border_radius=20,
            padding=ft.Padding(14, 8, 14, 8), on_click=click, ink=True,
        )

    def _tarjeta_funcion(icono, titulo, descripcion):
        return ft.Container(
            content=ft.Column([
                ft.Icon(icono, size=22, color="#60a5fa"),
                ft.Text(titulo, size=13, weight=ft.FontWeight.BOLD, color="#f1f5f9"),
                ft.Text(descripcion, size=11, color="#64748b"),
            ], spacing=4),
            bgcolor="#15161c", border=ft.border.all(1, "#22232d"), border_radius=12,
            padding=14, width=220,
        )

    def mostrar_pantalla_bienvenida():
        chat_view.controls.clear()
        idioma = idioma_var[0]
        try:
            chat_view.controls.append(
                ft.Column([
                    ft.Container(height=30),
                    ft.Icon(ft.Icons.MEDICAL_INFORMATION_OUTLINED, size=46, color="#3b82f6"),
                    ft.Text("Medicine Study AI", size=24, weight=ft.FontWeight.BOLD, color="#f8fafc"),
                    ft.Text(
                        t("bienvenida_subtitulo", idioma),
                        size=13, color="#94a3b8", text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Container(height=12),
                    ft.Row([
                        _tarjeta_funcion(ft.Icons.SEARCH, t("func_pubmed_titulo", idioma), t("func_pubmed_desc", idioma)),
                        _tarjeta_funcion(ft.Icons.UPLOAD_FILE_OUTLINED, t("func_pdfs_titulo", idioma), t("func_pdfs_desc", idioma)),
                        _tarjeta_funcion(ft.Icons.FACT_CHECK_OUTLINED, t("func_factualidad_titulo", idioma), t("func_factualidad_desc", idioma)),
                        _tarjeta_funcion(ft.Icons.CALCULATE_OUTLINED, t("func_calculadoras_titulo", idioma), t("func_calculadoras_desc", idioma)),
                    ], wrap=True, spacing=12, alignment=ft.MainAxisAlignment.CENTER),
                    ft.Container(height=16),
                    ft.Text(t("prueba_con_algo_como", idioma), size=11, color="#64748b"),
                    ft.Row([
                        _chip_sugerencia(t("chip_ciclo_cardiaco", idioma)),
                        _chip_sugerencia(t("chip_dolor_toracico", idioma)),
                        _chip_sugerencia(t("chip_metformina", idioma)),
                    ], wrap=True, spacing=8, alignment=ft.MainAxisAlignment.CENTER),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8)
            )
        except Exception as ex:
            # Nunca dejar la pantalla en blanco en silencio: si algo de la
            # pantalla de bienvenida falla, se ve el error y queda en el
            # log del servidor (Logs de HF) en vez de un panel vacío sin
            # ninguna pista de qué pasó.
            print(f"[mostrar_pantalla_bienvenida] Error: {ex}")
            chat_view.controls.clear()
            chat_view.controls.append(
                ft.Text(
                    f"✨ Medicine Study AI\n{t('bienvenida_subtitulo', idioma)}\n\n"
                    f"(No se pudo cargar la pantalla de inicio completa: {ex})",
                    size=15, color="#e2e8f0",
                )
            )
        page.update()

    def cambiar_switch(e):
        nonlocal switch_pubmed_var
        switch_pubmed_var = e.control.value

    def cambiar_switch_factualidad(e):
        nonlocal switch_factualidad_var
        switch_factualidad_var = e.control.value

    def cambiar_modo_evidencia(e):
        modo_evidencia_var[0] = e.control.value

    def cambiar_idioma(e):
        # idioma_var[0] se lee en vivo en cada turno para las respuestas de
        # la IA (mensajes_para_groq[0] = construir_system_prompt(...)), y
        # aquí además se retraduce todo lo que está siempre visible
        # (sidebar) y se refresca la pantalla actual a la nueva pantalla
        # de bienvenida ya traducida — antes el botón solo cambiaba el
        # idioma de las respuestas del chat, dejando calculadoras, examen
        # y el resto del sidebar en español sin importar la selección.
        idioma_var[0] = e.control.value
        aplicar_idioma_ui(idioma_var[0])
        chat_view.controls.clear()
        mostrar_pantalla_bienvenida()

    def al_seleccionar_archivo(e):
        archivos = getattr(e, "files", None)
        if not archivos and hasattr(e, "control") and getattr(e.control, "result", None):
            archivos = e.control.result.files

        if not archivos:
            return

        txt_estado_pdf.value = "⏳ Transfiriendo archivo..."
        page.update()

        archivo = archivos[0]
        upload_url = page.get_upload_url(archivo.name, 600)
        file_picker.upload([
            ft.FilePickerUploadFile(archivo.name, upload_url)
        ])

    def al_completar_subida(e):
      
        progreso = getattr(e, "progress", None)
        if progreso is not None and progreso < 1:
            return

        error_subida = getattr(e, "error", None)
        if error_subida:
            txt_estado_pdf.value = f"❌ Error al subir el archivo: {error_subida}"
            page.update()
            return

        txt_estado_pdf.value = "⏳ Procesando y extrayendo texto del PDF..."
        page.update()
        try:
            nombre_archivo = getattr(e, "file_name", None) or getattr(e, "name", None)
            if not nombre_archivo:
                txt_estado_pdf.value = "❌ Archivo no identificado"
                page.update()
                return

            ruta_final_archivo = UPLOAD_DIR / nombre_archivo
            if not ruta_final_archivo.exists():
                return

            
            resultado_extraccion = extraer_texto_pdf_con_ocr(ruta_final_archivo)
            texto_extraido = resultado_extraccion["texto"]
            tipo_texto = "ocr" if resultado_extraccion["via_ocr"] else "normal"

            # Filtro de seguridad: un PDF podría traer texto oculto intentando
            # manipular las instrucciones del sistema una vez indexado como
            # fragmento [Fn]. Se redactan las líneas sospechosas ANTES de
            # fragmentar/indexar (el SYSTEM_PROMPT en config.py es la segunda
            # capa de defensa, por si algo se escapa de este filtro).
            texto_extraido, alertas_inyeccion = sanitizar_texto_pdf(texto_extraido)
            if alertas_inyeccion:
                chat_view.controls.append(
                    _tarjeta_aviso(f"🛡️ Filtro de seguridad: {resumir_alertas(alertas_inyeccion)}", tipo="warning")
                )

            if modelo_embeddings:
                n_fragmentos = guardar_fragmentos_pdf(usuario_actual_id[0], nombre_archivo, texto_extraido, tipo_texto=tipo_texto)
                if n_fragmentos > 0:
                    if resultado_extraccion["via_ocr"]:
                        n_paginas_ocr = len(resultado_extraccion["paginas_ocreadas"])
                        txt_estado_pdf.value = (
                            f"✅ PDF indexado ({n_fragmentos} fragmentos, "
                            f"{n_paginas_ocr} págs. vía OCR): {nombre_archivo[:18]}..."
                        )
                    else:
                        txt_estado_pdf.value = f"✅ PDF indexado ({n_fragmentos} fragmentos): {nombre_archivo[:18]}..."
                else:
                    if not _disponible_ocr():
                        txt_estado_pdf.value = "❌ No se pudo extraer texto (parece escaneado; el OCR no está disponible en este servidor)"
                    else:
                        txt_estado_pdf.value = "❌ No se pudo extraer texto del PDF, ni siquiera con OCR"
            else:
               
                fragmentos_sesion.append(texto_extraido[:MAX_CARACTERES_BLOQUE])
                txt_estado_pdf.value = f"✅ PDF cargado (sin búsqueda semántica): {nombre_archivo[:18]}..."

            
            if modelo_embeddings:
                try:
                    tablas = extraer_tablas_pdf(ruta_final_archivo)
                except Exception:
                    tablas = []
                if tablas:
                    n_tablas_indexadas = 0
                    for tabla in tablas:
                        fuente_tabla = (
                            f"{nombre_archivo} · tabla {tabla['indice_en_pagina']} (pág. {tabla['pagina']})"
                        )
                        markdown_tabla, alertas_tabla = sanitizar_texto_pdf(tabla["markdown"])
                        if alertas_tabla:
                            alertas_inyeccion.extend(alertas_tabla)
                        if guardar_fragmentos_pdf(usuario_actual_id[0], fuente_tabla, markdown_tabla, tipo_texto="tabla") > 0:
                            n_tablas_indexadas += 1
                    if n_tablas_indexadas > 0:
                        txt_estado_pdf.value += f" · {n_tablas_indexadas} tabla(s) indexada(s)"

            chat_view.controls.append(ft.Text(f"📎 Has cargado el documento: {nombre_archivo}", color="#22c55e", size=13, italic=True))

            if ruta_final_archivo.exists():
                os.remove(ruta_final_archivo)

        except Exception as ex:
            txt_estado_pdf.value = "❌ Error al leer el PDF"
            chat_view.controls.append(_tarjeta_aviso(f"❌ No se pudo procesar el PDF: {ex}", tipo="error"))
        page.update()

   
    file_picker = ft.FilePicker()
    file_picker.on_result = al_seleccionar_archivo
    file_picker.on_upload = al_completar_subida
    page.overlay.append(file_picker)

    def abrir_buscador_archivos(e):
        file_picker.pick_files(allow_multiple=False, allowed_extensions=["pdf"])

    def cargar_conversacion_vieja(e):
        nonlocal historial
        chat_id = e.control.data
        chat_actual_id[0] = chat_id
        mensajes_guardados = obtener_mensajes_chat(chat_id, usuario_actual_id[0])
        if mensajes_guardados:
            historial = mensajes_guardados
            _renderizar_historial_en_chat()
            fragmentos_sesion.clear()
            txt_estado_pdf.value = ""
            page.update()

    chat_a_eliminar_id = [None]

    def cerrar_modal(e):
        modal_confirmacion.open = False
        page.update()

    def confirmar_eliminar_chat(e):
        id_para_borrar = chat_a_eliminar_id[0]
        if id_para_borrar:
            eliminar_chat_db(id_para_borrar, usuario_actual_id[0])
            if chat_actual_id[0] == id_para_borrar:
                nuevo_chat_click(None)
            else:
                actualizar_sidebar_historial()
        modal_confirmacion.open = False
        page.update()

    def abrir_modal_borrar(e):
        chat_a_eliminar_id[0] = e.control.data
        modal_confirmacion.open = True
        page.update()

    titulo_modal_borrar = ft.Text(t("confirmar_eliminar_titulo", idioma_var[0]))
    texto_modal_borrar = ft.Text(t("confirmar_eliminar_texto", idioma_var[0]))
    btn_cancelar_borrar = ft.TextButton(t("cancelar", idioma_var[0]), on_click=cerrar_modal)
    btn_confirmar_borrar = ft.TextButton(t("eliminar", idioma_var[0]), on_click=confirmar_eliminar_chat, style=ft.ButtonStyle(color="red"))
    modal_confirmacion = ft.AlertDialog(
        modal=True,
        title=titulo_modal_borrar,
        content=texto_modal_borrar,
        actions=[btn_cancelar_borrar, btn_confirmar_borrar],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    page.overlay.append(modal_confirmacion)

    def actualizar_sidebar_historial():
        lista_historial_ui.controls.clear()
        todos_los_chats = obtener_todos_los_chats(usuario_actual_id[0])
        for c_id, titulo in todos_los_chats:
            lista_historial_ui.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Container(
                            content=ft.Text(f"💬 {titulo}", color="#94a3b8", size=13, overflow=ft.TextOverflow.ELLIPSIS),
                            data=c_id,
                            on_click=cargar_conversacion_vieja,
                            expand=True
                        ),
                        ft.IconButton(
                            icon=ft.Icons.DELETE_OUTLINE,
                            icon_color="#ef4444",
                            icon_size=16,
                            data=c_id,
                            on_click=abrir_modal_borrar,
                            tooltip="Eliminar chat"
                        )
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    padding=ft.Padding(6, 2, 2, 2),
                    border_radius=6,
                    ink=True
                )
            )
        page.update()

    def nuevo_chat_click(e):
        nonlocal historial
        chat_actual_id[0] = str(time.time())
        historial = [construir_system_prompt(idioma_var[0])]
        fragmentos_sesion.clear()
        txt_estado_pdf.value = ""
        mostrar_pantalla_bienvenida()

    def enviar_mensaje(e):
        nonlocal historial
        if procesando_mensaje[0]:
            
            return
        texto = entrada.value.strip()
        if not texto: return

        procesando_mensaje[0] = True
        entrada.disabled = True
        btn_enviar.disabled = True
        page.update()
        try:
            _enviar_mensaje_interno(texto)
        finally:
            procesando_mensaje[0] = False
            entrada.disabled = False
            btn_enviar.disabled = False
            page.update()

    def _enviar_mensaje_interno(texto):
        nonlocal historial

        # 🚦 Límite de uso: se revisa ANTES de gastar cuota de Groq/PubMed.
        limite_chat = verificar_limite(usuario_actual_id[0], "chat", idioma=idioma_var[0])
        if not limite_chat["permitido"]:
            if len(historial) == 1:
                chat_view.controls.clear()
            entrada.value = ""
            chat_view.controls.append(_burbuja_usuario(texto))
            chat_view.controls.append(_tarjeta_aviso(f"🚦 {limite_chat['motivo']}", tipo="warning"))
            page.update()
            return
        registrar_solicitud(usuario_actual_id[0], "chat")

        if len(historial) == 1:
            chat_view.controls.clear()
        entrada.value = ""
        chat_view.controls.append(_burbuja_usuario(texto, indice_historial=len(historial)))
        page.update()

        # 🚨 Clasificación de riesgo clínico: herramienta EDUCATIVA, no un
        # servicio de manejo de emergencias ni de consejo médico personal.
        clasificacion = clasificar_consulta(texto)
        if clasificacion["categoria"] == "emergencia":
            texto_mensaje_emergencia = (
                mensaje_emergencia_salud_mental(idioma_var[0]) if clasificacion.get("subtipo") == "salud_mental"
                else mensaje_emergencia_medica(idioma_var[0])
            )
            chat_view.controls.append(_tarjeta_aviso(
                ft.Text(texto_mensaje_emergencia, color="#fca5a5", size=13), tipo="error"
            ))
            page.update()
            registrar_evento(
                usuario_actual_id[0], f"chat_emergencia_{clasificacion.get('subtipo') or 'medica'}",
                estado="bloqueado", texto_consulta=texto,
            )
            return

        sufijo_riesgo_personal = ""
        if clasificacion["categoria"] == "riesgo_personal":
            chat_view.controls.append(_tarjeta_aviso(aviso_riesgo_personal(idioma_var[0]), tipo="info"))
            page.update()
            sufijo_riesgo_personal = instruccion_refuerzo_riesgo_personal(idioma_var[0])

        # Panel plegable de "proceso" — colapsado por defecto. Aquí van los
        # pasos intermedios (búsqueda en PubMed, generación, verificación)
        # en vez de imprimirse sueltos y permanentes en el chat.
        panel_proceso, columna_pasos = _crear_panel_proceso()
        chat_view.controls.append(panel_proceso)
        page.update()

        tiempo_inicio_turno = time.time()
        contexto_pubmed = ""
        papers_relevantes = []
        if switch_pubmed_var:
            limite_pubmed = verificar_limite(usuario_actual_id[0], "pubmed", idioma=idioma_var[0])
            if not limite_pubmed["permitido"]:
                columna_pasos.controls.append(
                    ft.Text(f"🚦 {limite_pubmed['motivo']}", color="#f59e0b", size=11)
                )
                page.update()
            else:
                registrar_solicitud(usuario_actual_id[0], "pubmed")
                fila_pubmed = _agregar_paso_proceso(columna_pasos, t("buscando_pubmed", idioma_var[0]))
                try:
                    papers_relevantes, n_nuevos, total_unicos, intentos_debug = buscar_pubmed_estructurado(texto, usuario_actual_id[0])
                    papers_relevantes = filtrar_papers_por_evidencia(papers_relevantes, modo_evidencia_var[0])
                    if papers_relevantes:
                        contexto_pubmed = formatear_contexto_papers(papers_relevantes)
                        _completar_paso_proceso(fila_pubmed, t("pubmed_con_resultados", idioma_var[0], n=len(papers_relevantes)))
                        agregar_papers_a_chat(chat_view, page, papers_relevantes, n_nuevos, total_unicos)
                    else:
                        _completar_paso_proceso(
                            fila_pubmed,
                            t("pubmed_sin_resultados", idioma_var[0], n=total_unicos),
                        )
                    if intentos_debug:
                        columna_pasos.controls.append(
                            ft.Text("🔎 " + " | ".join(intentos_debug), color="#475569", size=10, italic=True)
                        )
                        page.update()
                except Exception as ex_pubmed:
                    _completar_paso_proceso(fila_pubmed, t("error_pubmed", idioma_var[0], error=ex_pubmed), error=True)
        if client:
            try:
                fragmentos_relevantes = buscar_fragmentos_relevantes(usuario_actual_id[0], texto)
                if fragmentos_relevantes:
                    bloque_pdf = "[FRAGMENTOS RELEVANTES DE TUS DOCUMENTOS, recuperados por búsqueda semántica]:\n"
                    for i, (similitud, fuente, frag_texto, tipo_texto) in enumerate(fragmentos_relevantes, start=1):
                        ocr_tag = " · vía OCR" if tipo_texto == "ocr" else ""
                        bloque_pdf += f"\n[F{i}] (Fuente: {fuente} | similitud: {similitud:.2f}{ocr_tag})\n{frag_texto}\n"
                elif fragmentos_sesion:
                    bloque_pdf = "\n".join(fragmentos_sesion)
                    fragmentos_sesion.clear()
                    fragmentos_relevantes = []
                else:
                    bloque_pdf = ""
                    fragmentos_relevantes = []

                if fragmentos_relevantes:
                    columna_pasos.controls.append(
                        ft.Text(f"📎 {t('fragmentos_usados', idioma_var[0], n=len(fragmentos_relevantes))}",
                                color="#475569", size=11, italic=True)
                    )
                    page.update()

                # 🔤 Glosario ICD-11: solo si el idioma NO es inglés (PubMed ya
                # está en inglés, no hace falta terminología oficial extra) y
                # solo si no se pasó el límite de uso — un fallo aquí nunca
                # debe frenar la respuesta principal, así que va todo envuelto
                # y con su propio try/except silencioso.
                bloque_icd11 = ""
                if idioma_var[0] != "en":
                    limite_icd11 = verificar_limite(usuario_actual_id[0], "icd11", idioma=idioma_var[0])
                    if limite_icd11["permitido"]:
                        fila_icd11 = _agregar_paso_proceso(columna_pasos, t("verificando_terminologia_icd11", idioma_var[0]))
                        try:
                            registrar_solicitud(usuario_actual_id[0], "icd11")
                            glosario = construir_glosario_icd11(texto, idioma_var[0])
                            bloque_icd11 = glosario["bloque_contexto"]
                            if glosario["terminos_encontrados"]:
                                _completar_paso_proceso(
                                    fila_icd11,
                                    t("terminologia_icd11_verificada", idioma_var[0], n=len(glosario["terminos_encontrados"])),
                                )
                            else:
                                _completar_paso_proceso(fila_icd11, t("icd11_sin_terminos", idioma_var[0]))
                        except Exception:
                            _completar_paso_proceso(fila_icd11, t("icd11_sin_terminos", idioma_var[0]), error=True)

                bloque_total_contexto = f"{bloque_pdf}\n{contexto_pubmed}\n{bloque_icd11}"

                historial.append({"role": "user", "content": f"{bloque_total_contexto}\nPregunta: {texto}{sufijo_riesgo_personal}"})
                historial = recortar_historial(historial)
                mensajes_para_groq = [{"role": m["role"], "content": m["content"]} for m in historial]
                # El idioma puede haberse cambiado a mitad de conversación —
                # se sobreescribe el mensaje de sistema con el idioma ACTUAL
                # en vez de usar el que se guardó cuando se creó el chat, así
                # el cambio de idioma aplica desde el siguiente mensaje sin
                # necesidad de abrir un chat nuevo.
                mensajes_para_groq[0] = construir_system_prompt(idioma_var[0])

                fila_generando = _agregar_paso_proceso(columna_pasos, t("generando_respuesta", idioma_var[0]))

                response_stream = client.chat.completions.create(
                    model=MODELO_CHAT,
                    messages=mensajes_para_groq,
                    temperature=0.2,
                    stream=True
                )
                fila_respuesta, ai_markdown = _burbuja_ai("", pregunta=texto)
                chat_view.controls.append(fila_respuesta)
                page.update()
                full_response = ""
                _contador_chunks = 0
                for chunk in response_stream:
                    delta = getattr(chunk.choices[0].delta, "content", None)
                    if delta:
                        full_response += delta
                        ai_markdown.value = full_response
                        _contador_chunks += 1
                        # Actualizar la UI cada pocos fragmentos (no en cada
                        # token) — se ve igual de "vivo" pero sin recargar
                        # de renders el Markdown en cada carácter.
                        if _contador_chunks % 3 == 0 or "\n" in delta:
                            page.update()
                ai_markdown.value = full_response
                _completar_paso_proceso(fila_generando, t("respuesta_generada", idioma_var[0]))
                page.update()

                if detectar_citas_alucinadas(full_response, len(papers_relevantes), len(fragmentos_relevantes)):
                    chat_view.controls.append(_tarjeta_aviso(
                        "⚠️ Esta respuesta incluye referencias numeradas (ej. [1], [F1]) pero no "
                        "se encontró ningún paper de PubMed ni fragmento de tus documentos para "
                        "esta pregunta. Esas citas son probablemente inventadas por el modelo — "
                        "no las tomes como evidencia real.",
                        tipo="error",
                    ))

                citas_fuera_rango = detectar_citas_fuera_de_rango(
                    full_response, len(papers_relevantes), len(fragmentos_relevantes)
                )
                if citas_fuera_rango["papers_invalidos"] or citas_fuera_rango["fragmentos_invalidos"]:
                    partes_invalidas = []
                    if citas_fuera_rango["papers_invalidos"]:
                        partes_invalidas.append(
                            "papers " + ", ".join(f"[{n}]" for n in citas_fuera_rango["papers_invalidos"])
                        )
                    if citas_fuera_rango["fragmentos_invalidos"]:
                        partes_invalidas.append(
                            "fragmentos " + ", ".join(f"[F{n}]" for n in citas_fuera_rango["fragmentos_invalidos"])
                        )
                    chat_view.controls.append(_tarjeta_aviso(
                        f"⚠️ La respuesta cita {', '.join(partes_invalidas)}, que no corresponden a "
                        "ninguna fuente real de esta búsqueda — probablemente un número inventado "
                        "por el modelo. No confíes en esa cita específica.",
                        tipo="error",
                    ))

                if detectar_negacion_contradictoria(full_response, len(papers_relevantes), len(fragmentos_relevantes)):
                    full_response_limpio = limpiar_negacion_contradictoria(
                        full_response, len(papers_relevantes), len(fragmentos_relevantes)
                    )
                    se_limpio = full_response_limpio != full_response
                    if se_limpio:
                        full_response = full_response_limpio
                        ai_markdown.value = full_response
                        page.update()
                    mensaje_alerta = (
                        "🤔 El modelo dijo que no encontró papers/evidencia, pero SÍ había "
                        f"{len(papers_relevantes)} paper(s) y {len(fragmentos_relevantes)} fragmento(s) "
                        "reales disponibles este turno. "
                        + ("Se quitó esa frase falsa del texto de arriba automáticamente — revisa el "
                           "panel de Fuentes abajo, ahí están los papers reales que sí se usaron."
                           if se_limpio else
                           "No se pudo limpiar automáticamente (el modelo la escribió distinto a lo "
                           "esperado) — revisa el panel de Fuentes abajo, la frase de arriba no es "
                           "confiable.")
                    )
                    chat_view.controls.append(_tarjeta_aviso(mensaje_alerta, tipo="info"))

                contradicciones = verificar_consistencia_fisiologica(texto, full_response)
                if contradicciones:
                    lineas_contradiccion = [
                        ft.Text(
                            "🧬 Posible inconsistencia fisiológica detectada — revisa antes de confiar en este diagnóstico:",
                            color="#fbbf24", size=12, weight=ft.FontWeight.BOLD,
                        )
                    ]
                    for c in contradicciones:
                        lineas_contradiccion.append(
                            ft.Text(f"• {c['diagnostico']}: {c['explicacion']}", color="#fde68a", size=11)
                        )
                    chat_view.controls.append(_tarjeta_aviso(
                        ft.Column(lineas_contradiccion, spacing=3), tipo="warning"
                    ))

                fuentes = construir_lista_fuentes(papers_relevantes, fragmentos_relevantes, full_response)

                fact = None
                if switch_factualidad_var and fuentes:
                    fila_fact = _agregar_paso_proceso(columna_pasos, t("verificando_afirmaciones", idioma_var[0]))
                    contexto_juez = construir_contexto_para_juez(papers_relevantes, fragmentos_relevantes)
                    fact = evaluar_factualidad(full_response, contexto_juez)
                    _completar_paso_proceso(fila_fact, t("afirmaciones_verificadas", idioma_var[0]))

                msg_asistente = {"role": "assistant", "content": full_response}
                if fuentes:
                    msg_asistente["_fuentes"] = fuentes
                if fact:
                    msg_asistente["_factualidad"] = fact
                historial.append(msg_asistente)
                historial = recortar_historial(historial)

                if fuentes:
                    chat_view.controls.append(construir_panel_fuentes(fuentes))
                if fact:
                    anexar_badge_factualidad(chat_view, page, fact)

                resumen_evidencia = resumen_evidencia_citada(fuentes) if fuentes else {"disponible": False}
                if resumen_evidencia["disponible"]:
                    msg_asistente["_evidencia"] = resumen_evidencia
                    nivel_traducido = t_categoria(resumen_evidencia["nivel_mas_fuerte"], idioma_var[0])
                    chat_view.controls.append(_tarjeta_aviso(
                        "🏅 " + t(
                            "badge_evidencia_citada", idioma_var[0],
                            nivel=nivel_traducido, n=resumen_evidencia["n_papers_citados"],
                        ),
                        tipo="info",
                    ))

                es_primer_mensaje = len(historial) <= 3
                titulo_chat = "Consulta Médica"
                if es_primer_mensaje:
                    titulo_chat = generar_titulo_con_ia(texto, idioma=idioma_var[0])
                else:
                    todos = obtener_todos_los_chats(usuario_actual_id[0])
                    for c_id, titulo_existente in todos:
                        if c_id == chat_actual_id[0]:
                            titulo_chat = titulo_existente
                            break
                guardar_chat_db(chat_actual_id[0], titulo_chat, historial, usuario_actual_id[0])
                actualizar_sidebar_historial()
                registrar_evento(
                    usuario_actual_id[0], "chat", modelo=MODELO_CHAT, estado="ok",
                    latencia_ms=int((time.time() - tiempo_inicio_turno) * 1000),
                    n_fuentes=len(fuentes) if fuentes else 0, texto_consulta=texto,
                )
                page.update()
            except Exception as ex:
                chat_view.controls.append(_tarjeta_aviso(t("error_generico", idioma_var[0], error=ex), tipo="error"))
                registrar_evento(
                    usuario_actual_id[0], "chat", modelo=MODELO_CHAT, estado="error",
                    latencia_ms=int((time.time() - tiempo_inicio_turno) * 1000), texto_consulta=texto,
                )
                page.update()
        else:
            chat_view.controls.append(_tarjeta_aviso(t("api_no_configurado", idioma_var[0]), tipo="error"))
            page.update()

    
    def actualizar_contador_flashcards():
        if usuario_actual_id[0] is None:
            return
        n = contar_flashcards_pendientes(usuario_actual_id[0])
        txt_contador_flashcards.value = t("repasar", idioma_var[0], n=n)
        page.update()

    def generar_flashcards_click(e):
        idioma = idioma_var[0]
        tema = entrada.value.strip()
        if not tema:
            txt_estado_flashcards.value = t("escribe_tema_primero", idioma)
            page.update()
            return

        limite = verificar_limite(usuario_actual_id[0], "flashcards", idioma=idioma_var[0])
        if not limite["permitido"]:
            txt_estado_flashcards.value = f"🚦 {limite['motivo']}"
            page.update()
            return
        registrar_solicitud(usuario_actual_id[0], "flashcards")

        txt_estado_flashcards.value = t("generando_flashcards", idioma)
        page.update()
       
        fragmentos = buscar_fragmentos_relevantes(usuario_actual_id[0], tema)
        if fragmentos:
            texto_fuente = "\n\n".join(frag[2] for frag in fragmentos)
            fuente_etiqueta = t("tus_documentos", idioma)
        else:
            texto_fuente = tema
            fuente_etiqueta = t("conocimiento_general", idioma)

        tiempo_inicio = time.time()
        creadas, diagnostico = generar_flashcards_con_ia(usuario_actual_id[0], texto_fuente, tema=tema, fuente=fuente_etiqueta, idioma=idioma)
        latencia_ms = int((time.time() - tiempo_inicio) * 1000)
        registrar_evento(
            usuario_actual_id[0], "flashcards", modelo=MODELO_AUXILIAR,
            estado="ok" if creadas else "error", latencia_ms=latencia_ms, texto_consulta=tema,
        )
        if creadas:
            
            registrar_concepto_estudiado(usuario_actual_id[0], tema, tipo="flashcards", fuente=fuente_etiqueta)
            relacionados = obtener_temas_relacionados(usuario_actual_id[0], tema)
            mensaje = t("flashcards_creadas", idioma, n=len(creadas), tema=tema)
            if relacionados:
                nombres = ", ".join(r["tema"] for r in relacionados)
                mensaje += "\n" + t("esto_se_relaciona_con", idioma, temas=nombres)
            txt_estado_flashcards.value = mensaje
            entrada.value = ""
        else:
            txt_estado_flashcards.value = t("flashcards_no_generadas", idioma, diag=diagnostico)
        actualizar_contador_flashcards()
        page.update()

    def volver_al_chat_desde_repaso(e):
        en_modo_repaso[0] = False
        chat_view.controls.clear()
        mostrar_pantalla_bienvenida()
        actualizar_contador_flashcards()

    def mostrar_vista_repaso():
        chat_view.controls.clear()
        idioma = idioma_var[0]
        if indice_flashcard[0] >= len(flashcards_sesion):
            chat_view.controls.append(ft.Text(t("repaso_terminado", idioma), size=18, weight=ft.FontWeight.BOLD, color="#22c55e"))
            chat_view.controls.append(ft.TextButton(t("volver_al_chat", idioma), on_click=volver_al_chat_desde_repaso))
            page.update()
            actualizar_contador_flashcards()
            return

        tarjeta = flashcards_sesion[indice_flashcard[0]]
        subtitulo = t("tarjeta_de", idioma, n=indice_flashcard[0] + 1, t=len(flashcards_sesion))
        if tarjeta.get("tema"):
            subtitulo += f" · {tarjeta['tema']}"
        controles = [
            ft.Text(subtitulo, size=12, color="#64748b"),
            ft.Container(
                content=ft.Text(tarjeta["pregunta"], size=16, weight=ft.FontWeight.BOLD, color="#f8fafc"),
                padding=20, bgcolor="#1e1f28", border_radius=10, border=ft.border.all(1, "#2a2b36"),
            ),
        ]
        if mostrando_respuesta_flashcard[0]:
            controles.append(
                ft.Container(
                    content=ft.Text(tarjeta["respuesta"], size=14, color="#e2e8f0"),
                    padding=20, bgcolor="#1e293b", border_radius=10, border=ft.border.all(1, "#3b82f6"),
                )
            )
            controles.append(
                ft.Row([
                    ft.FilledButton(t("boton_otra_vez", idioma), on_click=lambda e: calificar_flashcard("otra_vez"),
                                     style=ft.ButtonStyle(bgcolor="#ef4444", color="#ffffff")),
                    ft.FilledButton(t("boton_dificil", idioma), on_click=lambda e: calificar_flashcard("dificil"),
                                     style=ft.ButtonStyle(bgcolor="#f59e0b", color="#ffffff")),
                    ft.FilledButton(t("boton_bien", idioma), on_click=lambda e: calificar_flashcard("bien"),
                                     style=ft.ButtonStyle(bgcolor="#3b82f6", color="#ffffff")),
                    ft.FilledButton(t("boton_facil", idioma), on_click=lambda e: calificar_flashcard("facil"),
                                     style=ft.ButtonStyle(bgcolor="#22c55e", color="#ffffff")),
                ], spacing=8, wrap=True)
            )
        else:
            controles.append(
                ft.FilledButton(t("mostrar_respuesta", idioma), on_click=mostrar_respuesta_flashcard_click,
                                 style=ft.ButtonStyle(bgcolor="#3b82f6", color="#ffffff"))
            )
        controles.append(ft.TextButton(t("salir_del_repaso", idioma), on_click=volver_al_chat_desde_repaso))
        chat_view.controls.extend(controles)
        page.update()

    def mostrar_respuesta_flashcard_click(e):
        mostrando_respuesta_flashcard[0] = True
        mostrar_vista_repaso()

    def calificar_flashcard(boton):
        tarjeta = flashcards_sesion[indice_flashcard[0]]
        registrar_repaso(usuario_actual_id[0], tarjeta["id"], boton)
        indice_flashcard[0] += 1
        mostrando_respuesta_flashcard[0] = False
        mostrar_vista_repaso()

    def iniciar_repaso(e):
        flashcards_sesion[:] = obtener_flashcards_pendientes(usuario_actual_id[0])
        indice_flashcard[0] = 0
        mostrando_respuesta_flashcard[0] = False
        en_modo_repaso[0] = True
        if not flashcards_sesion:
            chat_view.controls.clear()
            chat_view.controls.append(ft.Text(t("sin_flashcards_pendientes", idioma_var[0]), size=16, color="#e2e8f0"))
            chat_view.controls.append(ft.TextButton(t("volver_al_chat", idioma_var[0]), on_click=volver_al_chat_desde_repaso))
            page.update()
            return
        mostrar_vista_repaso()

   
    def generar_examen_click(e):
        idioma = idioma_var[0]
        tema = entrada.value.strip()
        if not tema:
            txt_estado_examen.value = t("escribe_tema_primero", idioma)
            page.update()
            return

        limite = verificar_limite(usuario_actual_id[0], "examen", idioma=idioma_var[0])
        if not limite["permitido"]:
            txt_estado_examen.value = f"🚦 {limite['motivo']}"
            page.update()
            return
        registrar_solicitud(usuario_actual_id[0], "examen")

        txt_estado_examen.value = t("generando_examen", idioma)
        page.update()
        fragmentos = buscar_fragmentos_relevantes(usuario_actual_id[0], tema)
        if fragmentos:
            texto_fuente = "\n\n".join(frag[2] for frag in fragmentos)
            fuente_etiqueta = t("tus_documentos", idioma)
        else:
            texto_fuente = tema
            fuente_etiqueta = t("conocimiento_general", idioma)

        tiempo_inicio = time.time()
        creadas, diagnostico = generar_examen_con_ia(usuario_actual_id[0], texto_fuente, tema=tema, fuente=fuente_etiqueta, idioma=idioma)
        registrar_evento(
            usuario_actual_id[0], "examen", modelo=MODELO_AUXILIAR,
            estado="ok" if creadas else "error",
            latencia_ms=int((time.time() - tiempo_inicio) * 1000), texto_consulta=tema,
        )
        if creadas:
            registrar_concepto_estudiado(usuario_actual_id[0], tema, tipo="examen", fuente=fuente_etiqueta)
            txt_estado_examen.value = t("examen_creado", idioma, n=len(creadas), tema=tema)
            entrada.value = ""
            examen_sesion[:] = creadas
            indice_pregunta_examen[0] = 0
            opcion_seleccionada_examen[0] = None
            respuesta_revelada_examen[0] = False
            aciertos_examen[0] = 0
            page.update()
            mostrar_vista_examen()
            return
        else:
            txt_estado_examen.value = t("examen_no_generado", idioma, diag=diagnostico)
        page.update()

    def volver_al_chat_desde_examen(e):
        chat_view.controls.clear()
        mostrar_pantalla_bienvenida()

    def mostrar_vista_examen():
        chat_view.controls.clear()
        idioma = idioma_var[0]
        if indice_pregunta_examen[0] >= len(examen_sesion):
            total = len(examen_sesion)
            controles_resumen = [
                ft.Text(t("examen_terminado", idioma), size=18, weight=ft.FontWeight.BOLD, color="#22c55e"),
                ft.Text(t("aciertos_de", idioma, a=aciertos_examen[0], t=total), size=15, color="#e2e8f0"),
                ft.TextButton(t("volver_al_chat", idioma), on_click=volver_al_chat_desde_examen),
            ]
            chat_view.controls.extend(controles_resumen)
            page.update()
            return

        pregunta_actual = examen_sesion[indice_pregunta_examen[0]]
        controles = [
            ft.Text(t("pregunta_de", idioma, n=indice_pregunta_examen[0] + 1, t=len(examen_sesion)), size=12, color="#64748b"),
            ft.Container(
                content=ft.Text(pregunta_actual["pregunta"], size=16, weight=ft.FontWeight.BOLD, color="#f8fafc"),
                padding=20, bgcolor="#1e1f28", border_radius=10, border=ft.border.all(1, "#2a2b36"),
            ),
        ]

        for i, opcion in enumerate(pregunta_actual["opciones"]):
            if respuesta_revelada_examen[0]:
                if i == pregunta_actual["respuesta_correcta"]:
                    color_fondo, color_borde = "#052e1a", "#22c55e"
                elif i == opcion_seleccionada_examen[0]:
                    color_fondo, color_borde = "#2d0f0f", "#ef4444"
                else:
                    color_fondo, color_borde = "#1e1f28", "#2a2b36"
                controles.append(
                    ft.Container(
                        content=ft.Text(opcion, size=14, color="#e2e8f0"),
                        padding=14, bgcolor=color_fondo, border_radius=8, border=ft.border.all(1, color_borde),
                    )
                )
            else:
                controles.append(
                    ft.FilledButton(
                        content=ft.Text(opcion, color="#e2e8f0"),
                        style=ft.ButtonStyle(bgcolor="#1e1f28", shape=ft.RoundedRectangleBorder(radius=8)),
                        on_click=lambda e, idx=i: seleccionar_opcion_examen(idx),
                    )
                )

        if respuesta_revelada_examen[0]:
            if pregunta_actual.get("explicacion"):
                controles.append(ft.Text(f"💡 {pregunta_actual['explicacion']}", size=13, color="#94a3b8", italic=True))
            controles.append(
                ft.FilledButton(t("siguiente", idioma), on_click=siguiente_pregunta_examen,
                                 style=ft.ButtonStyle(bgcolor="#3b82f6", color="#ffffff"))
            )

        controles.append(ft.TextButton(t("salir_del_examen", idioma), on_click=volver_al_chat_desde_examen))
        chat_view.controls.extend(controles)
        page.update()

    def seleccionar_opcion_examen(indice):
        pregunta_actual = examen_sesion[indice_pregunta_examen[0]]
        opcion_seleccionada_examen[0] = indice
        respuesta_revelada_examen[0] = True
        es_correcta = indice == pregunta_actual["respuesta_correcta"]
        if es_correcta:
            aciertos_examen[0] += 1
        if pregunta_actual.get("id"):
            registrar_intento_examen(usuario_actual_id[0], pregunta_actual["id"], es_correcta)
        mostrar_vista_examen()

    def siguiente_pregunta_examen(e):
        indice_pregunta_examen[0] += 1
        opcion_seleccionada_examen[0] = None
        respuesta_revelada_examen[0] = False
        mostrar_vista_examen()

    
    def volver_al_chat_desde_progreso(e):
        chat_view.controls.clear()
        mostrar_pantalla_bienvenida()

    def mostrar_vista_progreso(e):
        chat_view.controls.clear()
        idioma = idioma_var[0]
        resumen = resumen_progreso(usuario_actual_id[0])
        niveles = evaluar_nivel_por_tema(usuario_actual_id[0])

        controles = [
            ft.Text(t("progreso_titulo", idioma), size=18, weight=ft.FontWeight.BOLD, color="#f8fafc"),
            ft.Row([
                ft.Text(t("temas_estudiados", idioma, n=resumen['n_temas']), size=12, color="#94a3b8"),
                ft.Text(t("n_flashcards", idioma, n=resumen['n_flashcards']), size=12, color="#94a3b8"),
                ft.Text(t("n_preguntas_examen", idioma, n=resumen['n_preguntas']), size=12, color="#94a3b8"),
                ft.Text(t("n_intentos_respondidos", idioma, n=resumen['n_intentos']), size=12, color="#94a3b8"),
            ], spacing=16, wrap=True),
            ft.Divider(color="#1f212a"),
        ]

        if not niveles:
            controles.append(ft.Text(
                t("sin_examenes_suficientes", idioma),
                size=13, color="#64748b", italic=True,
            ))
        else:
            controles.append(ft.Text(t("nivel_por_tema", idioma), size=13, color="#e2e8f0", weight=ft.FontWeight.BOLD))
            claves_nivel = {
                "Necesita repaso": "nivel_necesita_repaso", "En progreso": "nivel_en_progreso",
                "Dominado": "nivel_dominado", "Muy pocos datos aún": "nivel_pocos_datos",
            }
            colores_nivel = {
                "Necesita repaso": "#ef4444", "En progreso": "#f59e0b",
                "Dominado": "#22c55e", "Muy pocos datos aún": "#64748b",
            }
            for item in niveles:
                color_nivel = colores_nivel.get(item["nivel"], "#94a3b8")
                nivel_traducido = t(claves_nivel.get(item["nivel"], "nivel_pocos_datos"), idioma)
                controles.append(
                    ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Text(item["tema"], size=14, weight=ft.FontWeight.BOLD, color="#f8fafc", expand=True),
                                ft.Container(
                                    content=ft.Text(nivel_traducido, size=11, color="#ffffff"),
                                    bgcolor=color_nivel, border_radius=6, padding=ft.Padding(8, 3, 8, 3),
                                ),
                            ]),
                            ft.Text(
                                t("correctas_pct", idioma, a=item['aciertos'], t=item['n_intentos'], p=f"{item['porcentaje']*100:.0f}"),
                                size=12, color="#94a3b8",
                            ),
                        ], spacing=4),
                        padding=12, bgcolor="#1e1f28", border_radius=8, border=ft.border.all(1, "#2a2b36"),
                    )
                )

        controles.append(ft.TextButton(t("volver_al_chat", idioma), on_click=volver_al_chat_desde_progreso))
        chat_view.controls.extend(controles)
        page.update()

    def mostrar_vista_calculadoras(e):
        idioma = idioma_var[0]

        def volver_al_chat_desde_calculadoras(e):
            chat_view.controls.clear()
            mostrar_pantalla_bienvenida()

        def _caja_resultado_calculadora():
            return ft.Container(
                content=ft.Text("", size=13, color="#94a3b8"),
                padding=12, bgcolor="#1e1f28", border_radius=8,
                border=ft.border.all(1, "#2a2b36"), visible=False,
            )

        def _mostrar_error_calculadora(caja, mensaje):
            caja.content = ft.Text(f"❌ {mensaje}", color="#ef4444", size=13)
            caja.border = ft.border.all(1, "#ef4444")
            caja.visible = True
            page.update()

        chat_view.controls.clear()

        # --- IMC ---
        campo_peso_imc = ft.TextField(label=t("campo_peso", idioma), width=140, border_color="#1f212a", bgcolor="#16171d", color="#e2e8f0")
        campo_altura_imc = ft.TextField(label=t("campo_altura", idioma), width=140, border_color="#1f212a", bgcolor="#16171d", color="#e2e8f0")
        caja_imc = _caja_resultado_calculadora()

        def click_imc(e):
            r = calcular_imc(campo_peso_imc.value, campo_altura_imc.value, idioma=idioma)
            if "error" in r:
                _mostrar_error_calculadora(caja_imc, r["error"])
                return
            caja_imc.border = ft.border.all(1, "#2a2b36")
            caja_imc.content = ft.Column([
                ft.Text(t("resultado_imc", idioma, valor=r["valor"]), size=15, weight=ft.FontWeight.BOLD, color="#f8fafc"),
                ft.Text(t_categoria(r["categoria"], idioma), size=13, color="#94a3b8"),
            ], spacing=2)
            caja_imc.visible = True
            page.update()

        panel_imc = ft.ExpansionTile(
            title=ft.Text(t("panel_imc", idioma), size=14, weight=ft.FontWeight.BOLD, color="#e2e8f0"),
            initially_expanded=True,
            controls=[ft.Container(
                content=ft.Column([
                    ft.Row([campo_peso_imc, campo_altura_imc], spacing=10, wrap=True),
                    ft.FilledButton(t("boton_calcular", idioma), on_click=click_imc, style=ft.ButtonStyle(bgcolor="#3b82f6", color="#ffffff")),
                    caja_imc,
                ], spacing=10),
                padding=12,
            )],
        )

        # --- Superficie corporal (BSA) ---
        campo_peso_bsa = ft.TextField(label=t("campo_peso", idioma), width=140, border_color="#1f212a", bgcolor="#16171d", color="#e2e8f0")
        campo_altura_bsa = ft.TextField(label=t("campo_altura", idioma), width=140, border_color="#1f212a", bgcolor="#16171d", color="#e2e8f0")
        dropdown_formula_bsa = ft.Dropdown(
            label=t("campo_formula", idioma), width=160, value="mosteller",
            options=[ft.dropdown.Option("mosteller", "Mosteller"), ft.dropdown.Option("dubois", "Du Bois")],
            border_color="#1f212a", bgcolor="#16171d", color="#e2e8f0",
        )
        caja_bsa = _caja_resultado_calculadora()

        def click_bsa(e):
            r = calcular_superficie_corporal(campo_peso_bsa.value, campo_altura_bsa.value, dropdown_formula_bsa.value, idioma=idioma)
            if "error" in r:
                _mostrar_error_calculadora(caja_bsa, r["error"])
                return
            caja_bsa.border = ft.border.all(1, "#2a2b36")
            caja_bsa.content = ft.Text(t("resultado_bsa", idioma, formula=r["formula"], valor=r["valor"]), size=14, color="#f8fafc")
            caja_bsa.visible = True
            page.update()

        panel_bsa = ft.ExpansionTile(
            title=ft.Text(t("panel_bsa", idioma), size=14, weight=ft.FontWeight.BOLD, color="#e2e8f0"),
            controls=[ft.Container(
                content=ft.Column([
                    ft.Row([campo_peso_bsa, campo_altura_bsa, dropdown_formula_bsa], spacing=10, wrap=True),
                    ft.FilledButton(t("boton_calcular", idioma), on_click=click_bsa, style=ft.ButtonStyle(bgcolor="#3b82f6", color="#ffffff")),
                    caja_bsa,
                ], spacing=10),
                padding=12,
            )],
        )

        # --- Función renal (Cockcroft-Gault + CKD-EPI) ---
        campo_edad_renal = ft.TextField(label=t("campo_edad", idioma), width=110, border_color="#1f212a", bgcolor="#16171d", color="#e2e8f0")
        campo_peso_renal = ft.TextField(label=t("campo_peso", idioma), width=110, border_color="#1f212a", bgcolor="#16171d", color="#e2e8f0")
        campo_altura_renal = ft.TextField(label=t("campo_altura_opcional", idioma), width=170, border_color="#1f212a", bgcolor="#16171d", color="#e2e8f0")
        campo_cr_renal = ft.TextField(label=t("campo_creatinina", idioma), width=170, border_color="#1f212a", bgcolor="#16171d", color="#e2e8f0")
        dropdown_sexo_renal = ft.Dropdown(
            label=t("campo_sexo", idioma), width=100, options=[ft.dropdown.Option("M", "M"), ft.dropdown.Option("F", "F")],
            border_color="#1f212a", bgcolor="#16171d", color="#e2e8f0",
        )
        switch_peso_ajustado = ft.Switch(label=t("usar_peso_ajustado", idioma), value=False)
        caja_renal = _caja_resultado_calculadora()

        def click_renal(e):
            cg = calcular_aclaramiento_creatinina(
                campo_edad_renal.value, campo_peso_renal.value, campo_cr_renal.value,
                dropdown_sexo_renal.value, altura_cm=campo_altura_renal.value,
                usar_peso_ajustado=switch_peso_ajustado.value, idioma=idioma,
            )
            if "error" in cg:
                _mostrar_error_calculadora(caja_renal, cg["error"])
                return
            egfr = calcular_egfr_ckd_epi(campo_edad_renal.value, campo_cr_renal.value, dropdown_sexo_renal.value, idioma=idioma)
            controles = [
                ft.Text(t("resultado_cockcroft", idioma, valor=cg["valor_ml_min"]), size=14, weight=ft.FontWeight.BOLD, color="#f8fafc"),
                ft.Text(t_categoria(cg["categoria"], idioma) + (f" · {cg['nota']}" if cg.get("nota") else ""), size=12, color="#94a3b8"),
            ]
            if "error" not in egfr:
                controles.append(ft.Divider(height=6, color="#2a2b36"))
                controles.append(ft.Text(t("resultado_ckdepi", idioma, valor=egfr["valor_ml_min_173"]), size=13, color="#cbd5e1"))
                controles.append(ft.Text(t_categoria(egfr["etapa"], idioma), size=12, color="#94a3b8"))
            caja_renal.border = ft.border.all(1, "#2a2b36")
            caja_renal.content = ft.Column(controles, spacing=2)
            caja_renal.visible = True
            page.update()

        panel_renal = ft.ExpansionTile(
            title=ft.Text(t("panel_renal", idioma), size=14, weight=ft.FontWeight.BOLD, color="#e2e8f0"),
            controls=[ft.Container(
                content=ft.Column([
                    ft.Row([campo_edad_renal, campo_peso_renal, campo_altura_renal, campo_cr_renal, dropdown_sexo_renal], spacing=10, wrap=True),
                    switch_peso_ajustado,
                    ft.FilledButton(t("boton_calcular", idioma), on_click=click_renal, style=ft.ButtonStyle(bgcolor="#3b82f6", color="#ffffff")),
                    caja_renal,
                ], spacing=10),
                padding=12,
            )],
        )

        # --- Dosis por peso ---
        campo_peso_dosis = ft.TextField(label=t("campo_peso", idioma), width=120, border_color="#1f212a", bgcolor="#16171d", color="#e2e8f0")
        campo_mgkg_dosis = ft.TextField(label=t("campo_mgkg", idioma), width=100, border_color="#1f212a", bgcolor="#16171d", color="#e2e8f0")
        campo_max_dosis = ft.TextField(label=t("campo_dosis_max", idioma), width=180, border_color="#1f212a", bgcolor="#16171d", color="#e2e8f0")
        campo_tomas_dosis = ft.TextField(label=t("campo_tomas_dia", idioma), width=150, border_color="#1f212a", bgcolor="#16171d", color="#e2e8f0")
        caja_dosis = _caja_resultado_calculadora()

        def click_dosis(e):
            r = calcular_dosis_por_peso(
                campo_peso_dosis.value, campo_mgkg_dosis.value,
                dosis_max_mg=campo_max_dosis.value or None,
                tomas_por_dia=campo_tomas_dosis.value or None, idioma=idioma,
            )
            if "error" in r:
                _mostrar_error_calculadora(caja_dosis, r["error"])
                return
            controles = [ft.Text(t("resultado_dosis_total", idioma, valor=r["dosis_total_mg"]), size=15, weight=ft.FontWeight.BOLD, color="#f8fafc")]
            if r.get("techo_aplicado"):
                controles.append(ft.Text(t("aviso_techo_dosis", idioma), size=12, color="#f59e0b"))
            if r.get("piso_aplicado"):
                controles.append(ft.Text(t("aviso_piso_dosis", idioma), size=12, color="#f59e0b"))
            if "dosis_por_toma_mg" in r:
                controles.append(ft.Text(t("dosis_por_toma", idioma, dosis=r["dosis_por_toma_mg"], tomas=r["tomas_por_dia"]), size=13, color="#94a3b8"))
            caja_dosis.border = ft.border.all(1, "#2a2b36")
            caja_dosis.content = ft.Column(controles, spacing=2)
            caja_dosis.visible = True
            page.update()

        panel_dosis = ft.ExpansionTile(
            title=ft.Text(t("panel_dosis", idioma), size=14, weight=ft.FontWeight.BOLD, color="#e2e8f0"),
            controls=[ft.Container(
                content=ft.Column([
                    ft.Row([campo_peso_dosis, campo_mgkg_dosis, campo_max_dosis, campo_tomas_dosis], spacing=10, wrap=True),
                    ft.FilledButton(t("boton_calcular", idioma), on_click=click_dosis, style=ft.ButtonStyle(bgcolor="#3b82f6", color="#ffffff")),
                    caja_dosis,
                ], spacing=10),
                padding=12,
            )],
        )

        # --- Ajuste de dosis por función renal (tabla de referencia) ---
        campo_farmaco_ajuste = ft.TextField(label=t("campo_farmaco", idioma), width=180, border_color="#1f212a", bgcolor="#16171d", color="#e2e8f0")
        campo_crcl_ajuste = ft.TextField(label=t("campo_aclaramiento", idioma), width=180, border_color="#1f212a", bgcolor="#16171d", color="#e2e8f0")
        caja_ajuste = _caja_resultado_calculadora()

        def click_ajuste(e):
            r = obtener_ajuste_renal(campo_farmaco_ajuste.value, campo_crcl_ajuste.value, idioma=idioma)
            if "error" in r:
                _mostrar_error_calculadora(caja_ajuste, r["error"])
                return
            if not r.get("encontrado"):
                caja_ajuste.border = ft.border.all(1, "#f59e0b")
                caja_ajuste.content = ft.Text(f"ℹ️ {r['mensaje']}", size=13, color="#fbbf24")
                caja_ajuste.visible = True
                page.update()
                return
            caja_ajuste.border = ft.border.all(1, "#2a2b36")
            caja_ajuste.content = ft.Column([
                ft.Text(f"{r['farmaco']} — {r['banda']}", size=14, weight=ft.FontWeight.BOLD, color="#f8fafc"),
                ft.Text(r["instruccion"], size=13, color="#94a3b8"),
                ft.Text(t("referencia_educativa", idioma), size=11, color="#64748b", italic=True),
            ], spacing=2)
            caja_ajuste.visible = True
            page.update()

        panel_ajuste = ft.ExpansionTile(
            title=ft.Text(t("panel_ajuste_renal", idioma), size=14, weight=ft.FontWeight.BOLD, color="#e2e8f0"),
            controls=[ft.Container(
                content=ft.Column([
                    ft.Text(
                        t("farmacos_en_tabla", idioma, lista=', '.join(sorted(AJUSTES_RENALES_COMUNES.keys()))),
                        size=11, color="#64748b", italic=True,
                    ),
                    ft.Row([campo_farmaco_ajuste, campo_crcl_ajuste], spacing=10, wrap=True),
                    ft.FilledButton(t("boton_buscar_ajuste", idioma), on_click=click_ajuste, style=ft.ButtonStyle(bgcolor="#3b82f6", color="#ffffff")),
                    caja_ajuste,
                ], spacing=10),
                padding=12,
            )],
        )

        # --- Interacciones farmacológicas ---
        campo_farmacos_interaccion = ft.TextField(
            label=t("campo_farmacos_lista", idioma), multiline=True, min_lines=3, max_lines=6,
            border_color="#1f212a", bgcolor="#16171d", color="#e2e8f0",
        )
        columna_resultado_interacciones = ft.Column([], spacing=8)

        def click_interacciones(e):
            columna_resultado_interacciones.controls.clear()
            nombres = (campo_farmacos_interaccion.value or "").split("\n")
            resultado = verificar_interacciones(nombres)
            if resultado.get("error"):
                columna_resultado_interacciones.controls.append(ft.Text(t("interacciones_escribe_dos", idioma), color="#ef4444", size=13))
                page.update()
                return

            if not resultado["encontradas"] and not resultado["pares_sin_datos"]:
                columna_resultado_interacciones.controls.append(ft.Text(t("sin_resultados", idioma), size=13, color="#64748b"))
                page.update()
                return

            colores_severidad = {"Mayor": "#ef4444", "Moderada": "#f59e0b", "Menor": "#64748b"}
            for inter in resultado["encontradas"]:
                color = colores_severidad.get(inter["severidad"], "#94a3b8")
                columna_resultado_interacciones.controls.append(
                    ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Text(f"{inter['farmaco_a']} + {inter['farmaco_b']}", size=14, weight=ft.FontWeight.BOLD, color="#f8fafc", expand=True),
                                ft.Container(
                                    content=ft.Text(inter["severidad"], size=11, color="#ffffff"),
                                    bgcolor=color, border_radius=6, padding=ft.Padding(8, 3, 8, 3),
                                ),
                            ]),
                            ft.Text(t("mecanismo", idioma, v=inter['mecanismo']), size=12, color="#94a3b8"),
                            ft.Text(t("efecto", idioma, v=inter['efecto']), size=12, color="#94a3b8"),
                            ft.Text(t("recomendacion", idioma, v=inter['recomendacion']), size=12, color="#cbd5e1"),
                        ], spacing=3),
                        padding=12, bgcolor="#1e1f28", border_radius=8, border=ft.border.all(1, color),
                    )
                )

            if resultado["pares_sin_datos"]:
                columna_resultado_interacciones.controls.append(
                    ft.Text(
                        t("pares_sin_datos_local", idioma, pares="; ".join(f"{a} + {b}" for a, b in resultado["pares_sin_datos"])),
                        size=12, color="#64748b", italic=True,
                    )
                )
                primer_par = resultado["pares_sin_datos"][0]
                caja_ia = ft.Container(visible=False)

                def click_analizar_ia(e, par=primer_par, caja=caja_ia):
                    r = analizar_interaccion_con_ia(par[0], par[1], idioma=idioma)
                    if not r["disponible"]:
                        caja.content = ft.Text(f"❌ {r['diagnostico']}", size=12, color="#ef4444")
                    else:
                        caja.content = ft.Column([
                            ft.Text(
                                t("conocimiento_general_no_verificado", idioma),
                                size=11, color="#93c5fd", italic=True,
                            ),
                            ft.Text(r["texto"], size=12, color="#cbd5e1"),
                        ], spacing=4)
                    caja.bgcolor = "#1e293b"
                    caja.border = ft.border.all(1, "#3b82f6")
                    caja.border_radius = 8
                    caja.padding = 10
                    caja.visible = True
                    page.update()

                columna_resultado_interacciones.controls.append(
                    ft.FilledButton(
                        t("preguntar_ia_sobre", idioma, a=primer_par[0], b=primer_par[1]),
                        on_click=click_analizar_ia,
                        style=ft.ButtonStyle(bgcolor="#1e1b2e", color="#c4b5fd"),
                    )
                )
                columna_resultado_interacciones.controls.append(caja_ia)

            page.update()

        panel_interacciones = ft.ExpansionTile(
            title=ft.Text(t("panel_interacciones", idioma), size=14, weight=ft.FontWeight.BOLD, color="#e2e8f0"),
            controls=[ft.Container(
                content=ft.Column([
                    campo_farmacos_interaccion,
                    ft.FilledButton(t("boton_verificar_interacciones", idioma), on_click=click_interacciones, style=ft.ButtonStyle(bgcolor="#3b82f6", color="#ffffff")),
                    columna_resultado_interacciones,
                ], spacing=10),
                padding=12,
            )],
        )

        chat_view.controls.extend([
            ft.Text(t("calc_titulo_vista", idioma), size=18, weight=ft.FontWeight.BOLD, color="#f8fafc"),
            ft.Text(
                t("calc_disclaimer", idioma),
                size=12, color="#64748b", italic=True,
            ),
            panel_imc, panel_bsa, panel_renal, panel_dosis, panel_ajuste, panel_interacciones,
            ft.TextButton(t("volver_al_chat", idioma), on_click=volver_al_chat_desde_calculadoras),
        ])
        page.update()

    entrada = ft.TextField(
        hint_text="Pregunta algo sobre medicina o tu PDF...",
        expand=True,
        border_color="#1f212a",
        bgcolor="#16171d",
        on_submit=enviar_mensaje
    )

    btn_enviar = ft.IconButton(
        icon=ft.Icons.SEND_ROUNDED,
        icon_color="#3b82f6",
        on_click=enviar_mensaje
    )

    def cerrar_sesion(e):
        usuario_actual_id[0] = None
        usuario_actual_nombre[0] = None
        mostrar_login_screen()

   
    texto_usuario_sidebar = ft.Text("", size=12, color="#64748b", expand=True, overflow=ft.TextOverflow.ELLIPSIS)

    btn_logout = ft.IconButton(icon=ft.Icons.LOGOUT, icon_color="#ef4444", icon_size=16, tooltip=t("cerrar_sesion", idioma_var[0]), on_click=cerrar_sesion)
    texto_titulo_sidebar = ft.Text(t("sidebar_titulo", idioma_var[0]), size=20, weight=ft.FontWeight.BOLD, color="#f8fafc")
    texto_nuevo_chat = ft.Text(t("nuevo_chat", idioma_var[0]), color="#3b82f6")
    texto_cargar_pdf = ft.Text(t("cargar_pdf", idioma_var[0]), color="#e2e8f0")
    dropdown_idioma = ft.Dropdown(
        label=t("idioma_respuesta", idioma_var[0]),
        value=IDIOMA_POR_DEFECTO,
        options=[ft.dropdown.Option(codigo, cfg["nombre"]) for codigo, cfg in IDIOMAS.items()],
        on_change=cambiar_idioma,
        border_color="#1f212a", bgcolor="#16171d", color="#e2e8f0",
    )
    switch_pubmed = ft.Switch(label=t("busqueda_pubmed", idioma_var[0]), value=False, on_change=cambiar_switch)
    dropdown_nivel_evidencia = ft.Dropdown(
        label=t("nivel_evidencia", idioma_var[0]),
        value="todo",
        options=[ft.dropdown.Option(k, t(f"modo_evidencia_{k}", idioma_var[0])) for k in MODOS_EVIDENCIA],
        on_change=cambiar_modo_evidencia,
        border_color="#1f212a", bgcolor="#16171d", color="#e2e8f0",
    )
    switch_factualidad = ft.Switch(label=t("verificar_factualidad", idioma_var[0]), value=True, on_change=cambiar_switch_factualidad)
    texto_seccion_flashcards = ft.Text(t("seccion_flashcards", idioma_var[0]), size=12, color="#64748b", weight=ft.FontWeight.BOLD)
    texto_btn_generar_flashcards = ft.Text(t("generar_de_un_tema", idioma_var[0]), color="#c4b5fd")
    btn_generar_flashcards = ft.FilledButton(
        content=texto_btn_generar_flashcards,
        style=ft.ButtonStyle(bgcolor="#1e1b2e", shape=ft.RoundedRectangleBorder(radius=8)),
        on_click=generar_flashcards_click,
        tooltip=t("tooltip_escribe_tema", idioma_var[0]),
    )
    texto_seccion_examen = ft.Text(t("seccion_examen", idioma_var[0]), size=12, color="#64748b", weight=ft.FontWeight.BOLD)
    texto_btn_generar_examen = ft.Text(t("generar_examen_de_un_tema", idioma_var[0]), color="#c4b5fd")
    btn_generar_examen = ft.FilledButton(
        content=texto_btn_generar_examen,
        style=ft.ButtonStyle(bgcolor="#1e1b2e", shape=ft.RoundedRectangleBorder(radius=8)),
        on_click=generar_examen_click,
        tooltip=t("tooltip_escribe_tema", idioma_var[0]),
    )
    texto_btn_progreso = ft.Text(t("mi_progreso", idioma_var[0]), color="#c4b5fd")
    texto_btn_calculadoras = ft.Text(t("calculadoras_clinicas", idioma_var[0]), color="#c4b5fd")
    texto_historial_titulo = ft.Text(t("historial_consultas", idioma_var[0]), size=12, color="#64748b", weight=ft.FontWeight.BOLD)

    def aplicar_idioma_ui(idioma):
        """
        Retraduce TODO lo que está siempre visible (sidebar + input del
        chat) cuando cambia el idioma — antes solo se traducían las
        respuestas de la IA y las vistas que se reconstruyen (calculadoras,
        examen, etc.), pero el sidebar se construye una sola vez, así que
        necesita que le actualicemos cada control a mano.
        """
        btn_logout.tooltip = t("cerrar_sesion", idioma)
        texto_titulo_sidebar.value = t("sidebar_titulo", idioma)
        texto_nuevo_chat.value = t("nuevo_chat", idioma)
        texto_cargar_pdf.value = t("cargar_pdf", idioma)
        dropdown_idioma.label = t("idioma_respuesta", idioma)
        switch_pubmed.label = t("busqueda_pubmed", idioma)
        dropdown_nivel_evidencia.label = t("nivel_evidencia", idioma)
        dropdown_nivel_evidencia.options = [
            ft.dropdown.Option(k, t(f"modo_evidencia_{k}", idioma)) for k in MODOS_EVIDENCIA
        ]
        switch_factualidad.label = t("verificar_factualidad", idioma)
        texto_seccion_flashcards.value = t("seccion_flashcards", idioma)
        texto_btn_generar_flashcards.value = t("generar_de_un_tema", idioma)
        btn_generar_flashcards.tooltip = t("tooltip_escribe_tema", idioma)
        texto_seccion_examen.value = t("seccion_examen", idioma)
        texto_btn_generar_examen.value = t("generar_examen_de_un_tema", idioma)
        btn_generar_examen.tooltip = t("tooltip_escribe_tema", idioma)
        texto_btn_progreso.value = t("mi_progreso", idioma)
        texto_btn_calculadoras.value = t("calculadoras_clinicas", idioma)
        texto_historial_titulo.value = t("historial_consultas", idioma)
        entrada.hint_text = t("entrada_hint", idioma)
        titulo_modal_borrar.value = t("confirmar_eliminar_titulo", idioma)
        texto_modal_borrar.value = t("confirmar_eliminar_texto", idioma)
        btn_cancelar_borrar.text = t("cancelar", idioma)
        btn_confirmar_borrar.text = t("eliminar", idioma)
        actualizar_contador_flashcards()
        page.update()

    sidebar = ft.Container(
        content=ft.Column([
            texto_titulo_sidebar,
            ft.Row(
                [texto_usuario_sidebar, btn_logout],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            ft.Divider(color="#1f212a"),
            ft.FilledButton(
                content=ft.Row(
                    [ft.Icon(ft.Icons.ADD, color="#3b82f6"), texto_nuevo_chat],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                style=ft.ButtonStyle(bgcolor="#1f212a", shape=ft.RoundedRectangleBorder(radius=8)),
                on_click=nuevo_chat_click,
            ),
            ft.Divider(color="#1f212a"),
            ft.FilledButton(
                content=ft.Row(
                    [ft.Icon(ft.Icons.UPLOAD_FILE, color="#e2e8f0"), texto_cargar_pdf],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                style=ft.ButtonStyle(bgcolor="#1e293b", shape=ft.RoundedRectangleBorder(radius=8)),
                on_click=abrir_buscador_archivos,  
            ),
            txt_estado_pdf,
            ft.Divider(color="#1f212a"),
            dropdown_idioma,
            ft.Divider(color="#1f212a"),
            switch_pubmed,
            dropdown_nivel_evidencia,
            switch_factualidad,
            ft.Divider(color="#1f212a"),
            texto_seccion_flashcards,
            btn_generar_flashcards,
            txt_estado_flashcards,
            ft.FilledButton(
                content=txt_contador_flashcards,
                style=ft.ButtonStyle(bgcolor="#1e1b2e", shape=ft.RoundedRectangleBorder(radius=8)),
                on_click=iniciar_repaso,
            ),
            ft.Divider(color="#1f212a"),
            texto_seccion_examen,
            btn_generar_examen,
            txt_estado_examen,
            ft.Divider(color="#1f212a"),
            ft.FilledButton(
                content=texto_btn_progreso,
                style=ft.ButtonStyle(bgcolor="#1e1b2e", shape=ft.RoundedRectangleBorder(radius=8)),
                on_click=mostrar_vista_progreso,
            ),
            ft.Divider(color="#1f212a"),
            ft.FilledButton(
                content=texto_btn_calculadoras,
                style=ft.ButtonStyle(bgcolor="#1e1b2e", shape=ft.RoundedRectangleBorder(radius=8)),
                on_click=mostrar_vista_calculadoras,
            ),
            ft.Divider(color="#1f212a"),
            texto_historial_titulo,
            ft.Container(content=lista_historial_ui, expand=True),
            ft.Text("Medicine Study AI v3.1", size=10, color="#475569")
        ], scroll=ft.ScrollMode.AUTO),
        width=260,
        bgcolor="#111217",
        padding=15,
        border=ft.BorderSide(1, "#1f212a"),
        border_radius=12
    )

    def mostrar_app_principal():
        texto_usuario_sidebar.value = f"👤 {usuario_actual_nombre[0]}"
        page.controls.clear()
        page.add(
            ft.Row([
                sidebar,
                ft.VerticalDivider(width=1, color="#1f212a"),
                ft.Column([
                    chat_view,
                    ft.Row([entrada, btn_enviar], spacing=10)
                ], expand=True)
            ], expand=True)
        )
        page.update()
        # Cada paso posterior va envuelto por separado: si uno falla, los
        # demás igual se ejecutan y queda evidencia en el log del servidor
        # en vez de dejar la app a medio cargar sin ninguna pista.
        try:
            actualizar_sidebar_historial()
        except Exception as ex:
            print(f"[mostrar_app_principal] Error en actualizar_sidebar_historial: {ex}")
        try:
            mostrar_pantalla_bienvenida()
        except Exception as ex:
            print(f"[mostrar_app_principal] Error en mostrar_pantalla_bienvenida: {ex}")
            chat_view.controls.clear()
            chat_view.controls.append(ft.Text(f"❌ Error cargando la pantalla principal: {ex}", color="#ef4444"))
            page.update()
        try:
            actualizar_contador_flashcards()
        except Exception as ex:
            print(f"[mostrar_app_principal] Error en actualizar_contador_flashcards: {ex}")

    
    modo_registro = [False]

    campo_usuario_login = ft.TextField(
        label="Usuario", width=300, border_color="#1f212a", bgcolor="#16171d", autofocus=True
    )
    campo_password_login = ft.TextField(
        label="Contraseña", width=300, border_color="#1f212a", bgcolor="#16171d",
        password=True, can_reveal_password=True
    )
    texto_error_login = ft.Text("", color="#ef4444", size=12)
    titulo_login = ft.Text("Iniciar sesión", size=22, weight=ft.FontWeight.BOLD, color="#f8fafc")
    texto_toggle_login = ft.Text(
        "¿No tienes cuenta? Regístrate", color="#3b82f6", size=13
    )

    def procesar_login(e):
        usuario = (campo_usuario_login.value or "").strip()
        password = campo_password_login.value or ""

        if not usuario or not password:
            texto_error_login.value = "Completa usuario y contraseña."
            page.update()
            return
        if len(usuario) < 3:
            texto_error_login.value = "El usuario debe tener al menos 3 caracteres."
            page.update()
            return
        if len(password) < 4:
            texto_error_login.value = "La contraseña debe tener al menos 4 caracteres."
            page.update()
            return

        if modo_registro[0]:
            nuevo_id, error = crear_usuario(usuario, password)
            if error:
                texto_error_login.value = error
                page.update()
                return
            usuario_actual_id[0] = nuevo_id
            usuario_actual_nombre[0] = usuario
        else:
            fila = obtener_usuario_por_nombre(usuario)
            if not fila or not verificar_password(password, fila[1]):
                texto_error_login.value = "Usuario o contraseña incorrectos."
                page.update()
                return
            usuario_actual_id[0] = fila[0]
            usuario_actual_nombre[0] = usuario

        campo_usuario_login.value = ""
        campo_password_login.value = ""
        texto_error_login.value = ""
        mostrar_app_principal()

    def alternar_modo_login(e):
        modo_registro[0] = not modo_registro[0]
        texto_error_login.value = ""
        if modo_registro[0]:
            titulo_login.value = "Crear cuenta"
            btn_login.text = "Crear cuenta"
            texto_toggle_login.value = "¿Ya tienes cuenta? Inicia sesión"
        else:
            titulo_login.value = "Iniciar sesión"
            btn_login.text = "Iniciar sesión"
            texto_toggle_login.value = "¿No tienes cuenta? Regístrate"
        page.update()

    btn_login = ft.FilledButton(
        text="Iniciar sesión",
        width=300,
        style=ft.ButtonStyle(bgcolor="#3b82f6", shape=ft.RoundedRectangleBorder(radius=8)),
        on_click=procesar_login,
    )
    campo_password_login.on_submit = procesar_login

    def mostrar_login_screen():
        page.controls.clear()
        page.add(
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text("✨ Medicine Study AI", size=26, weight=ft.FontWeight.BOLD, color="#f8fafc"),
                        ft.Container(height=10),
                        titulo_login,
                        campo_usuario_login,
                        campo_password_login,
                        texto_error_login,
                        btn_login,
                        ft.TextButton(
                            content=texto_toggle_login,
                            on_click=alternar_modo_login,
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=12,
                ),
                alignment=ft.alignment.center,
                expand=True,
            )
        )
        page.update()

    mostrar_login_screen()