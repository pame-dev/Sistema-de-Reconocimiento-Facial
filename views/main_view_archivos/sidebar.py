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



class SidebarMixin:
    def create_sidebar(self):
        c = self.colors
        self.sidebar = ctk.CTkFrame(self.body_frame, fg_color=c['sidebar'],
                                    width=SIDEBAR_WIDTH, corner_radius=0)
        self.sidebar.pack_propagate(False)

        mh = ctk.CTkFrame(self.sidebar, fg_color=c['header'],
                           corner_radius=0, height=48)
        mh.pack(fill="x")
        mh.pack_propagate(False)
        ctk.CTkLabel(mh, text=f"  {t('navegacion')}", font=("Segoe UI", 11, "bold"),
                     text_color=c['white'], anchor="w").pack(fill="both", expand=True, padx=16)

        for icono, clave, cmd in [
            ("🏠", "inicio",   self.show_home),
            ("➕", "nuevo",    self.show_nuevo_registro),
            ("📚", "info",     self.show_informacion_escolar),
            ("📊", "historial", self.show_historial_accesos),
            ("🔐", "pantalla", self.show_pantalla_accesos),
        ]:
            self._create_menu_button(icono, clave, cmd)

        ctk.CTkFrame(self.sidebar, fg_color=c['header_hover'],
                     height=1, corner_radius=0).pack(fill="x", padx=16, pady=14)
        ctk.CTkLabel(self.sidebar, text="v1.0.0", font=("Segoe UI", 10),
                     text_color=c['text_gray']).pack(side="bottom", pady=(0, 8))

    def _create_menu_button(self, icono, clave, command):
        c   = self.colors
        btn = ctk.CTkButton(
            self.sidebar,
            text=f"  {icono}  {t(clave)}",
            anchor="w", font=("Segoe UI", 13),
            fg_color="transparent", hover_color=COLORS['sidebar_hover'],
            text_color=c['white'], height=44, corner_radius=10)
        btn.configure(command=lambda cmd=command: self._nav(cmd, btn))
        btn.pack(fill="x", padx=10, pady=2)
        self.nav_buttons.append((btn, clave, icono))

    def _actualizar_sidebar_idioma(self):
        for btn, clave, icono in self.nav_buttons:
            btn.configure(text=f"  {icono}  {t(clave)}")

    def _nav(self, command, btn):
        if self._active_btn and self._active_btn != btn:
            self._active_btn.configure(fg_color="transparent")
        btn.configure(fg_color=self.colors['sidebar_hover'])
        self._active_btn = btn
        self._close_sidebar()
        command()
        #self.nav_buttons = []

    def _close_sidebar(self):
        if self.menu_visible:
            self.sidebar.pack_forget()
            self.menu_visible = False

    # ══════════════════════════════════════════════════════════════════════════
    # CONTENT
    # ══════════════════════════════════════════════════════════════════════════
    def create_content_area(self):
        self.content_frame = ctk.CTkFrame(self.body_frame,
                                          fg_color=self.colors['background'])
        self.content_frame.pack(fill="both", expand=True, side="left")
        self.content_frame.main_view = self

    def toggle_menu(self):
        if self.menu_visible:
            self.sidebar.pack_forget()
            self.menu_visible = False
        else:
            self.content_frame.pack_forget()
            self.sidebar.pack(fill="y", side="left")
            self.content_frame.pack(fill="both", expand=True, side="left")
            self.menu_visible = True

    def clear_content(self):
        self._stop_camera()
        for w in self.content_frame.winfo_children():
            view = getattr(w, 'view', None)
            if view and hasattr(view, 'destroy'):
                try:
                    view.destroy()
                except Exception:
                    pass
            w.destroy()
