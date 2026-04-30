import os
import math
import tkinter as tk

import customtkinter as ctk
from PIL import Image

from config import ASSETS_PATH, COLORS, ICON_FILE
from views.font_scale import FontScale

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGO_PATH = os.path.join(BASE_DIR, ASSETS_PATH, ICON_FILE)

# ── Paleta ────────────────────────────────────────────────────────────────────
_NAVY        = "#0C1B3A"   # fondo panel izquierdo
_NAVY_LIGHT  = "#162847"   # hover / acento panel
_BLUE        = "#378ADD"   # azul acento
_BLUE_DIM    = "#185FA5"   # azul oscuro
_BLUE_GLOW   = "#85B7EB"   # azul claro (texto secundario panel)
_BLUE_PALE   = "#E6F1FB"   # azul muy claro (chip bg)
_BLUE_CHIP   = "#B5D4F4"   # borde chip

_CARD_BG     = "#F8FAFC"   # fondo right side
_WHITE       = "#FFFFFF"   # card interna
_GRAY_BG     = "#F1EFE8"   # chip sesión bg
_GRAY_BORDER = "#D3D1C7"   # bordes grises
_GRAY_MID    = "#B4B2A9"   # separadores
_GRAY_TEXT   = "#888780"   # texto muted

_TEXT_DARK   = "#0C1B3A"   # texto principal
_TEXT_SEMI   = "#2C2C2A"   # texto semi oscuro
_GREEN       = "#3B6D11"   # verde icono
_GREEN_BG    = "#EAF3DE"   # verde fondo icono
_GREEN_DOT   = "#639922"   # punto activo

_METRIC_BLUE = "#185FA5"   # métrica azul


