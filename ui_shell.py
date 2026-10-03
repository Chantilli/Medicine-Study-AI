"""Compatibilidad para el helper histórico de layout."""
from PySide6.QtWidgets import QHBoxLayout, QPushButton


def configurar_shell_responsive(parent, sidebar, contenido_principal, layout_principal, ancho_movil=800):
    """Configura un layout Qt y devuelve un botón para alternar el sidebar."""
    layout_principal.addWidget(sidebar)
    layout_principal.addWidget(contenido_principal)
    boton = QPushButton("☰")
    boton.clicked.connect(lambda: sidebar.setVisible(not sidebar.isVisible()))
    return boton, lambda: None
