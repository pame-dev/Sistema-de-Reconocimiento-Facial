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



class UtilsMixin:
    def _guardar_estado_vista_actual(self):
        if self._vista_actual != "nuevo_registro":
            return
        vista = getattr(self, "_nuevo_registro_view", None)
        if not vista:
            return
        try:
            self._nuevo_registro_state = vista.export_state()
        except Exception:
            self._nuevo_registro_state = None
    
    def _esta_en_pantalla_completa(self):
        root = self.parent.winfo_toplevel()
        try:
            if bool(root.attributes("-fullscreen")):
                return True
        except Exception:
            pass
        try:
            if str(root.state()).lower() == "zoomed":
                return True
        except Exception:
            pass
        try:
            sw = root.winfo_screenwidth()
            sh = root.winfo_screenheight()
            w = root.winfo_width()
            h = root.winfo_height()
            return w >= sw - 20 and h >= sh - 20
        except Exception:
            return False

    def _debe_usar_layout_vertical_accesos(self):
        return not self._esta_en_pantalla_completa()