class LoginView:
    """Pantalla de acceso directo al sistema — diseño renovado."""

    def __init__(self, parent, app):
        self.app = app

        # Contenedor raíz
        self.frame = ctk.CTkFrame(parent, fg_color=_CARD_BG)
        self.frame.pack(fill="both", expand=True)

        # Panel izquierdo (42 % del ancho)
        self.left = ctk.CTkFrame(
            self.frame, fg_color=_NAVY, corner_radius=0
        )
        self.left.place(relx=0, rely=0, relwidth=0.42, relheight=1.0)

        # Área derecha (58 %)
        self.right = ctk.CTkFrame(self.frame, fg_color=_CARD_BG, corner_radius=0)
        self.right.place(relx=0.42, rely=0, relwidth=0.58, relheight=1.0)

        # Círculos decorativos sobre el canvas del panel izquierdo
        self._circles_canvas = None

        self.left.bind("<Configure>", self._draw_circles)

        self._build_left()
        self._build_right()

    # ── Decoración geométrica ─────────────────────────────────────────────────

    def _draw_circles(self, event=None):
        """Dibuja círculos tenues sobre el panel izquierdo."""
        w = self.left.winfo_width()
        h = self.left.winfo_height()
        if w < 10:
            return

        if self._circles_canvas:
            self._circles_canvas.destroy()

        canvas = tk.Canvas(
            self.left, bg=_NAVY, highlightthickness=0,
            width=w, height=h
        )
        canvas.place(x=0, y=0, relwidth=1.0, relheight=1.0)
        canvas.lower("all")

        # Círculos esquina superior derecha (colores sólidos progresivos)
        circle_colors = ["#1A3560", "#162E55", "#12264A"]
        for r, color in zip([180, 110, 55], circle_colors):
            canvas.create_oval(
                w - r, -r, w + r, r,
                outline=color, width=1, fill=""
            )

        # Círculos esquina inferior izquierda
        for r, color in zip([200, 120], ["#1A3560", "#162E55"]):
            canvas.create_oval(
                -r, h - r, r, h + r,
                outline=color, width=1, fill=""
            )

        self._circles_canvas = canvas
        # Reubicar el contenido encima del canvas
        self._left_inner.lift()

    # ── Panel izquierdo ───────────────────────────────────────────────────────

    def _build_left(self):
        self._left_inner = ctk.CTkFrame(self.left, fg_color="transparent")
        self._left_inner.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.88)

        # Ícono / logo
        try:
            img = Image.open(LOGO_PATH)
            self._logo_img = ctk.CTkImage(light_image=img, dark_image=img, size=(80, 62))
            ctk.CTkLabel(
                self._left_inner, image=self._logo_img, text=""
            ).pack(pady=(0, 18))
        except Exception:
            # Ícono SVG-like hecho con un frame circular
            icon_frame = ctk.CTkFrame(
                self._left_inner,
                width=64, height=64,
                corner_radius=32,
                fg_color="#162847",
                border_width=1,
                border_color="#2A5A8A",
            )
            icon_frame.pack(pady=(0, 18))
            icon_frame.pack_propagate(False)
            ctk.CTkLabel(
                icon_frame, text="🛡",
                font=("Segoe UI Emoji", 28),
                text_color=_BLUE
            ).place(relx=0.5, rely=0.5, anchor="center")

        # Nombre del sistema
        ctk.CTkLabel(
            self._left_inner, text="UnimoraAccess",
            font=("Georgia", 28, "bold"),
            text_color="#E6F1FB"
        ).pack()

        

        # Divisor con punto central
        div = ctk.CTkFrame(self._left_inner, fg_color="transparent", height=14)
        div.pack(fill="x", pady=(2, 18))
        ctk.CTkFrame(div, fg_color="#1E3D6A", height=1, corner_radius=0).place(
            relx=0.0, rely=0.5, relwidth=0.44, anchor="w"
        )
        ctk.CTkFrame(div, fg_color=_BLUE, width=6, height=6, corner_radius=3).place(
            relx=0.5, rely=0.5, anchor="center"
        )
        ctk.CTkFrame(div, fg_color="#1E3D6A", height=1, corner_radius=0).place(
            relx=1.0, rely=0.5, relwidth=0.44, anchor="e"
        )

        ctk.CTkLabel(
            self._left_inner,
            text="Control de acceso biométrico\npara instituciones educativas",
            font=("Segoe UI", 11),
            text_color=_BLUE_GLOW,
            justify="center"
        ).pack(pady=(0, 22))

        # Feature chips
        features = [
            ("⊙", "Reconocimiento facial en tiempo real"),
            ("⊠", "Acceso seguro y registrado"),
            ("≡", "Historial completo de entradas"),
            ("⊞", "Gestión de alumnos y personal"),
        ]
        for sym, txt in features:
            chip = ctk.CTkFrame(
                self._left_inner,
                fg_color="#162847",
                corner_radius=8,
                border_width=1,
                border_color="#1E3D6A",
            )
            chip.pack(fill="x", pady=3, ipady=6)

            ctk.CTkLabel(
                chip, text=sym,
                font=("Courier New", 16, "bold"),
                text_color=_BLUE,
                width=28,
            ).pack(side="left", padx=(12, 6))

            ctk.CTkLabel(
                chip, text=txt,
                font=("Segoe UI", 10),
                text_color=_BLUE_GLOW,
                anchor="w"
            ).pack(side="left", padx=(0, 12))

        ctk.CTkLabel(
            self._left_inner,
            text="v1.0.0  ·  2026",
            font=("Courier New", 9),
            text_color="#1E3D6A"
        ).pack(pady=(20, 0))

    # ── Lado derecho ──────────────────────────────────────────────────────────

    def _build_right(self):
        center = ctk.CTkFrame(self.right, fg_color="transparent")
        center.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.78)

        # ── Encabezado ────────────────────────────────────────────────────────
        # Ícono verde
        icon_box = ctk.CTkFrame(
            center,
            width=56, height=56,
            corner_radius=14,
            fg_color=_GREEN_BG,
            border_width=1,
            border_color="#C5DDA8",
        )
        icon_box.pack(pady=(0, 16))
        icon_box.pack_propagate(False)
        ctk.CTkLabel(
            icon_box, text="✓",
            font=("Segoe UI", 26, "bold"),
            text_color=_GREEN
        ).place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(
            center, text="Acceso directo",
            font=("Georgia", 20, "bold"),
            text_color=_TEXT_DARK
        ).pack()

        ctk.CTkLabel(
            center,
            text="Sistema de control de acceso institucional",
            font=("Segoe UI", 11),
            text_color=_GRAY_TEXT
        ).pack(pady=(4, 24))

        # ── Tarjeta sesión activa ─────────────────────────────────────────────
        session_card = ctk.CTkFrame(
            center,
            fg_color=_WHITE,
            corner_radius=12,
            border_width=1,
            border_color=_GRAY_BORDER,
        )
        session_card.pack(fill="x", pady=(0, 16))

        session_inner = ctk.CTkFrame(session_card, fg_color="transparent")
        session_inner.pack(fill="x", padx=16, pady=14)

        # Avatar azul marino
        avatar = ctk.CTkFrame(
            session_inner,
            width=36, height=36,
            corner_radius=18,
            fg_color="transparent",
        )
        avatar.pack(side="left", padx=(0, 12))
        avatar.pack_propagate(False)
        # Intentar cargar imagen de avatar proporcionada, si falla usar la letra por defecto
        try:
            avatar_path = r"C:\Users\Colibecas\Desktop\Sistema-de-Reconocimiento-Facial\assets\sentinelSystemLogoo.png"
            _img = Image.open(avatar_path)
            self._avatar_img = ctk.CTkImage(light_image=_img, dark_image=_img, size=(36, 36))
            ctk.CTkLabel(avatar, image=self._avatar_img, text="").place(relx=0.5, rely=0.5, anchor="center")
        except Exception:
            ctk.CTkLabel(
                avatar, text="A",
                font=("Segoe UI", 14, "bold"),
                text_color="#E6F1FB"
            ).place(relx=0.5, rely=0.5, anchor="center")

        # Info usuario
        info = ctk.CTkFrame(session_inner, fg_color="transparent")
        info.pack(side="left")
        ctk.CTkLabel(
            info, text="Administrador",
            font=("Segoe UI", 12, "bold"),
            text_color=_TEXT_SEMI
        ).pack(anchor="w")
        ctk.CTkLabel(
            info, text="Acceso total al sistema",
            font=("Segoe UI", 10),
            text_color=_GRAY_TEXT
        ).pack(anchor="w")

        # Punto verde activo
        dot_frame = ctk.CTkFrame(session_inner, fg_color="transparent")
        dot_frame.pack(side="right")
        ctk.CTkFrame(
            dot_frame,
            width=9, height=9,
            corner_radius=5,
            fg_color=_GREEN_DOT,
        ).pack()

        # Leyenda sesión automática
        ctk.CTkLabel(
            session_card,
            text="Sesión iniciada automáticamente",
            font=("Segoe UI", 10),
            text_color=_GRAY_MID
        ).pack(pady=(0, 12))

        # ── Botón ingresar ────────────────────────────────────────────────────
        ctk.CTkButton(
            center,
            text="  Entrar al sistema  →",
            height=48,
            corner_radius=10,
            fg_color=_NAVY,
            hover_color=_NAVY_LIGHT,
            text_color="#E6F1FB",
            font=FontScale.fb(13),
            command=self.login,
        ).pack(fill="x", pady=(0, 20))

        # ── Separador ─────────────────────────────────────────────────────────
        sep = ctk.CTkFrame(center, fg_color="transparent", height=20)
        sep.pack(fill="x")

        ctk.CTkFrame(sep, fg_color=_GRAY_BORDER, height=1, corner_radius=0).place(
            relx=0.0, rely=0.5, relwidth=0.34, anchor="w"
        )
        ctk.CTkLabel(
            sep, text="UNIMORA ACCES",
            font=("Courier New", 9),
            text_color=_GRAY_MID
        ).place(relx=0.5, rely=0.5, anchor="center")
        ctk.CTkFrame(sep, fg_color=_GRAY_BORDER, height=1, corner_radius=0).place(
            relx=1.0, rely=0.5, relwidth=0.34, anchor="e"
        )

        # ── Métricas ──────────────────────────────────────────────────────────
        metrics_row = ctk.CTkFrame(center, fg_color="transparent")
        metrics_row.pack(fill="x", pady=(14, 0))

        metrics = [
            ("128",  "Usuarios",  _TEXT_DARK),
            ("99 %", "Precisión", _GREEN_DOT),
            ("24/7", "Activo",    _METRIC_BLUE),
        ]
        for val, label, color in metrics:
            card = ctk.CTkFrame(
                metrics_row,
                fg_color=_WHITE,
                corner_radius=8,
                border_width=1,
                border_color=_GRAY_BORDER,
            )
            card.pack(side="left", expand=True, fill="both",
                      padx=4, ipady=8)
            ctk.CTkLabel(
                card, text=val,
                font=("Georgia", 16, "bold"),
                text_color=color
            ).pack()
            ctk.CTkLabel(
                card, text=label,
                font=("Segoe UI", 9),
                text_color=_GRAY_TEXT
            ).pack()

    # ── Acción ───────────────────────────────────────────────────────────────

    def login(self):
        try:
            self.app.show_main_view()
        except Exception as e:
            import traceback
            traceback.print_exc()
            try:
                from tkinter import messagebox
                messagebox.showerror("Error", f"Fallo al entrar al sistema:\n{e}")
            except Exception:
                pass