# Vista Principal con Menú Lateral
import tkinter as tk
import os
from config import COLORS, SIDEBAR_WIDTH, HEADER_HEIGHT
from views.nuevo_registro_view import NuevoRegistroView
from views.informacion_escolar_view import InformacionEscolarView
from PIL import Image, ImageTk


class MainView:
    """Vista principal de la aplicación con header, menú lateral y área de contenido"""

    def __init__(self, parent, app):
        self.app = app
        self.menu_expanded = False

        self.main_frame = tk.Frame(parent, bg=COLORS['background'])
        self.main_frame.pack(fill="both", expand=True)

        self.create_header()

        self.body_frame = tk.Frame(self.main_frame, bg=COLORS['background'])
        self.body_frame.pack(fill="both", expand=True)

        self.create_sidebar()
        self.create_content_area()
        self.show_home()

    def create_header(self):
        header = tk.Frame(self.main_frame, bg=COLORS['header'], height=HEADER_HEIGHT)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        tk.Button(
            header,
            text="☰",
            font=("Arial", 20),
            bg=COLORS['header'],
            fg="white",
            activebackground=COLORS['header_hover'],
            activeforeground="white",
            relief="flat",
            cursor="hand2",
            width=3,
            command=self.toggle_menu
        ).pack(side="left", padx=10)

        tk.Label(
            header,
            text="Sentinel System - Panel Principal",
            font=("Arial", 16, "bold"),
            bg=COLORS['header'],
            fg="white"
        ).pack(side="left", padx=20)

    def create_sidebar(self):
        self.sidebar = tk.Frame(self.body_frame, bg=COLORS['sidebar'], width=SIDEBAR_WIDTH)
        self.sidebar.pack_propagate(False)

        tk.Label(
            self.sidebar,
            text="Menú",
            font=("Arial", 14, "bold"),
            bg=COLORS['sidebar'],
            fg="white",
            pady=20
        ).pack(fill="x")

        tk.Frame(self.sidebar, bg=COLORS['header'], height=2).pack(fill="x")

        self.create_menu_button("🏠 Inicio",                 self.show_home)
        self.create_menu_button("➕ Nuevo Registro",        self.show_nuevo_registro)
        self.create_menu_button("📚 Información Escolar",   self.show_informacion_escolar)
        self.create_menu_button("📊 Historial de Accesos",  self.show_historial_accesos)

        tk.Frame(self.sidebar, bg=COLORS['header'], height=2).pack(fill="x", pady=10)

        tk.Button(
            self.sidebar,
            text="Cerrar Sesión",
            font=("Arial", 11),
            bg=COLORS['danger'],
            fg="white",
            activebackground=COLORS['danger_dark'],
            activeforeground="white",
            relief="flat",
            cursor="hand2",
            command=self.logout
        ).pack(side="bottom", fill="x", padx=10, pady=10)

    def create_menu_button(self, text, command):
        btn = tk.Button(
            self.sidebar,
            text=text,
            font=("Arial", 12),
            bg=COLORS['sidebar'],
            fg="white",
            activebackground=COLORS['sidebar_hover'],
            activeforeground="white",
            relief="flat",
            cursor="hand2",
            anchor="w",
            padx=20,
            pady=15,
            command=command
        )
        btn.pack(fill="x")
        btn.bind("<Enter>", lambda e: btn.config(bg=COLORS['sidebar_hover']))
        btn.bind("<Leave>", lambda e: btn.config(bg=COLORS['sidebar']))

    def create_content_area(self):
        self.content_frame = tk.Frame(self.body_frame, bg=COLORS['background'])
        self.content_frame.pack(fill="both", expand=True, side="left")

    def toggle_menu(self):
        if self.menu_expanded:
            self.sidebar.pack_forget()
            self.menu_expanded = False
        else:
            self.content_frame.pack_forget()
            self.sidebar.pack(fill="y", side="left")
            self.content_frame.pack(fill="both", expand=True, side="left")
            self.menu_expanded = True

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

    def show_historial_accesos(self):
        self.clear_content()
        # Sin funcionalidad aún — placeholder
        frame = tk.Frame(self.content_frame, bg=COLORS['white'])
        frame.place(relx=0.5, rely=0.5, anchor="center", width=400, height=200)

        tk.Label(
            frame,
            text="📊",
            font=("Arial", 48),
            bg=COLORS['white']
        ).pack(pady=(20, 5))

        tk.Label(
            frame,
            text="Historial de Accesos",
            font=("Arial", 18, "bold"),
            bg=COLORS['white'],
            fg=COLORS['text_dark']
        ).pack()

        tk.Label(
            frame,
            text="(En desarrollo)",
            font=("Arial", 12),
            bg=COLORS['white'],
            fg=COLORS['text_gray']
        ).pack(pady=5)

    def logout(self):
        self.app.show_login_view()