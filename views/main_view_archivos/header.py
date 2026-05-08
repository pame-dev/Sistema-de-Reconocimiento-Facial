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

class HeaderMixin:
    def create_header(self):
        c = self.colors
        header = ctk.CTkFrame(self.main_frame, fg_color=c['header'],
                              corner_radius=0, height=HEADER_HEIGHT)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        ctk.CTkButton(header, text="☰", font=("Segoe UI", 12, "bold"),
              fg_color="transparent", hover_color=COLORS['header_hover'],
              text_color=c['white'], width=20, height=28, corner_radius=8,
              command=self.toggle_menu).pack(side="left", padx=0)

        title_frame = ctk.CTkFrame(header, fg_color="transparent")
        title_frame.pack(side="left", padx=0)
        try:
            logo_path = os.path.join(os.path.dirname(__file__), "..","..", "assets",
                                     "sentinelSystemIconoo.png")
            img = Image.open(logo_path).resize((28, 28), Image.LANCZOS)
            self._header_logo = ctk.CTkImage(light_image=img, dark_image=img, size=(28, 28))
            ctk.CTkLabel(title_frame, image=self._header_logo, text="").pack(side="left", padx=(0, 0))
        except Exception:
            pass
        self.lbl_titulo = ctk.CTkLabel(
            title_frame,
            text=t("titulo"),
            font=("Segoe UI", 21, "bold"),
            text_color=c['white']
        )
        self.lbl_titulo.pack(side="left")

        self.btn_salir = ctk.CTkButton(
            header, text=t("salir"), font=("Segoe UI", 14, "bold"),
            fg_color=c['danger'], hover_color=COLORS['danger_dark'],
            text_color=c['white'], width=20, height=34, corner_radius=8,
            command=self.logout)
        self.btn_salir.pack(side="right", padx=(8, 4))

        self.lbl_reloj = ctk.CTkLabel(
            header,
            text="",
            font=("Segoe UI", 14),
            text_color=c['white'],
            justify="center",
        )
        self.lbl_reloj.pack(side="right", padx=(4, 4))
        self._actualizar_reloj()

        self._btn_traducir = ctk.CTkButton(header, text="🌐", font=("Segoe UI Emoji", 15),
                      fg_color="transparent", hover_color=COLORS['header_hover'],
                  text_color=c['white'], width=36, height=38, corner_radius=8,
                      command=self.traducir_app)
        self._btn_traducir.pack(side="right", padx=(0, 0))

        self._btn_modo_oscuro = ctk.CTkButton(header, text="🌙", font=("Segoe UI Emoji", 15),
                      fg_color="transparent", hover_color=COLORS['header_hover'],
                  text_color=c['white'], width=36, height=38, corner_radius=8,
                      command=self.modo_oscuro)
        self._btn_modo_oscuro.pack(side="right", padx=(0, 0))

    def disable_top_controls(self):
        try:
            self._btn_zoom.pack_forget()
            self._btn_traducir.pack_forget()
            self._btn_modo_oscuro.pack_forget()
        except Exception:
            pass

    def enable_top_controls(self):
        try:
            self._btn_zoom.pack(side="right", padx=(4, 4))
            self._btn_traducir.pack(side="right", padx=(0, 2))
            self._btn_modo_oscuro.pack(side="right", padx=(0, 2))
        except Exception:
            pass

    def _actualizar_reloj(self):
        self.lbl_reloj.configure(text=datetime.now().strftime("%d/%m/%Y\n%H:%M:%S"))
        self.main_frame.after(1000, self._actualizar_reloj)

    