"""
Controles de Flet reutilizables para mostrar papers, el panel de fuentes
con trazabilidad, y el badge de factualidad. Son funciones puras de UI:
reciben datos ya calculados (papers, fuentes, resultado del juez) y
arman los controles — no hacen búsquedas ni llamadas a Groq.
"""
import flet as ft

from pubmed_search import clasificar_evidencia
from citas_evidencia import formatear_cita_vancouver

def agregar_papers_a_chat(chat_view, page, papers, n_nuevos, total_unicos):
    """
    Añade al chat la tarjeta visual de papers con enlaces clicables a DOI
    y PubMed, y el nivel de evidencia de cada uno. Las tarjetas son
    efímeras (solo UI): el historial persistido guarda únicamente el
    texto numerado que ve el modelo (formatear_contexto_papers).
    """
    if not papers:
        return

    n_conocidos = len(papers) - n_nuevos
    resumen_conteo = f"{n_nuevos} nuevos"
    if n_conocidos > 0:
        resumen_conteo += f" · {n_conocidos} ya conocidos"

    controles_tarjeta = [
        ft.Text(
            f"📚 Papers de PubMed — {resumen_conteo} · {total_unicos} únicos en tu base",
            size=13, weight=ft.FontWeight.BOLD, color="#f8fafc"
        ),
        ft.Divider(height=8, color="#2a2b36"),
    ]

    for i, p in enumerate(papers, start=1):
        score = p.get("score")
        badge = f"  ·  {score * 100:.0f}% relevante" if score is not None else ""
        if p.get("fuente_bd"):
            badge += f"  ·  {p['fuente_bd']}"
        controles_tarjeta.append(
            ft.Row([
                ft.Container(
                    content=ft.Text(f"[{i}]", color="#f59e0b", weight=ft.FontWeight.BOLD, size=13),
                    width=28,
                ),
                ft.Text(f"{p.get('titulo', 'Sin título')}{badge}", color="#e2e8f0", size=13, expand=True),
            ], spacing=4)
        )
        controles_tarjeta.append(
            ft.Text(formatear_cita_vancouver(p), color="#94a3b8", size=12, italic=True)
        )
        controles_tarjeta.append(
            ft.Container(
                content=ft.Text(
                    clasificar_evidencia(p.get("tipos_publicacion", [])),
                    color="#a78bfa", size=11, weight=ft.FontWeight.W_600,
                ),
                bgcolor="#2a2140", border_radius=4, padding=ft.Padding(6, 2, 6, 2),
            )
        )
        
        enlaces = []
        if p.get("doi"):
            doi_url = f"https://doi.org/{p['doi']}"
            enlaces.append(ft.TextButton(
                content=ft.Text("🔗 DOI", color="#3b82f6", size=12, weight=ft.FontWeight.W_600),
                on_click=lambda e, u=doi_url: page.launch_url(u),
            ))
        if p.get("pmid"):
            pmid_url = f"https://pubmed.ncbi.nlm.nih.gov/{p['pmid']}/"
            enlaces.append(ft.TextButton(
                content=ft.Text("PubMed", color="#3b82f6", size=12, weight=ft.FontWeight.W_600),
                on_click=lambda e, u=pmid_url: page.launch_url(u),
            ))
        if enlaces:
            controles_tarjeta.append(ft.Row(enlaces, spacing=16))
        controles_tarjeta.append(ft.Divider(height=8, color="#1f212a"))

    chat_view.controls.append(
        ft.Container(
            content=ft.Column(controles_tarjeta, spacing=4),
            bgcolor="#1e1f28",
            border=ft.border.all(1, "#2a2b36"),
            border_radius=10,
            padding=12,
        )
    )
    if hasattr(chat_view, "scroll_to"):
        chat_view.scroll_to(key="end")
    page.update()

