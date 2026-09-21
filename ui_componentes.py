"""Componentes visuales pequeños y reutilizables para la interfaz Flet."""
import flet as ft


def tarjeta_aviso(contenido, tipo="info"):
    estilos = {
        "error": ("#3b1a1a", "#ef4444", "#fca5a5"),
        "warning": ("#3a2f0f", "#f59e0b", "#fde68a"),
        "info": ("#1e293b", "#3b82f6", "#93c5fd"),
    }
    bg, borde, color_texto = estilos.get(tipo, estilos["info"])
    hijo = contenido if isinstance(contenido, ft.Control) else ft.Text(
        contenido, color=color_texto, size=12
    )
    return ft.Container(
        content=hijo,
        bgcolor=bg,
        border=ft.border.all(1, borde),
        border_radius=8,
        padding=10,
    )


def indicador_carga(texto):
    return ft.Row(
        [
            ft.ProgressRing(width=13, height=13, stroke_width=2, color="#3b82f6"),
            ft.Text(texto, color="#64748b", italic=True, size=12),
        ],
        spacing=8,
    )


def indicador_streaming(texto):
    """Indicador visible mientras la respuesta llega por streaming."""
    return ft.Row(
        [
            ft.ProgressRing(width=14, height=14, stroke_width=2, color="#60a5fa"),
            ft.Text(texto, color="#93c5fd", italic=True, size=12),
        ],
        spacing=8,
    )


def chip_sugerencia(texto, on_click):
    return ft.Container(
        content=ft.Text(texto, size=12, color="#cbd5e1"),
        bgcolor="#1a1b23",
        border=ft.border.all(1, "#2a2b36"),
        border_radius=20,
        padding=ft.Padding(14, 8, 14, 8),
        on_click=on_click,
        ink=True,
    )


def tarjeta_funcion(icono, titulo, descripcion):
    return ft.Container(
        content=ft.Column(
            [
                ft.Icon(icono, size=22, color="#60a5fa"),
                ft.Text(titulo, size=13, weight=ft.FontWeight.BOLD, color="#f1f5f9"),
                ft.Text(descripcion, size=11, color="#64748b"),
            ],
            spacing=4,
        ),
        bgcolor="#15161c",
        border=ft.border.all(1, "#22232d"),
        border_radius=12,
        padding=14,
        width=220,
    )
