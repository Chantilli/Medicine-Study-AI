"""Componentes Qt reutilizables y compatibles con imports históricos."""
from PySide6.QtWidgets import QFrame, QLabel, QProgressBar, QPushButton, QVBoxLayout


def tarjeta_aviso(contenido, tipo="info"):
    widget = QFrame()
    widget.setProperty("tipo", tipo)
    layout = QVBoxLayout(widget)
    layout.addWidget(contenido if hasattr(contenido, "setText") else QLabel(str(contenido)))
    return widget


def indicador_carga(texto):
    widget = QFrame()
    layout = QVBoxLayout(widget)
    layout.addWidget(QProgressBar())
    layout.addWidget(QLabel(texto))
    return widget


def indicador_streaming(texto):
    return indicador_carga(texto)


def chip_sugerencia(texto, on_click):
    boton = QPushButton(texto)
    boton.clicked.connect(on_click)
    return boton


def tarjeta_funcion(icono, titulo, descripcion):
    widget = QFrame()
    layout = QVBoxLayout(widget)
    layout.addWidget(QLabel(str(icono)))
    layout.addWidget(QLabel(titulo))
    layout.addWidget(QLabel(descripcion))
    return widget
