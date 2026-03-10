# Vista Principal con Menú Lateral
import tkinter as tk
import customtkinter as ctk
import os
import sys
import subprocess
from config import COLORS, SIDEBAR_WIDTH, HEADER_HEIGHT
from views.nuevo_registro_view import NuevoRegistroView
from views.informacion_escolar_view import InformacionEscolarView
from views.historial_accesos_view import HistorialAccesosView
from PIL import Image, ImageTk


class MainView:
    """Vista principal de la aplicación con header, menú lateral y área de contenido"""

    def __init__(self, parent, app):
        self.app = app
        self.menu_visible = True
        self.nav_buttons = []
        self.home_logo_image = None

        self.main_frame = ctk.CTkFrame(parent, fg_color=COLORS['background'])
        self.main_frame.pack(fill="both", expand=True)

        self.create_header()

        self.body_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.body_frame.pack(fill="both", expand=True)

        self.create_sidebar()
        self.create_content_area()
        self.show_home()

    def create_header(self):
        header = ctk.CTkFrame(self.main_frame, fg_color=COLORS['header'], corner_radius=0, height=HEADER_HEIGHT)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        ctk.CTkButton(
            header,
            text="☰",
            font=("Segoe UI", 24, "bold"),
            fg_color="transparent",
            hover_color=COLORS['header_hover'],
            text_color=COLORS['white'],
            width=50,
            height=44,
            command=self.toggle_menu
        ).pack(side="left", padx=10)

        ctk.CTkLabel(
            header,
            text="Sentinel System - Panel Principal",
            font=("Segoe UI", 20, "bold"),
            text_color=COLORS['white']
        ).pack(side="left", padx=20)

    def create_sidebar(self):
        self.sidebar = ctk.CTkFrame(
            self.body_frame,
            fg_color=COLORS['sidebar'],
            width=SIDEBAR_WIDTH,
            corner_radius=0,
            border_width=0
        )
        self.sidebar.pack(fill="y", side="left")
        self.sidebar.pack_propagate(False)

        ctk.CTkLabel(
            self.sidebar,
            text="Menú",
            font=("Segoe UI", 18, "bold"),
            text_color=COLORS['white']
        ).pack(fill="x")
        ctk.CTkLabel(self.sidebar, text="", height=12).pack()

        ctk.CTkFrame(self.sidebar, fg_color=COLORS['header_hover'], height=1, corner_radius=0).pack(fill="x", padx=16)
        ctk.CTkLabel(self.sidebar, text="", height=8).pack()

        self.create_menu_button("🏠 Inicio",                 self.show_home)
        self.create_menu_button("➕ Nuevo Registro",        self.show_nuevo_registro)
        self.create_menu_button("📚 Información Escolar",   self.show_informacion_escolar)
        self.create_menu_button("📊 Historial de Accesos",  self.show_historial_accesos)
        self.create_menu_button("🔐 Pantalla de Accesos",   self.show_pantalla_accesos)

        ctk.CTkFrame(self.sidebar, fg_color=COLORS['header_hover'], height=1, corner_radius=0).pack(fill="x", padx=16, pady=14)

        ctk.CTkButton(
            self.sidebar,
            text="Cerrar Sesión",
            font=("Segoe UI", 12, "bold"),
            fg_color=COLORS['danger'],
            hover_color=COLORS['danger_dark'],
            text_color=COLORS['white'],
            corner_radius=10,
            height=42,
            command=self.logout
        ).pack(side="bottom", fill="x", padx=10, pady=10)

    def create_menu_button(self, text, command):
        btn = ctk.CTkButton(
            self.sidebar,
            text=text,
            anchor="w",
            font=("Segoe UI", 14),
            fg_color="transparent",
            hover_color=COLORS['sidebar_hover'],
            text_color=COLORS['white'],
            height=44,
            corner_radius=10,
            command=command
        )
        btn.pack(fill="x", padx=10, pady=2)
        self.nav_buttons.append(btn)

    def create_content_area(self):
        self.content_frame = ctk.CTkFrame(self.body_frame, fg_color=COLORS['background'])
        self.content_frame.pack(fill="both", expand=True, side="left")

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
        for widget in self.content_frame.winfo_children():
            widget.destroy()

    def show_home(self):
        self.clear_content()

        welcome_frame = tk.Frame(self.content_frame, bg=COLORS['white'])
        welcome_frame.place(relx=0.5, rely=0.5, anchor="center", width=500, height=350)

        tk.Label(
            welcome_frame,
            text="Bienvenido al Sistema",
            font=("Arial", 24, "bold"),
            bg=COLORS['white'],
            fg=COLORS['text_dark']
        ).pack(pady=40)

        tk.Label(
            welcome_frame,
            text="Seleccione una opción del menú\npara comenzar",
            font=("Arial", 14),
            bg=COLORS['white'],
            fg=COLORS['text_gray'],
            justify="center"
        ).pack(pady=20)

        try:
            logo_path = os.path.join(os.path.dirname(__file__), "..", "assets", "sentinelSystemIcono.png")
            logo_img = Image.open(logo_path)
            logo_img = logo_img.resize((100, 90))
            logo_photo = ImageTk.PhotoImage(logo_img)
            logo_label = tk.Label(welcome_frame, image=logo_photo, bg=COLORS['white'])
            logo_label.image = logo_photo
            logo_label.pack(pady=20)
        except:
            pass

    def show_nuevo_registro(self):
        self.clear_content()
        NuevoRegistroView(self.content_frame)

    def show_informacion_escolar(self):
        self.clear_content()
        vista = InformacionEscolarView(self.content_frame)
        self.content_frame.update()
        vista.cargar_datos()

    def show_pantalla_accesos(self):
        """Ejecuta el sistema de reconocimiento facial"""
        try:
            # Ruta al archivo reconocimiento.py
            script_path = os.path.join(
                os.path.dirname(__file__),
                "..",
                "admin",
                "biometric_system",
                "reconocimiento.py"
            )
            script_path = os.path.abspath(script_path)

            # Directorio raíz del proyecto
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

            # Verificar que el archivo existe
            if not os.path.exists(script_path):
                raise FileNotFoundError(f"No se encontró el archivo: {script_path}")

            # Ejecutar el script usando el mismo intérprete de Python y desde el directorio raíz
            subprocess.Popen(
                [sys.executable, script_path],
                cwd=project_root,
                creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
            )

            # Mostrar confirmación en el contenido
            self.clear_content()
            frame = ctk.CTkFrame(
                self.content_frame,
                fg_color=COLORS['card_bg'],
                corner_radius=16,
                border_width=1,
                border_color=COLORS['border']
            )
            frame.place(relx=0.5, rely=0.5, anchor="center", width=480, height=260)

            ctk.CTkLabel(
                frame,
                text="📹",
                font=("Segoe UI Emoji", 48)
            ).pack(pady=(20, 5))

            ctk.CTkLabel(
                frame,
                text="Sistema de Reconocimiento",
                font=("Segoe UI", 22, "bold"),
                text_color=COLORS['text_dark']
            ).pack()

            ctk.CTkLabel(
                frame,
                text="Se ha iniciado la cámara de reconocimiento facial",
                font=("Segoe UI", 13),
                text_color=COLORS['text_gray'],
                wraplength=350
            ).pack(pady=5)

        except Exception as e:
            self.clear_content()
            frame = ctk.CTkFrame(
                self.content_frame,
                fg_color=COLORS['card_bg'],
                corner_radius=16,
                border_width=1,
                border_color=COLORS['border']
            )
            frame.place(relx=0.5, rely=0.5, anchor="center", width=520, height=280)

            ctk.CTkLabel(
                frame,
                text="⚠️",
                font=("Segoe UI Emoji", 48)
            ).pack(pady=(20, 5))

            ctk.CTkLabel(
                frame,
                text="Error al iniciar",
                font=("Segoe UI", 22, "bold"),
                text_color=COLORS['danger']
            ).pack()

            ctk.CTkLabel(
                frame,
                text=str(e),
                font=("Segoe UI", 12),
                text_color=COLORS['text_gray'],
                wraplength=350
            ).pack(pady=5)

    def show_historial_accesos(self):
        self.clear_content()
        vista = HistorialAccesosView(self.content_frame)
        self.content_frame.update()
        vista.cargar_datos()

    def logout(self):
        self.app.show_login_view()