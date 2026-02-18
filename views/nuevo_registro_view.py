# Vista de Nuevo Registro
import tkinter as tk
from config import COLORS


class NuevoRegistroView:
    """Vista para registrar nuevos usuarios en el sistema"""
    
    def __init__(self, parent):
        container = tk.Frame(parent, bg=COLORS['white'])
        container.pack(fill="both", expand=True, padx=30, pady=30)
        
        # Título de la sección
        tk.Label(
            container,
            text="Nuevo Registro",
            font=("Arial", 20, "bold"),
            bg=COLORS['white'],
            fg=COLORS['text_dark']
        ).pack(pady=20, anchor="w")
        
        # Descripción
        tk.Label(
            container,
            text="Aquí podrás registrar nuevos usuarios en el sistema.",
            font=("Arial", 12),
            bg=COLORS['white'],
            fg=COLORS['text_gray']
        ).pack(pady=10, anchor="w")
        
        # Área de formulario (placeholder)
        form_frame = tk.Frame(container, bg=COLORS['content_bg'], relief="solid", borderwidth=1)
        form_frame.pack(fill="both", expand=True, pady=20)
        
        tk.Label(
            form_frame,
            text="Formulario de registro\n(En desarrollo)",
            font=("Arial", 14),
            bg=COLORS['content_bg'],
            fg=COLORS['text_light']
        ).pack(expand=True)
