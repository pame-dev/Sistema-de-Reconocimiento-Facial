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
from tools.access_counter import AccessCounter

class HomeMixin:
    def show_home(self):
        self._vista_actual = "home"
        self.clear_content()
        c = self.colors

        outer = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        outer.pack(fill="both", expand=True, padx=30, pady=24)

        stats_row = ctk.CTkFrame(outer, fg_color="transparent")
        stats_row.pack(fill="x", pady=(0, 18))
        stats_row.grid_columnconfigure((0, 1, 2), weight=1, uniform="stat")

        self._stat_total     = self._stat_card(stats_row, t("total"), "0", COLORS['primary'], "🔢", 0)
        self._stat_aceptados = self._stat_card(stats_row, t("aceptados"), "0", "#27AE60",         "✅", 1)
        self._stat_denegados = self._stat_card(stats_row, t("denegados"), "0", COLORS['danger'],  "❌", 2)
        self._cargar_stats()

        card = ctk.CTkFrame(outer, fg_color=c['card_bg'], corner_radius=18,
                            border_width=1, border_color=COLORS['border'])
        card.pack(fill="both", expand=True)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.place(relx=0.5, rely=0.5, anchor="center")

        try:
            logo_path = os.path.join(os.path.dirname(__file__), "..", "..","assets",
                                     "sentinelSystemIconoo.png")
            img = Image.open(logo_path).resize((90, 90), Image.LANCZOS)
            self._home_logo = ctk.CTkImage(light_image=img, dark_image=img, size=(100, 90))
            ctk.CTkLabel(inner, image=self._home_logo, text="").pack(pady=(0, 12))
        except Exception:
            ctk.CTkLabel(inner, text="🔐", font=FontScale.fb(48)).pack(pady=(0, 12))

        ctk.CTkLabel(inner, text=t("bienvenida"),
                     font=FontScale.fb(22), text_color=c['text_dark']).pack()
        ctk.CTkLabel(inner, text=t("seleccion"),
                     font=FontScale.f(18), text_color=c['text_gray']).pack(pady=(6, 22))
        ctk.CTkButton(inner, text=t("agregar"),
                      fg_color=c['primary'], hover_color=COLORS['primary_dark'],
                      text_color="#ffffff", font=FontScale.fb(16),
                      corner_radius=10, height=42, width=260,
                      command=self.show_nuevo_registro).pack()

    def _stat_card(self, parent, titulo, valor, color, icono, col):
        c    = self.colors
        card = ctk.CTkFrame(parent, fg_color=c['card_bg'], corner_radius=14,
                            border_width=1, border_color=COLORS['border'])
        card.grid(row=0, column=col, padx=4, sticky="ew")
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(padx=8, pady=8, fill="x")
        top = ctk.CTkFrame(inner, fg_color="transparent")
        top.pack(fill="x")
        ctk.CTkLabel(top, text=titulo, font=FontScale.fb(19),
                     text_color=color, anchor="w").pack(side="left")
        ctk.CTkLabel(top, text=icono, font=FontScale.f(20)).pack(side="right")
        lbl = ctk.CTkLabel(inner, text=valor, font=FontScale.fb(24),
                           text_color=c['text_dark'], anchor="w")
        lbl.pack(anchor="w", pady=(4, 0))
        return lbl

    def _cargar_stats(self):
        try:
            total = AccessCounter.get()
            conn = get_db()
            if not conn:
                self._stat_total.configure(text=str(total))
                return
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM accesos WHERE estado_acceso='aceptado'")
            aceptados = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM accesos WHERE estado_acceso='denegado'")
            denegados = cur.fetchone()[0]
            conn.close()
            total_db = (aceptados or 0) + (denegados or 0)
            self._stat_total.configure(text=str(total_db))
            self._stat_aceptados.configure(text=str(aceptados))
            self._stat_denegados.configure(text=str(denegados))
        except Exception:
            pass