# Vista de Inicio de Sesión
import tkinter as tk
from PIL import Image, ImageTk
import os
from config import COLORS, ASSETS_PATH, LOGO_FILE


class LoginView:
    """Pantalla de inicio con logo y botón de inicio de sesión"""
    
    def __init__(self, parent, app):
        self.app = app
        
        # Frame principal
        self.frame = tk.Frame(parent, bg="#f0f0f0")
        self.frame.pack(fill="both", expand=True)
        
        # Contenedor central
        self.content_frame = tk.Frame(self.frame, bg=COLORS['white'], relief="flat")
        self.content_frame.place(relx=0.5, rely=0.5, anchor="center", width=400, height=550)
        
        # Variables de entrada
        self.email_var = tk.StringVar()
        self.password_var = tk.StringVar()
        
        self.load_logo()
        
        # Título
        tk.Label(
            self.content_frame,
            text="Control de acceso seguro para Universidades",
            font=("Arial", 12, "bold"),
            bg=COLORS['white'],
            fg="#333333"
        ).pack(pady=(0, 5))
        
        # Subtítulo
        tk.Label(
            self.content_frame,
            text="Sentinel System",
            font=("Arial", 12),
            bg=COLORS['white'],
            fg="#666666"
        ).pack(pady=5)
        
        tk.Label(self.content_frame, text="", bg=COLORS['white'], height=1).pack()
        
        # Campo de correo electrónico
        tk.Label(
            self.content_frame,
            text="Correo Electrónico",
            font=("Arial", 10, "bold"),
            bg=COLORS['white'],
            fg="#333333",
            anchor="w"
        ).pack(pady=(10, 5), padx=40, fill="x")
        
        email_entry = tk.Entry(
            self.content_frame,
            textvariable=self.email_var,
            font=("Arial", 11),
            bg="#f5f5f5",
            relief="solid",
            borderwidth=1
        )
        email_entry.pack(pady=(0, 15), padx=40, fill="x", ipady=8)
        
        # Campo de contraseña
        tk.Label(
            self.content_frame,
            text="Contraseña",
            font=("Arial", 10, "bold"),
            bg=COLORS['white'],
            fg="#333333",
            anchor="w"
        ).pack(pady=(0, 5), padx=40, fill="x")
        
        password_entry = tk.Entry(
            self.content_frame,
            textvariable=self.password_var,
            font=("Arial", 11),
            bg="#f5f5f5",
            relief="solid",
            borderwidth=1,
            show="●"
        )
        password_entry.pack(pady=(0, 20), padx=40, fill="x", ipady=8)
        
        # Botón principal
        tk.Button(
            self.content_frame,
            text="Iniciar Sesión",
            font=("Arial", 14, "bold"),
            bg=COLORS['primary'],
            fg="white",
            activebackground=COLORS['primary_dark'],
            activeforeground="white",
            relief="flat",
            cursor="hand2",
            width=20,
            height=2,
            command=self.login
        ).pack(pady=(5, 20))
    
    def load_logo(self):
        """Carga el logo del sistema o muestra texto alternativo"""
        try:
            logo_path = os.path.join(ASSETS_PATH, LOGO_FILE)
            image = Image.open(logo_path)
            image.thumbnail((300, 200), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(image)
            
            logo_label = tk.Label(self.content_frame, image=photo, bg=COLORS['white'])
            logo_label.image = photo  # Mantener referencia para evitar garbage collection
            logo_label.pack(pady=(2, 0))
        except:
            # Fallback si no hay logo
            tk.Label(
                self.content_frame,
                text="SENTINEL\nSYSTEM",
                font=("Arial", 24, "bold"),
                bg=COLORS['white'],
                fg=COLORS['primary']
            ).pack(pady=40)
    
    def login(self):
        """Valida las credenciales y navega a la vista principal"""
        email = self.email_var.get().strip()
        password = self.password_var.get().strip()
        
        # Validar que los campos no estén vacíos
        if not email or not password:
            self.show_error("Por favor, complete todos los campos")
            return
        
        # Validar formato de correo básico
        if "@" not in email or "." not in email:
            self.show_error("Por favor, ingrese un correo válido")
            return
        
        # Aquí puedes agregar validación contra base de datos
        # Por ahora, permitir acceso para continuar con el sistema
        self.app.show_main_view()
    
    def show_error(self, message):
        """Muestra un mensaje de error"""
        from tkinter import messagebox
        messagebox.showerror("Error de autenticación", message)
