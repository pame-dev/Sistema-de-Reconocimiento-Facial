# views/seleccion_rol.py
import customtkinter as ctk

from config import COLORS, get_colors
from idiomas import t
from views.nuevo_registro.constants import ROL_CONFIG
from views.nuevo_registro.utils import darken


class SeleccionRolMixin:
    """
    Mixin que añade la pantalla de selección de rol.
    Requiere que la clase base tenga: self.container, self.colors,
    self.rol_actual, self._limpiar_container(), self._mostrar_formulario().
    """

    def _mostrar_seleccion_rol(self):
        self.rol_actual   = None
        self.valores_form = {}
        self._limpiar_container()

        outer = ctk.CTkFrame(self.container, fg_color="transparent")
        outer.pack(fill="both", expand=True)

        ctk.CTkLabel(outer, text=t("nuevo_registro_titulo"),
                     font=("Segoe UI", 22, "bold"),
                     text_color=self.colors['text_dark']).pack(pady=(20, 4))
        ctk.CTkLabel(outer, text=t("selecciona_tipo_usuario"),
                     font=("Segoe UI", 12),
                     text_color=self.colors['text_gray']).pack(pady=(0, 16))

        cards_frame = ctk.CTkFrame(outer, fg_color="transparent")
        cards_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        for i in range(3):
            cards_frame.grid_columnconfigure(i, weight=1, uniform="rol")
        cards_frame.grid_rowconfigure(0, weight=1)

        for idx, (rol_key, cfg) in enumerate(ROL_CONFIG.items()):
            self._crear_tarjeta(cards_frame, rol_key, cfg, col=idx)

    def _crear_tarjeta(self, parent, rol_key, cfg, col):
        color = cfg["color"]
        outer = ctk.CTkFrame(parent, fg_color=color, corner_radius=14)
        outer.grid(row=0, column=col, padx=10, pady=10, sticky="nsew")
        outer.grid_rowconfigure(0, weight=1)
        outer.grid_columnconfigure(0, weight=1)

        card = ctk.CTkFrame(outer, fg_color=self.colors['card_bg'], corner_radius=12)
        card.grid(row=0, column=0, padx=3, pady=3, sticky="nsew")
        card.grid_rowconfigure(1, weight=1)
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(card, text=cfg["icono"],
             font=("Segoe UI Emoji", 50)).grid(row=0, column=0, pady=(10, 2))

        info = ctk.CTkFrame(card, fg_color="transparent")
        info.grid(row=1, column=0, sticky="ew", padx=8, pady=0)
        ctk.CTkLabel(info, text=cfg["titulo"], font=("Segoe UI", 10, "bold"),
                     text_color=color, justify="center").pack()
        

        ctk.CTkButton(card, text=t("seleccionar"),
                      fg_color=color, hover_color=darken(color),
                      text_color=self.colors['white'],
                      font=("Segoe UI", 8, "bold"),
                      corner_radius=10, height=32,
                      command=lambda r=rol_key: self._seleccionar_rol(r),
                      ).grid(row=2, column=0, padx=2, pady=(12, 22), sticky="ew")

        for w in (outer, card):
            w.bind("<Button-1>", lambda e, r=rol_key: self._seleccionar_rol(r))

    def _seleccionar_rol(self, rol_key):
        self.rol_actual = rol_key
        self._mostrar_formulario()