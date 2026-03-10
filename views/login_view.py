import os
import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk
from PIL import Image

from config import ASSETS_PATH, COLORS, LOGO_FILE


class LoginView:
    """Pantalla de inicio con logo y botón de inicio de sesión"""
    
    def __init__(self, parent, app):
        self.app = app
        self.logo_image = None

        self.frame = ctk.CTkFrame(parent, fg_color=COLORS["background"])
        self.frame.pack(fill="both", expand=True)

        self.center_card = ctk.CTkFrame(
            self.frame,
            fg_color=COLORS["white"],
            corner_radius=18,
            border_width=1,
            border_color=COLORS["border"],
        )
        self.center_card.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.40, relheight=0.90)

        self.email_var = tk.StringVar()
        self.password_var = tk.StringVar()

        self._build_ui()

    def _build_ui(self):
        self._load_logo()

        ctk.CTkLabel(
            self.center_card,
            text="Sentinel System",
            text_color=COLORS["text_dark"],
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(pady=(6, 4), padx=34)

        ctk.CTkLabel(
            self.center_card,
            text="Control de acceso seguro para universidades",
            text_color=COLORS["text_gray"],
            font=ctk.CTkFont(size=14),
        ).pack(pady=(0, 18))

        ctk.CTkLabel(
            self.center_card,
            text="Correo electronico",
            text_color=COLORS["text_dark"],
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w",
        ).pack(padx=40, fill="x")

        email_entry = ctk.CTkEntry(
            self.center_card,
            textvariable=self.email_var,
            height=42,
            corner_radius=10,
            border_width=1,
            border_color=COLORS["border"],
            fg_color=COLORS["card_bg"],
            text_color=COLORS["text_dark"],
            placeholder_text="usuario@universidad.edu",
        )
        email_entry.pack(pady=(6, 14), padx=40, fill="x")

        #campo de contraseña
        ctk.CTkLabel(
            self.center_card,
            text="Contrasena",
            text_color=COLORS["text_dark"],
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w",
        ).pack(padx=40, fill="x")

        password_entry = ctk.CTkEntry(
            self.center_card,
            textvariable=self.password_var,
            show="*",
            height=42,
            corner_radius=10,
            border_width=1,
            border_color=COLORS["border"],
            fg_color=COLORS["card_bg"],
            text_color=COLORS["text_dark"],
            placeholder_text="Ingresa tu contrasena",
        )
        password_entry.pack(pady=(6, 22), padx=40, fill="x")

        #boton de inicio de sesion
        ctk.CTkButton(
            self.center_card,
            text="Iniciar sesion",
            height=44,
            corner_radius=10,
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_dark"],
            text_color=COLORS["white"],
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self.login,
        ).pack(padx=40, fill="x")

        email_entry.focus_set()
        email_entry.bind("<Return>", lambda _event: password_entry.focus_set())
        password_entry.bind("<Return>", lambda _event: self.login())

    def _load_logo(self):
        """Carga el logo en formato CTkImage o muestra texto alternativo."""
        try:
            logo_path = os.path.join(ASSETS_PATH, LOGO_FILE)
            image = Image.open(logo_path)
            self.logo_image = ctk.CTkImage(light_image=image, dark_image=image, size=(220, 150))
            ctk.CTkLabel(self.center_card, text="", image=self.logo_image).pack(pady=(26, 10))
        except Exception:
            ctk.CTkLabel(
                self.center_card,
                text="SENTINEL\nSYSTEM",
                text_color=COLORS["primary"],
                font=ctk.CTkFont(size=28, weight="bold"),
            ).pack(pady=(30, 18))

    def login(self):
        """Valida credenciales y navega a la vista principal."""
        email = self.email_var.get().strip()
        password = self.password_var.get().strip()
        
        # Validar que los campos no estén vacíos
        if not email or not password:
            self.show_error("Por favor, complete todos los campos")
            return
        
        # Validar formato de correo básico
        if "@" not in email or "." not in email:
            self.show_error("Por favor, ingrese un correo valido")
            return
        
        # Aquí puedes agregar validación contra base de datos
        # Por ahora, permitir acceso para continuar con el sistema
        self.app.show_main_view()

    def show_error(self, message):
        """Muestra mensaje de error en un cuadro de dialogo."""
        messagebox.showerror("Error de autenticacion", message)
