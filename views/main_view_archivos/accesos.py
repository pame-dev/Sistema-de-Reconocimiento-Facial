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

import os
import sys

sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "admin", "biometric_system")
))

from reconocimiento import ReconocerFacial



class AccesosMixin:
    def show_pantalla_accesos(self):
        self._vista_actual    = "pantalla_accesos"
        self._panel_reset_job = None
        self._borde_job       = None
        self._sin_cara_job    = None
        self._historial_items = []
        self.clear_content()
        c = self.colors

        outer = ctk.CTkFrame(self.content_frame, fg_color=c['background'])
        outer.pack(fill="both", expand=True)
        outer.grid_rowconfigure(1, weight=1)
        outer.grid_columnconfigure(0, weight=1)

        # ── Barra superior ────────────────────────────────────────────────────
        bar = ctk.CTkFrame(outer, fg_color=c['bar_bg'],
                           border_color=c['bar_border'], border_width=1,
                           corner_radius=0, height=52)
        bar.grid(row=0, column=0, sticky="ew")
        bar.grid_propagate(False)

        logo_f = ctk.CTkFrame(bar, fg_color="transparent")
        logo_f.pack(side="left", padx=16, pady=8)
        ctk.CTkLabel(logo_f, text="🛡", font=("Segoe UI Emoji", 20),
                     text_color=c['info']).pack(side="left", padx=(0, 8))
        ctk.CTkLabel(logo_f, text=t("control_accesos"),
                     font=("Segoe UI", 14, "bold"),
                     text_color=c['info']).pack(side="left")

        self._btn_iniciar = ctk.CTkButton(
            bar, text=t("iniciar"),
            fg_color="#16a34a", hover_color="#15803d",
            text_color="white", font=("Segoe UI", 12, "bold"),
            width=100, height=32, corner_radius=8,
            command=self._toggle_camera)
        self._btn_iniciar.pack(side="left", padx=12)
        self._anim_running = False

        self._lbl_cam = ctk.CTkLabel(
            bar, text="⬤  Cargando modelo...",
            font=("Segoe UI", 10), text_color=c['accent'])
        self._lbl_cam.pack(side="right", padx=16)

        # ── Cuerpo ────────────────────────────────────────────────────────────
        self._accesos_body = ctk.CTkFrame(outer, fg_color="transparent")
        self._accesos_body.grid(row=1, column=0, sticky="nsew", padx=12, pady=(6, 12))
        self._accesos_body.grid_rowconfigure(0, weight=4, minsize=360)
        self._accesos_body.grid_rowconfigure(1, weight=1, minsize=170)
        self._accesos_body.grid_columnconfigure(0, weight=1)
        self._cam_card = ctk.CTkFrame(self._accesos_body, fg_color=c['card_bg'],
                                       border_color=c['cam_border'], border_width=3,
                                       corner_radius=14)
        self._cam_card.grid(row=0, column=0, sticky="nsew", pady=(0, 8))
        self._cam_card.grid_propagate(False)
        self._cam_card.grid_rowconfigure(0, weight=1)
        self._cam_card.grid_columnconfigure(0, weight=1)

        self._cam_canvas = tk.Canvas(self._cam_card, bg=c['cam_bg'], highlightthickness=0)
        self._cam_canvas.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
        self._cam_canvas.bind("<Configure>", lambda e: self._draw_placeholder())

        # Panel información
        self._user_card = ctk.CTkFrame(self._accesos_body, fg_color=c['card_bg'],
                                        border_color=c['border'], border_width=1,
                                        corner_radius=14)
        self._user_card.grid(row=1, column=0, sticky="nsew")
        self._user_card.grid_propagate(False)
        self._construir_panel_espera()

        # Iniciar motor de reconocimiento
        try:
            self._engine = ReconocerFacial()
            self._engine.on_resultado = self._cb_resultado
            self._engine.on_status    = self._cb_status
            self._engine.on_sin_cara  = self._cb_sin_cara
            threading.Thread(target=self._init_engine, daemon=True).start()
        except Exception as e:
            self._engine = None
            self._lbl_cam.configure(text="⬤  Error de reconocimiento", text_color="#ef4444")
            messagebox.showerror(
                "Error de reconocimiento",
                f"No se pudo iniciar el motor facial.\n\nDetalle: {e}",
            )

    # ── Panel espera ──────────────────────────────────────────────────────────
    def _construir_panel_espera(self):
        for w in self._user_card.winfo_children():
            w.destroy()
        inner = ctk.CTkFrame(self._user_card, fg_color="transparent")
        inner.place(relx=0.5, rely=0.5, anchor="center")
        ctk.CTkLabel(inner, text="👤", font=("Segoe UI Emoji", 52),
                     text_color="#cbd5e1").pack(pady=(0, 10))
        ctk.CTkLabel(inner, text=t("esperando"),
                     font=("Segoe UI", 21, "bold"),
                     text_color=self.colors['text_gray']).pack()
        ctk.CTkLabel(inner, text=t("colocate"),
                     font=("Segoe UI", 18),
                     text_color=self.colors['text_light']).pack(pady=(6, 0))

    # ── Panel usuario reconocido ──────────────────────────────────────────────
    def _construir_panel_usuario(self, nombre, datos_bd, tipo, confianza=None, distancia=None):
        for w in self._user_card.winfo_children():
            w.destroy()

        c           = self.colors
        es_aceptado = (tipo == "aceptado")
        color_tipo  = "#16a34a" if es_aceptado else "#dc2626"
        icono_tipo = f"✓  {t('acceso_permitido')}" if es_aceptado else f"✗  {t('acceso_denegado')}"
        rol = t(datos_bd.get('rol', 'usuario'))
        ICONOS_ROL = {"alumno": "🎓", "maestro": "📚", "personal": "🏢"}
        LABEL_ROL  = {
            "alumno":   "Estudiante",
            "maestro":  "Docente",
            "personal": "Personal Escolar",
        }
        icono_rol = ICONOS_ROL.get(rol, "👤")
        label_rol = LABEL_ROL.get(rol, rol.capitalize())

        # Franja superior
        top_bar = ctk.CTkFrame(self._user_card, fg_color=color_tipo,
                               corner_radius=0, height=50)
        top_bar.pack(fill="x")
        top_bar.pack_propagate(False)
        ctk.CTkLabel(top_bar, text=icono_tipo,
                     font=("Segoe UI", 15, "bold"),
                     text_color="#ffffff").pack(expand=True)

        # Scroll con info
        scroll = ctk.CTkScrollableFrame(self._user_card, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=14, pady=10)

        def sep():
            ctk.CTkFrame(scroll, fg_color=COLORS['border'],
                         height=1, corner_radius=0).pack(fill="x", pady=6)

        def fila(label_txt, valor):
            if not valor or valor == '—':
                return
            row = ctk.CTkFrame(scroll, fg_color="transparent")
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=label_txt,
                         font=("Segoe UI", 10), text_color=c['text_gray'],
                         width=100, anchor="w").pack(side="left")
            ctk.CTkLabel(row, text=str(valor),
                         font=("Segoe UI", 10, "bold"), text_color=c['text_dark'],
                         anchor="w", wraplength=150).pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(scroll, text=icono_rol, font=("Segoe UI Emoji", 40)).pack(pady=(4, 2))

        nombre_display = datos_bd.get('nombre_display', nombre)
        ctk.CTkLabel(scroll, text=nombre_display,
                     font=("Segoe UI", 15, "bold"), text_color=c['text_dark'],
                     wraplength=210, justify="center").pack()

        badge = ctk.CTkFrame(scroll, fg_color=color_tipo, corner_radius=8)
        badge.pack(pady=(4, 6))
        ctk.CTkLabel(badge, text=f"  {label_rol}  ",
                     font=("Segoe UI", 10, "bold"),
                     text_color="#ffffff").pack(padx=4, pady=3)

    # Confianza / distancia LBPH
        if confianza is not None:
            if distancia is not None:
                ctk.CTkLabel(
                    scroll,
                    text=f"{t('distancia_lbph')}: {distancia:.1f} · {t('confianza')}: {confianza:.1f}%",
                    font=("Segoe UI", 10),
                    text_color=c['text_gray']
                ).pack()
            else:
                ctk.CTkLabel(
                    scroll,
                    text=f"{t('confianza')}: {confianza:.1f}%",
                    font=("Segoe UI", 10),
                    text_color=c['text_gray']
                ).pack()

        sep()
        fila(t("matricula"), datos_bd.get('matricula'))
        fila(t("telefono"),  datos_bd.get('telefono'))
        fila(t("correo"),    datos_bd.get('correo'))

        if rol == 'alumno':
            sep()
            ctk.CTkLabel(
                scroll,
                text=t("info_academica"),
                font=("Segoe UI", 10, "bold"),
                text_color=color_tipo
            ).pack(anchor="w", pady=(0, 4))

            fila(t("facultad"), datos_bd.get('facultad'))
            fila(t("carrera"),  datos_bd.get('carrera'))
            fila(t("grado"),    datos_bd.get('grado'))
            fila(t("grupo"),    datos_bd.get('grupo'))

        elif rol == 'maestro':
            sep()
            ctk.CTkLabel(
                scroll,
                text=t("info_docente"),
                font=("Segoe UI", 10, "bold"),
                text_color=color_tipo
            ).pack(anchor="w", pady=(0, 4))

            fila(t("materia"),        datos_bd.get('materia'))
            fila(t("grado_imparte"),  datos_bd.get('grado'))

        elif rol == 'personal':
            sep()
            ctk.CTkLabel(
                scroll,
                text=t("info_laboral"),
                font=("Segoe UI", 10, "bold"),
                text_color=color_tipo
            ).pack(anchor="w", pady=(0, 4))

            fila(t("puesto"), datos_bd.get('puesto'))
            fila(t("area"),   datos_bd.get('area'))

        sep()
        ctk.CTkLabel(
            scroll,
            text=f"🕐 {datetime.now().strftime('%H:%M:%S')}",
            font=("Segoe UI", 11),
            text_color=c['text_gray']
        ).pack()
    # ── Animación borde cámara ────────────────────────────────────────────────
    def _animar_borde(self, color_hex, pasos=6):
        if self._borde_job:
            try:
                self.main_frame.after_cancel(self._borde_job)
            except Exception:
                pass
        c = self.colors

        def _tick(n):
            if n <= 0:
                try:
                    self._cam_card.configure(border_color=c['cam_border'])
                except Exception:
                    pass
                return
            try:
                self._cam_card.configure(
                    border_color=color_hex if n % 2 == 0 else c['cam_border'])
            except Exception:
                return
            self._borde_job = self.main_frame.after(180, _tick, n - 1)

        _tick(pasos)

    def _programar_reset_por_ausencia(self):
        if self._sin_cara_job:
            try:
                self.main_frame.after_cancel(self._sin_cara_job)
            except Exception:
                pass
        self._sin_cara_job = self.main_frame.after(5000, self._limpiar_panel_resultado)

    def _cancelar_reset_por_ausencia(self):
        if self._sin_cara_job:
            try:
                self.main_frame.after_cancel(self._sin_cara_job)
            except Exception:
                pass
            self._sin_cara_job = None

    def _limpiar_panel_resultado(self):
        try:
            self._construir_panel_espera()
            self._cam_card.configure(border_color=self.colors['cam_border'])
        except Exception:
            pass

    def _sincronizar_layout_pantalla_accesos(self):
        vertical = self._debe_usar_layout_vertical_accesos()
        if self._accesos_layout_vertical is None or vertical != self._accesos_layout_vertical:
            self._aplicar_layout_pantalla_accesos(vertical)

    def _aplicar_layout_pantalla_accesos(self, vertical=True):
        body = getattr(self, "_accesos_body", None)
        if not body or not body.winfo_exists():
            return

        try:
            self._cam_card.grid_forget()
            self._user_card.grid_forget()
        except Exception:
            pass

        # Limpiar configuraciones previas de grid.
        for idx in (0, 1):
            try:
                body.grid_rowconfigure(idx, weight=0, minsize=0)
            except Exception:
                pass
            try:
                body.grid_columnconfigure(idx, weight=0, minsize=0)
            except Exception:
                pass

        if vertical:
            body.grid_rowconfigure(0, weight=4, minsize=360)
            body.grid_rowconfigure(1, weight=1, minsize=170)
            body.grid_columnconfigure(0, weight=1)

            self._cam_card.grid(row=0, column=0, sticky="nsew", pady=(0, 8))
            self._user_card.grid(row=1, column=0, sticky="nsew")
        else:
            body.grid_rowconfigure(0, weight=1)
            body.grid_columnconfigure(0, weight=3)
            body.grid_columnconfigure(1, weight=2)

            self._cam_card.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
            self._user_card.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        self._accesos_layout_vertical = vertical