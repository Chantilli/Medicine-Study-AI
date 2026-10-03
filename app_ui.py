"""Interfaz de escritorio PySide6 para Medicine Study AI.

La ventana solo coordina eventos y presenta resultados; la lógica clínica,
RAG, búsquedas y persistencia permanecen en sus módulos de backend.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal, Slot, Qt
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFileDialog, QFormLayout, QHBoxLayout,
    QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMessageBox,
    QPushButton, QPlainTextEdit, QSpinBox, QStackedWidget, QTabWidget,
    QVBoxLayout, QWidget,
)

from calculadoras_clinicas import calcular_imc, calcular_superficie_corporal
from citas_evidencia import formatear_contexto_papers
from clasificador_riesgo_clinico import (
    clasificar_consulta, mensaje_emergencia_medica,
    mensaje_emergencia_salud_mental,
)
from config import (
    IDIOMA_POR_DEFECTO, MAX_TOKENS_RESPUESTA, MODELO_CHAT, UPLOAD_DIR,
    construir_system_prompt, client,
)
from database import (
    crear_usuario, guardar_chat_db, obtener_usuario_por_nombre,
    verificar_password,
)
from ocr_pdf import extraer_texto_pdf_con_ocr
from pubmed_search import buscar_pubmed_estructurado
from rag_embeddings import guardar_fragmentos_pdf


class Worker(QObject):
    terminado = Signal(object)
    error = Signal(str)

    def __init__(self, funcion, *args, **kwargs):
        super().__init__()
        self.funcion, self.args, self.kwargs = funcion, args, kwargs

    @Slot()
    def ejecutar(self):
        try:
            self.terminado.emit(self.funcion(*self.args, **self.kwargs))
        except Exception as exc:
            self.error.emit(str(exc))


def ejecutar_en_hilo(parent, funcion, callback, *args, **kwargs):
    """Ejecuta red/IO fuera del hilo de Qt y conserva referencias hasta terminar."""
    thread = QThread(parent)
    worker = Worker(funcion, *args, **kwargs)
    worker.moveToThread(thread)
    thread.started.connect(worker.ejecutar)
    worker.terminado.connect(callback)
    worker.error.connect(lambda mensaje: callback({"error": mensaje}))
    worker.terminado.connect(thread.quit)
    worker.error.connect(thread.quit)
    thread.finished.connect(worker.deleteLater)
    thread.finished.connect(thread.deleteLater)
    parent._workers = getattr(parent, "_workers", [])
    parent._workers.append((thread, worker))
    thread.finished.connect(
        lambda: parent._workers.remove((thread, worker))
        if (thread, worker) in parent._workers else None
    )
    thread.start()


class LoginWidget(QWidget):
    autenticado = Signal(int, str)

    def __init__(self):
        super().__init__()
        self.usuario = QLineEdit()
        self.usuario.setPlaceholderText("Usuario")
        self.password = QLineEdit()
        self.password.setPlaceholderText("Contraseña")
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        entrar = QPushButton("Iniciar sesión")
        registrar = QPushButton("Crear cuenta")
        entrar.clicked.connect(self.iniciar_sesion)
        registrar.clicked.connect(self.registrar)
        self.estado = QLabel()
        self.estado.setWordWrap(True)
        layout = QFormLayout(self)
        layout.addRow("Usuario", self.usuario)
        layout.addRow("Contraseña", self.password)
        botones = QHBoxLayout()
        botones.addWidget(entrar)
        botones.addWidget(registrar)
        layout.addRow(botones)
        layout.addRow(self.estado)

    def credenciales(self):
        return self.usuario.text().strip(), self.password.text()

    def iniciar_sesion(self):
        usuario, password = self.credenciales()
        fila = obtener_usuario_por_nombre(usuario) if usuario else None
        if fila and verificar_password(password, fila[1]):
            self.autenticado.emit(fila[0], usuario)
        else:
            self.estado.setText("Usuario o contraseña incorrectos.")

    def registrar(self):
        usuario, password = self.credenciales()
        if len(usuario) < 3 or len(password) < 6:
            self.estado.setText("Usa un usuario de 3+ caracteres y una contraseña de 6+.")
            return
        usuario_id, error = crear_usuario(usuario, password)
        if error:
            self.estado.setText(error)
        else:
            self.autenticado.emit(usuario_id, usuario)


class ChatWidget(QWidget):
    cerrar_sesion = Signal()

    def __init__(self, usuario_id, nombre):
        super().__init__()
        self.usuario_id, self.nombre = usuario_id, nombre
        self.chat_id = str(time.time())
        self.historial = [construir_system_prompt(IDIOMA_POR_DEFECTO)]
        self.papers = []
        self._construir_ui()

    def _construir_ui(self):
        self.salir = QPushButton("Cerrar sesión")
        self.salir.clicked.connect(self.cerrar_sesion)
        self.usuario_label = QLabel(f"Sesión: {self.nombre}")
        cabecera = QHBoxLayout()
        cabecera.addWidget(self.usuario_label)
        cabecera.addStretch()
        cabecera.addWidget(self.salir)

        self.mensajes = QPlainTextEdit()
        self.mensajes.setReadOnly(True)
        self.entrada = QPlainTextEdit()
        self.entrada.setPlaceholderText("Escribe una pregunta de estudio médico…")
        self.entrada.setMaximumHeight(90)
        self.enviar = QPushButton("Enviar")
        self.evidencia = QCheckBox("Buscar evidencia en PubMed")
        self.evidencia.setChecked(True)
        self.subir = QPushButton("Adjuntar PDF")
        self.subir.clicked.connect(self.adjuntar_pdf)
        self.enviar.clicked.connect(self.enviar_pregunta)
        acciones = QHBoxLayout()
        acciones.addWidget(self.evidencia)
        acciones.addWidget(self.subir)
        acciones.addStretch()
        acciones.addWidget(self.enviar)

        self.calculadoras = self._crear_calculadoras()
        tabs = QTabWidget()
        chat = QWidget()
        chat_layout = QVBoxLayout(chat)
        chat_layout.addLayout(cabecera)
        chat_layout.addWidget(self.mensajes)
        chat_layout.addWidget(self.entrada)
        chat_layout.addLayout(acciones)
        tabs.addTab(chat, "Chat")
        tabs.addTab(self.calculadoras, "Calculadoras")
        layout = QVBoxLayout(self)
        layout.addWidget(tabs)
        self._escribir("Medicine Study AI listo. Las respuestas son educativas y no sustituyen valoración clínica.")

    def _escribir(self, texto):
        self.mensajes.appendPlainText(texto)

    def _crear_calculadoras(self):
        widget = QWidget()
        form = QFormLayout(widget)
        peso = QLineEdit()
        altura = QLineEdit()
        resultado = QLabel()
        calcular = QPushButton("Calcular IMC y superficie corporal")
        def ejecutar():
            imc = calcular_imc(peso.text(), altura.text())
            bsa = calcular_superficie_corporal(peso.text(), altura.text())
            if "error" in imc:
                resultado.setText(imc["error"])
            else:
                resultado.setText(
                    f"IMC: {imc['valor']} ({imc['categoria']})\n"
                    f"Superficie corporal: {bsa.get('valor', bsa.get('error'))} m²"
                )
        calcular.clicked.connect(ejecutar)
        form.addRow("Peso (kg)", peso)
        form.addRow("Altura (cm)", altura)
        form.addRow(calcular)
        form.addRow(resultado)
        return widget

    def adjuntar_pdf(self):
        ruta, _ = QFileDialog.getOpenFileName(self, "Seleccionar PDF", str(UPLOAD_DIR), "PDF (*.pdf)")
        if not ruta:
            return
        destino = Path(UPLOAD_DIR) / Path(ruta).name
        if Path(ruta).resolve() != destino.resolve():
            destino.write_bytes(Path(ruta).read_bytes())
        self._escribir(f"PDF adjunto: {destino.name}. Se indexará para consultas posteriores.")
        ejecutar_en_hilo(self, self._indexar_pdf, self._pdf_indexado, self.usuario_id, str(destino))

    @staticmethod
    def _indexar_pdf(usuario_id, ruta):
        extraido = extraer_texto_pdf_con_ocr(ruta)
        guardar_fragmentos_pdf(
            usuario_id, Path(ruta).name, extraido["texto"],
            tipo_texto="ocr" if extraido["via_ocr"] else "normal",
        )
        return {"nombre": Path(ruta).name, "paginas": extraido["n_paginas"]}

    def _pdf_indexado(self, resultado):
        if "error" in resultado:
            self._escribir(f"Error al indexar PDF: {resultado['error']}")
        else:
            self._escribir(f"PDF indexado: {resultado['nombre']} ({resultado['paginas']} páginas).")

    def enviar_pregunta(self):
        pregunta = self.entrada.toPlainText().strip()
        if not pregunta:
            return
        self.entrada.clear()
        self.enviar.setEnabled(False)
        self._escribir(f"\nTú: {pregunta}")
        riesgo = clasificar_consulta(pregunta)
        if riesgo["categoria"] == "emergencia" and riesgo["subtipo"] == "medica":
            self._escribir(mensaje_emergencia_medica(IDIOMA_POR_DEFECTO))
            self.enviar.setEnabled(True)
            return
        if riesgo["categoria"] == "emergencia" and riesgo["subtipo"] == "salud_mental":
            self._escribir(mensaje_emergencia_salud_mental(IDIOMA_POR_DEFECTO))
            self.enviar.setEnabled(True)
            return
        ejecutar_en_hilo(self, self._responder, self._respuesta_recibida, pregunta)

    def _responder(self, pregunta):
        papers = []
        if self.evidencia.isChecked():
            papers, *_ = buscar_pubmed_estructurado(pregunta, self.usuario_id)
        contexto = formatear_contexto_papers(papers) if papers else ""
        mensajes = list(self.historial)
        mensajes.append({"role": "user", "content": f"{pregunta}\n\n{contexto}"})
        if client is None:
            return {"error": "GROQ_API_KEY no está configurada; no se puede generar una respuesta."}
        respuesta = client.chat.completions.create(
            model=MODELO_CHAT, messages=mensajes,
            max_tokens=MAX_TOKENS_RESPUESTA, temperature=0.2,
        ).choices[0].message.content
        return {"pregunta": pregunta, "respuesta": respuesta, "papers": papers}

    def _respuesta_recibida(self, resultado):
        self.enviar.setEnabled(True)
        if "error" in resultado:
            self._escribir(f"Error: {resultado['error']}")
            return
        respuesta = resultado["respuesta"]
        self.historial.extend([
            {"role": "user", "content": resultado["pregunta"]},
            {"role": "assistant", "content": respuesta},
        ])
        self._escribir(f"Medicine Study AI: {respuesta}")
        guardar_chat_db(self.chat_id, resultado["pregunta"][:80], self.historial, self.usuario_id)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Medicine Study AI")
        self.resize(1100, 760)
        self.stack = QStackedWidget()
        self.login = LoginWidget()
        self.login.autenticado.connect(self.mostrar_chat)
        self.stack.addWidget(self.login)
        self.setCentralWidget(self.stack)
        self.setStyleSheet(
            "QMainWindow, QWidget { background: #111217; color: #e2e8f0; }"
            "QLineEdit, QPlainTextEdit, QComboBox, QListWidget { background: #1e1f28; "
            "border: 1px solid #3b4252; padding: 6px; color: #f8fafc; }"
            "QPushButton { background: #2563eb; color: white; padding: 7px 12px; "
            "border-radius: 4px; } QPushButton:disabled { background: #475569; }"
        )

    @Slot(int, str)
    def mostrar_chat(self, usuario_id, nombre):
        if self.stack.count() > 1:
            self.stack.removeWidget(self.stack.widget(1))
        chat = ChatWidget(usuario_id, nombre)
        chat.cerrar_sesion.connect(self.cerrar_sesion)
        self.stack.addWidget(chat)
        self.stack.setCurrentWidget(chat)

    def cerrar_sesion(self):
        self.stack.setCurrentWidget(self.login)


def main():
    """Punto de entrada compatible para integraciones que llamaban app_ui.main."""
    aplicacion = QApplication.instance() or QApplication(sys.argv)
    ventana = MainWindow()
    ventana.show()
    return aplicacion.exec()
