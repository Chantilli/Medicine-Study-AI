"""Componentes visuales pequeños y reutilizables para la interfaz Flet."""
import flet as ft

PALETA = {
    "page": "#0b1120",
    "surface": "#111c2e",
    "surface_alt": "#16243a",
    "surface_soft": "#1b2d46",
    "border": "#263b58",
    "text": "#f8fafc",
    "muted": "#94a3b8",
    "primary": "#38bdf8",
    "primary_dark": "#075985",
    "teal": "#2dd4bf",
}


def tarjeta_aviso(contenido, tipo="info"):
    estilos = {
        "error": ("#351820", "#fb7185", "#fecdd3"),
        "warning": ("#332716", "#fbbf24", "#fde68a"),
        "info": ("#102d45", "#38bdf8", "#bae6fd"),
    }
    bg, borde, color_texto = estilos.get(tipo, estilos["info"])
    hijo = contenido if isinstance(contenido, ft.Control) else ft.Text(
        contenido, color=color_texto, size=12
    )
    return ft.Container(
        content=hijo,
        bgcolor=bg,
        border=ft.border.all(1, borde),
        border_radius=12,
        padding=ft.Padding(14, 12, 14, 12),
    )


def indicador_carga(texto):
    return ft.Row(
        [
            ft.ProgressRing(width=14, height=14, stroke_width=2, color=PALETA["primary"]),
            ft.Text(texto, color=PALETA["muted"], italic=True, size=12),
        ],
        spacing=8,
    )


def indicador_streaming(texto):
    """Indicador visible mientras la respuesta llega por streaming."""
    return ft.Row(
        [
            ft.ProgressRing(width=14, height=14, stroke_width=2, color=PALETA["teal"]),
            ft.Text(texto, color="#bae6fd", italic=True, size=12),
        ],
        spacing=8,
    )


def chip_sugerencia(texto, on_click):
    return ft.Container(
        content=ft.Text(texto, size=12, color="#dbeafe"),
        bgcolor=PALETA["surface_alt"],
        border=ft.border.all(1, PALETA["border"]),
        border_radius=20,
        padding=ft.Padding(14, 9, 14, 9),
        on_click=on_click,
        ink=True,
        tooltip="Usar esta sugerencia",
    )


def tarjeta_funcion(icono, titulo, descripcion):
    return ft.Container(
        content=ft.Column(
            [
                ft.Container(
                    content=ft.Icon(icono, size=22, color=PALETA["primary"]),
                    bgcolor="#12304a",
                    border_radius=10,
                    padding=8,
                ),
                ft.Text(titulo, size=13, weight=ft.FontWeight.BOLD, color=PALETA["text"]),
                ft.Text(descripcion, size=11, color=PALETA["muted"]),
            ],
            spacing=8,
        ),
        bgcolor=PALETA["surface"],
        border=ft.border.all(1, PALETA["border"]),
        border_radius=16,
        padding=16,
        width=228,
    )


def bloque_seccion(controles, *, bgcolor="#15161c", padding=10, expand=False):
    """Agrupa controles relacionados en un bloque visual reutilizable."""
    return ft.Container(
        content=ft.Column(controles, spacing=8),
        bgcolor=bgcolor,
        border=ft.border.all(1, PALETA["border"]),
        border_radius=14,
        padding=padding,
        expand=expand,
    )
