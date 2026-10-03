"""Presentación Qt de fuentes y resultados, compatible con imports existentes."""
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout

from citas_evidencia import formatear_cita_vancouver
from pubmed_search import clasificar_evidencia
from traducciones import t_categoria


def agregar_papers_a_chat(chat_view, page, papers, n_nuevos, total_unicos, idioma="es"):
    if not papers:
        return
    panel = QFrame()
    layout = QVBoxLayout(panel)
    conocidos = len(papers) - n_nuevos
    layout.addWidget(QLabel(
        f"📚 Papers de PubMed — {n_nuevos} nuevos, {conocidos} ya conocidos · "
        f"{total_unicos} únicos"
    ))
    for indice, paper in enumerate(papers, 1):
        layout.addWidget(QLabel(f"[{indice}] {paper.get('titulo', 'Sin título')}"))
        layout.addWidget(QLabel(formatear_cita_vancouver(paper)))
        layout.addWidget(QLabel(t_categoria(
            clasificar_evidencia(paper.get("tipos_publicacion", [])), idioma
        )))
    chat_view.addWidget(panel)


def construir_panel_fuentes(fuentes: list, idioma="es"):
    panel = QFrame()
    layout = QVBoxLayout(panel)
    layout.addWidget(QLabel(f"📚 Fuentes de esta respuesta ({len(fuentes)})"))
    for fuente in fuentes:
        layout.addWidget(QLabel(str(fuente)))
    return panel


def anexar_badge_factualidad(chat_view, page, fact: dict):
    if isinstance(fact, dict) and isinstance(fact.get("score"), (int, float)):
        chat_view.addWidget(QLabel(
            f"🎯 Factualidad estimada: {fact['score']:.0f}/100\n"
            f"{fact.get('resumen', '')}"
        ))
