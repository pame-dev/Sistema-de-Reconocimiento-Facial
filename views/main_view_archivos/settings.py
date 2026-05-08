import tkinter as tk
import customtkinter as ctk
import os
import sys
import threading
import time
import cv2
from datetime import datetime
from camera import Camera
from config import COLORS, get_colors, toggle_theme, SIDEBAR_WIDTH, HEADER_HEIGHT, get_db
from views.nuevo_registro_view import NuevoRegistroView
from views.informacion_escolar_view import InformacionEscolarView
from views.historial_accesos_view import HistorialAccesosView
from PIL import Image, ImageTk
from tkinter import messagebox
from idiomas import t, cambiar_idioma


from views.font_scale import FontScale

class SettingsMixin:
    def modo_oscuro(self):
        toggle_theme()
        self.colors = get_colors()
        self._recargar_vista()
        self.main_frame.configure(fg_color=self.colors['background'])
        self.content_frame.configure(fg_color=self.colors['background'])

    def traducir_app(self):
        cambiar_idioma()
        self.lbl_titulo.configure(text=t("titulo"))

        self._actualizar_sidebar_idioma()
        try:
            self.btn_salir.configure(text=t("salir"))
        except Exception:
            pass
        self._recargar_vista()

    def logout(self):
        if messagebox.askyesno(t("confirmar_salida"), t("seguro_salir")):
            self._stop_camera()
            self.app.show_login_view()