def construir_panel_fuentes(fuentes: list):
    """
    Panel plegable "📚 Fuentes de esta respuesta (N)" con trazabilidad:
    cada fuente muestra si el modelo la citó explícitamente ([n]/[Fn]) o
    si solo estaba disponible como contexto, para que el estudiante pueda
    verificar de dónde salió cada afirmación.
    """
    if not fuentes:
        return ft.Container()

    filas = []
    for f in fuentes:
        if f.get("tipo") == "paper":
            etiqueta = "✓ citado" if f.get("citado") else "en contexto, no citado"
            color_etiqueta = "#22c55e" if f.get("citado") else "#64748b"
            identificadores = []
            if f.get("pmid"):
                identificadores.append(f"PMID: {f['pmid']}")
            if f.get("doi"):
                identificadores.append(f"DOI: {f['doi']}")
            filas.append(
                ft.Container(
                    content=ft.Column([
                        ft.Text(f"[{f['indice']}] {f.get('titulo', '')}", size=12, weight=ft.FontWeight.BOLD, color="#e2e8f0"),
                        ft.Text(f"{f.get('nivel_evidencia', '')} · {' | '.join(identificadores)}", size=11, color="#94a3b8"),
                        ft.Text(etiqueta, size=11, color=color_etiqueta, italic=True),
                    ], spacing=2),
                    padding=ft.Padding(0, 4, 0, 4),
                )
            )
        elif f.get("tipo") == "fragmento_pdf":
            etiqueta = "✓ citado" if f.get("citado") else "en contexto, no citado"
            color_etiqueta = "#22c55e" if f.get("citado") else "#64748b"
            ocr_tag = " · vía OCR" if f.get("via_ocr") else ""
            filas.append(
                ft.Container(
                    content=ft.Column([
                        ft.Text(f"[F{f['indice']}] {f.get('fuente', '')}{ocr_tag}", size=12, weight=ft.FontWeight.BOLD, color="#e2e8f0"),
                        ft.Text(f"similitud: {f.get('similitud', 0):.2f}", size=11, color="#94a3b8"),
                        ft.Text(etiqueta, size=11, color=color_etiqueta, italic=True),
                        ft.Text(f.get("snippet", ""), size=11, color="#64748b", italic=True),
                    ], spacing=2),
                    padding=ft.Padding(0, 4, 0, 4),
                )
            )

    return ft.ExpansionTile(
        title=ft.Text(f"📚 Fuentes de esta respuesta ({len(fuentes)})", size=13, weight=ft.FontWeight.BOLD, color="#e2e8f0"),
        subtitle=ft.Text("Papers y fragmentos usados para responder — toca para ver el detalle", size=11, color="#64748b"),
        controls=[ft.Container(content=ft.Column(filas, spacing=2), padding=10, bgcolor="#1e1f28", border_radius=8)],
        initially_expanded=False,
    )

def anexar_badge_factualidad(chat_view, page, fact: dict):
    """
    Muestra el resultado de evaluar_factualidad() como una tarjeta con
    color según el score (verde ≥85, ámbar ≥50, rojo <50) y el detalle
    de cada afirmación evaluada.
    """
    if not fact or not isinstance(fact, dict):
        return
    score = fact.get("score")
    if not isinstance(score, (int, float)):
        return

    if score >= 85:
        color = "#22c55e"
    elif score >= 50:
        color = "#f59e0b"
    else:
        color = "#ef4444"

    controles = [
        ft.Text(f"🎯 Factualidad estimada: {score:.0f}/100", size=13, weight=ft.FontWeight.BOLD, color=color),
    ]
    if fact.get("resumen"):
        controles.append(ft.Text(fact["resumen"], size=12, color="#94a3b8"))

    iconos_estado = {"Soportada": "✅", "No soportada": "⚠️", "No verificable": "❔"}
    for af in (fact.get("afirmaciones") or [])[:8]:
        icono = iconos_estado.get(af.get("estado", ""), "•")
        fuente = af.get("fuente") or ""
        texto_af = (af.get("afirmacion", "") or "")[:110]
        controles.append(
            ft.Text(f"{icono} {texto_af}" + (f"  —  {fuente}" if fuente else ""), size=11, color="#cbd5e1")
        )

    chat_view.controls.append(
        ft.Container(
            content=ft.Column(controles, spacing=3),
            bgcolor="#1e1f28",
            border=ft.border.all(1, color),
            border_radius=8,
            padding=10,
        )
    )
    page.update()

