import os
import tkinter as tk

import customtkinter as ctk
from PIL import Image

from config import ASSETS_PATH, COLORS, ICON_FILE
from views.font_scale import FontScale

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGO_PATH = os.path.join(BASE_DIR, ASSETS_PATH, ICON_FILE)

# Paleta light moderna
_DARK_BG    = "#F0F4F8"   # fondo general gris muy claro
_DARK_PANEL = "#1A56A0"   # panel izquierdo azul oscuro (se queda oscuro para contraste)
_ACCENT     = "#2D7DD2"   # azul acento
_ACCENT2    = "#1A56A0"   # azul más oscuro
_TEXT_MAIN  = "#0D1190"   # texto principal casi negro
_TEXT_MUTED = "#5A6A7A"   # gris medio
_BORDER_DK  = "#B0C4DE"   # borde claro
_CARD_BG    = "#FFFFFF"   # card blanca
_INPUT_BG   = "#F6F8FA"   # input gris muy suave
_CHIP_BG    = "#EBF2FA"   # chip azul muy claro


class LoginView:
    """Pantalla de inicio de sesión — Dark tech aesthetic"""

    def __init__(self, parent, app):
        self.app           = app
        self._pass_visible = False

        # Fondo oscuro total
        self.frame = ctk.CTkFrame(parent, fg_color=_DARK_BG)
        self.frame.pack(fill="both", expand=True)

        # Panel izquierdo
        self.left_panel = ctk.CTkFrame(self.frame, fg_color=_DARK_PANEL, corner_radius=0)
        self.left_panel.place(relx=0, rely=0, relwidth=0.48, relheight=1.0)
        self._build_left_panel()

        # Línea divisoria de acento
        ctk.CTkFrame(self.frame, fg_color=_ACCENT, width=2, corner_radius=0).place(
            relx=0.48, rely=0, relwidth=0.002, relheight=1.0
        )

        # Card de login
        self.card = ctk.CTkFrame(
            self.frame,
            fg_color=_CARD_BG,
            corner_radius=20,
            border_width=1,
            border_color=_BORDER_DK,
        )
        self.card.place(relx=0.74, rely=0.5, anchor="center", relwidth=0.43, relheight=0.86)

        self.email_var    = tk.StringVar()
        self.password_var = tk.StringVar()
        self._build_card()

    # ── Panel izquierdo ───────────────────────────────────────────────────────

    def _build_left_panel(self):
        inner = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        inner.place(relx=0.5, rely=0.5, anchor="center")

        # Logo
        try:
            image = Image.open(LOGO_PATH)
            self._left_logo = ctk.CTkImage(light_image=image, dark_image=image, size=(130, 100))
            ctk.CTkLabel(inner, image=self._left_logo, text="").pack(pady=(0, 22))
        except Exception:
            ctk.CTkLabel(
                inner, text="🔐",
                font=("Segoe UI Emoji", 72),
                text_color=_ACCENT
            ).pack(pady=(0, 22))

        # Nombre
        ctk.CTkLabel(
            inner, text="SENTINEL",
            font=("Segoe UI", 32, "bold"),
            text_color="#FFFFFF"
        ).pack()

        ctk.CTkLabel(
            inner, text="S Y S T E M",
            font=("Segoe UI", 13),
            text_color="#A8C8F0"
        ).pack(pady=(2, 8))

        # Línea decorativa
        line = ctk.CTkFrame(inner, fg_color="transparent")
        line.pack(pady=(4, 22))
        ctk.CTkFrame(line, fg_color=_BORDER_DK, height=1, width=55, corner_radius=2).pack(side="left")
        ctk.CTkFrame(line, fg_color=_ACCENT,    height=2, width=36, corner_radius=2).pack(side="left", padx=4)
        ctk.CTkFrame(line, fg_color=_BORDER_DK, height=1, width=55, corner_radius=2).pack(side="left")

        ctk.CTkLabel(
            inner,
            text="Control de acceso biométrico\npara instituciones educativas",
            font=("Segoe UI", 12),
            text_color="#B0C4DE",
            justify="center"
        ).pack(pady=(0, 28))

        # Feature chips
        features = [
            ("🔍", "Reconocimiento facial en tiempo real"),
            ("🔒", "Acceso seguro y registrado"),
            ("📋", "Historial completo de entradas"),
            ("👥", "Gestión de alumnos, maestros y personal"),
        ]
        for icono, texto in features:
            chip = ctk.CTkFrame(
                inner, fg_color=_CHIP_BG,
                corner_radius=8,
                border_width=1,
                border_color=_BORDER_DK
            )
            chip.pack(fill="x", pady=3, ipady=5)
            ctk.CTkLabel(chip, text=icono, font=("Segoe UI Emoji", 14),
                         text_color=_ACCENT).pack(side="left", padx=(12, 8))
            ctk.CTkLabel(chip, text=texto, font=("Segoe UI", 11),
                         text_color=_TEXT_MUTED, anchor="w").pack(side="left", padx=(0, 12))

        ctk.CTkLabel(
            inner, text="v1.0.0  •  2026",
            font=("Segoe UI", 10), text_color=_BORDER_DK
        ).pack(pady=(24, 0))

    # ── Card ─────────────────────────────────────────────────────────────────

    def _build_card(self):

        # Logo pequeño
        try:
            image = Image.open(LOGO_PATH)
            self._card_logo = ctk.CTkImage(light_image=image, dark_image=image, size=(72, 55))
            ctk.CTkLabel(self.card, image=self._card_logo, text="").pack(pady=(22, 4))
        except Exception:
            ctk.CTkLabel(
                self.card, text="🔐",
                font=("Segoe UI Emoji", 42),
                text_color=_ACCENT
            ).pack(pady=(22, 4))

        ctk.CTkLabel(
            self.card, text="Le da la Bienvenida",
            font=("Segoe UI", 20, "bold"),
            text_color=_TEXT_MAIN
        ).pack(pady=(0, 3))

        ctk.CTkLabel(
            self.card, text="Ingresa tus credenciales para acceder",
            font=("Segoe UI", 11),
            text_color=_TEXT_MUTED
        ).pack(pady=(0, 18))

        # Separador
        ctk.CTkFrame(self.card, fg_color=_BORDER_DK, height=1).pack(fill="x", padx=28, pady=(0, 18))

        # Correo
        self._lbl("Correo electrónico")
        self.email_entry = ctk.CTkEntry(
            self.card,
            textvariable=self.email_var,
            height=44, corner_radius=10,
            border_width=1, border_color=_BORDER_DK,
            fg_color=_INPUT_BG,
            text_color=_TEXT_MAIN,
            placeholder_text="usuario@universidad.edu",
            placeholder_text_color=_TEXT_MUTED,
            font=("Segoe UI", 12),
        )
        self.email_entry.pack(pady=(5, 14), padx=28, fill="x")

        # Contraseña
        self._lbl("Contraseña")
        pass_row = ctk.CTkFrame(self.card, fg_color="transparent")
        pass_row.pack(pady=(5, 6), padx=28, fill="x")

        self.password_entry = ctk.CTkEntry(
            pass_row,
            textvariable=self.password_var,
            show="*", height=44, corner_radius=10,
            border_width=1, border_color=_BORDER_DK,
            fg_color=_INPUT_BG,
            text_color=_TEXT_MAIN,
            placeholder_text="••••••••",
            placeholder_text_color=_TEXT_MUTED,
            font=("Segoe UI", 13),
        )
        self.password_entry.pack(side="left", fill="x", expand=True)

        self.btn_ojo = ctk.CTkButton(
            pass_row, text="👁",
            width=44, height=44,
            fg_color=_INPUT_BG, hover_color=_BORDER_DK,
            text_color=_TEXT_MUTED,
            border_width=1, border_color=_BORDER_DK,
            corner_radius=10,
            font=("Segoe UI Emoji", 15),
            command=self._toggle_password
        )
        self.btn_ojo.pack(side="left", padx=(6, 0))

        # Botón ingresar
        ctk.CTkButton(
            self.card,
            text="Iniciar sesión  →",
            height=46, corner_radius=10,
            fg_color=_ACCENT, hover_color=_ACCENT2,
            text_color="#FFFFFF",
            font=FontScale.fb(13),
            command=self.login,
        ).pack(padx=28, fill="x", pady=(20, 0))

        # Footer
        ctk.CTkLabel(
            self.card,
            text="Sentinel System  •  Acceso seguro",
            font=("Segoe UI", 12),
            text_color="#AAAAAA"
        ).pack(side="bottom", pady=12)

        # Bindings
        self.email_entry.focus_set()
        self.email_entry.bind("<Return>",    lambda _: self.password_entry.focus_set())
        self.password_entry.bind("<Return>", lambda _: self.login())

    def _lbl(self, text):
        ctk.CTkLabel(
            self.card, text=text,
            text_color=_TEXT_MUTED,
            font=("Segoe UI", 11, "bold"),
            anchor="w"
        ).pack(padx=28, fill="x")

    def _toggle_password(self):
        self._pass_visible = not self._pass_visible
        self.password_entry.configure(show="" if self._pass_visible else "*")
        self.btn_ojo.configure(text="🙈" if self._pass_visible else "👁")

    def login(self):
        self.app.show_main_view()
