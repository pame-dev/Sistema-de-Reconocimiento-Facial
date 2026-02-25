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
        self.menu_expanded = False  # Estado del menú (abierto/cerrado)
        
        # Frame principal
        self.main_frame = tk.Frame(parent, bg=COLORS['background'])
        self.main_frame.pack(fill="both", expand=True)
        
        self.create_header()
        
        # Contenedor para menú y contenido
        self.body_frame = tk.Frame(self.main_frame, bg=COLORS['background'])
        self.body_frame.pack(fill="both", expand=True)
        
        self.create_sidebar()
        self.create_content_area()
        self.show_home()
    
    def create_header(self):
        """Crea la barra superior con botón de menú"""
        header = tk.Frame(self.main_frame, bg=COLORS['header'], height=HEADER_HEIGHT)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)
        
        # Botón hamburguesa para abrir/cerrar menú
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
        
        # Título del sistema
        tk.Label(
            header,
            text="Sentinel System - Panel Principal",
            font=("Arial", 16, "bold"),
            bg=COLORS['header'],
            fg="white"
        ).pack(side="left", padx=20)
    
    def create_sidebar(self):
        """Crea el menú lateral con opciones de navegación"""
        self.sidebar = tk.Frame(self.body_frame, bg=COLORS['sidebar'], width=SIDEBAR_WIDTH)
        self.sidebar.pack_propagate(False)
        
        # Título
        tk.Label(
            self.sidebar,
            text="Menú",
            font=("Arial", 14, "bold"),
            bg=COLORS['sidebar'],
            fg="white",
            pady=20
        ).pack(fill="x")
        
        tk.Frame(self.sidebar, bg=COLORS['header'], height=2).pack(fill="x")
        
        # Opciones del menú
        self.create_menu_button("Nuevo Registro", self.show_nuevo_registro)
        self.create_menu_button("Información Escolar", self.show_informacion_escolar)
        
        tk.Frame(self.sidebar, bg=COLORS['header'], height=2).pack(fill="x", pady=10)
        
        # Botón cerrar sesión
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
        """Crea un botón del menú con efecto hover"""
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
        
        # Efectos hover
        btn.bind("<Enter>", lambda e: btn.config(bg=COLORS['sidebar_hover']))
        btn.bind("<Leave>", lambda e: btn.config(bg=COLORS['sidebar']))
    
    def create_content_area(self):
        """Crea el área donde se muestran las diferentes vistas"""
        self.content_frame = tk.Frame(self.body_frame, bg=COLORS['background'])
        self.content_frame.pack(fill="both", expand=True, side="left")
    
    def toggle_menu(self):
        """Abre o cierra el menú lateral"""
        if self.menu_expanded:
            self.sidebar.pack_forget()
            self.menu_expanded = False
        else:
            # Reempaquetar en orden correcto: sidebar primero, content después
            self.content_frame.pack_forget()
            self.sidebar.pack(fill="y", side="left")
            self.content_frame.pack(fill="both", expand=True, side="left")
            self.menu_expanded = True
    
    def clear_content(self):
        """Elimina el contenido actual del área principal"""
        for widget in self.content_frame.winfo_children():
            widget.destroy()
    
    def show_home(self):
        """Pantalla de bienvenida inicial"""
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
        
        # Cargar icono si existe
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
        """Carga la vista de registro de nuevos usuarios"""
        self.clear_content()
        NuevoRegistroView(self.content_frame)
    
    def show_informacion_escolar(self):
        """Carga la vista de información escolar"""
        self.clear_content()
        vista = InformacionEscolarView(self.content_frame)
        self.content_frame.update()  # forzar render antes de cargar datos
        vista.cargar_datos()
    
    def logout(self):
        """Cierra sesión y vuelve al login"""
        self.app.show_login_view()