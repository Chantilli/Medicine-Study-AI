"""Layout y comportamiento responsive de la aplicación Flet."""
import flet as ft


def configurar_shell_responsive(
    page: ft.Page,
    sidebar: ft.Control,
    contenido_principal: ft.Control,
    layout_principal: ft.Row,
    ancho_movil: int = 800,
):
    """Conecta menú móvil, sidebar y redimensionamiento en un único lugar."""
    sidebar_abierto = [True]

    def alternar_sidebar(e=None):
        sidebar_abierto[0] = not sidebar_abierto[0]
        sidebar.visible = sidebar_abierto[0]
        page.update()

    def al_redimensionar(e=None):
        es_movil = bool(page.width and page.width < ancho_movil)
        if es_movil:
            sidebar_abierto[0] = False
            sidebar.visible = False
        else:
            sidebar_abierto[0] = True
            sidebar.visible = True
        page.update()

    boton_menu = ft.IconButton(
        icon=ft.Icons.MENU,
        icon_color="#3b82f6",
        tooltip="Mostrar u ocultar menú",
        on_click=alternar_sidebar,
    )
    page.on_resized = al_redimensionar
    layout_principal.controls = [
        sidebar,
        ft.VerticalDivider(width=1, color="#1f212a"),
        contenido_principal,
    ]
    return boton_menu, al_redimensionar
