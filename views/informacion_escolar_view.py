# Vista de Información Escolar
import tkinter as tk
from config import COLORS


class InformacionEscolarView:
    """Vista para consultar y gestionar información escolar"""
    
    def __init__(self, parent):
        container = tk.Frame(parent, bg=COLORS['white'])
        container.pack(fill="both", expand=True, padx=30, pady=30)
        
        # Título de la sección
        tk.Label(
            container,
            text="Información Escolar",
            font=("Arial", 20, "bold"),
            bg=COLORS['white'],
            fg=COLORS['text_dark']
        ).pack(pady=20, anchor="w")
        
        # Descripción
        tk.Label(
            container,
            text="Consulta y gestiona la información escolar de los usuarios.",
            font=("Arial", 12),
            bg=COLORS['white'],
            fg=COLORS['text_gray']
        ).pack(pady=10, anchor="w")
        
        # Área de contenido (placeholder)
        content_frame = tk.Frame(container, bg=COLORS['content_bg'], relief="solid", borderwidth=1)
        content_frame.pack(fill="both", expand=True, pady=20)
        
        tk.Label(
            content_frame,
            text="Información escolar\n(En desarrollo)",
            font=("Arial", 14),
            bg=COLORS['content_bg'],
            fg=COLORS['text_light']
        ).pack(expand=True)
