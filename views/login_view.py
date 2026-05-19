import os
import tkinter as tk

import customtkinter as ctk
from PIL import Image

from config import (
    ASSETS_PATH,
    COLORS,
    ICON_FILE,
    LOGO_FILE,
    toggle_theme
)

from views.font_scale import FontScale
from idiomas import cambiar_idioma, idioma_actual, t

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGO_PATH = os.path.join(BASE_DIR, ASSETS_PATH, ICON_FILE)


class LoginView:
    """Pantalla de acceso directo al sistema."""

    def __init__(self, parent, app):

        self.app = app
        self.parent = parent

        # ─────────────────────────────────────────────
        # COLORES DINÁMICOS
        # ─────────────────────────────────────────────

        self.c = COLORS

        # ─────────────────────────────────────────────
        # CONTENEDOR PRINCIPAL
        # ─────────────────────────────────────────────

        self.frame = ctk.CTkFrame(
            parent,
            fg_color=self.c['background']
        )

        self.frame.pack(fill="both", expand=True)

        # ─────────────────────────────────────────────
        # PANEL IZQUIERDO
        # ─────────────────────────────────────────────

        self.left = ctk.CTkFrame(
            self.frame,
            fg_color=self.c['sidebar'],
            corner_radius=0
        )

        self.left.place(
            relx=0,
            rely=0,
            relwidth=0.48,
            relheight=1.0
        )

        # ─────────────────────────────────────────────
        # PANEL DERECHO
        # ─────────────────────────────────────────────

        self.right = ctk.CTkFrame(
            self.frame,
            fg_color=self.c['background'],
            corner_radius=0
        )

        self.right.place(
            relx=0.48,
            rely=0,
            relwidth=0.52,
            relheight=1.0
        )

        self._circles_canvas = None

        self.left.bind("<Configure>", self._draw_circles)

        self._build_left()
        self._build_right()

        self.crear_boton_idioma()
        self.crear_boton_tema()
        
        self.parent.bind(
            "<Configure>",
            lambda e: self.responsive_top_buttons()
        )

        self.responsive_top_buttons()

    # ─────────────────────────────────────────────────────────
    # BOTÓN CAMBIO IDIOMA
    # ─────────────────────────────────────────────────────────

    def crear_boton_idioma(self):

        idioma = idioma_actual()

        texto = "🌐 ES" if idioma == "es" else "🌐 EN"

        self.btn_idioma = ctk.CTkButton(
            self.frame,
            text=texto,
            width=110,
            height=40,
            corner_radius=18,
            fg_color=self.c['card_bg'],
            hover_color=self.c['sidebar_hover'],
            border_width=1,
            border_color=self.c['border'],
            text_color=self.c['text_dark'],
            font=("Segoe UI", 13, "bold"),
            command=self.cambiar_idioma_ui,
            cursor="hand2"
        )

        self.btn_idioma.place(
            relx=0.97,
            rely=0.03,
            anchor="ne"
        )

    def cambiar_idioma_ui(self):

        nuevo = "en" if idioma_actual() == "es" else "es"

        cambiar_idioma(nuevo)

        self.frame.pack_forget()

        nueva_vista = LoginView(self.parent, self.app)

        try:
            self.app.current_view = nueva_vista

        except Exception:
            pass

    # ─────────────────────────────────────────────
    # BOTÓN TEMA
    # ─────────────────────────────────────────────

    def crear_boton_tema(self):

        modo = "light"

        if self.c['background'] == "#0d1117":
            modo = "dark"

        icono = "🌙" if modo == "light" else "☀"

        self.btn_tema = ctk.CTkButton(
            self.frame,
            text=icono,
            width=42,
            height=40,
            corner_radius=18,
            fg_color=self.c['card_bg'],
            hover_color=self.c['sidebar_hover'],
            border_width=1,
            border_color=self.c['border'],
            text_color=self.c['text_dark'],
            font=("Segoe UI Emoji", 16),
            command=self.cambiar_tema,
            cursor="hand2"
        )

        self.btn_tema.place(
            relx=0.89,
            rely=0.03,
            anchor="ne"
        )

    def cambiar_tema(self):

        toggle_theme()

        self.frame.pack_forget()

        nueva_vista = LoginView(
            self.parent,
            self.app
        )

        try:
            self.app.current_view = nueva_vista

        except Exception:
            pass
        
    # ─────────────────────────────────────────────
    # RESPONSIVE BOTONES SUPERIORES
    # ─────────────────────────────────────────────

    def responsive_top_buttons(self, event=None):
        """Ajusta el tamaño de los botones según el ancho de la ventana."""
        # Validar que los widgets aún existen antes de configurarlos
        if not hasattr(self, 'btn_tema') or self.btn_tema is None:
            return
        
        try:
            if not self.btn_tema.winfo_exists():
                return
        except (tk.TclError, AttributeError):
            return

        try:
            self.btn_tema.configure(
                width=32,
                height=32,
                font=("Segoe UI Emoji", 11)
            )
        except tk.TclError:
            return
        except Exception:
            return

        # Repetir patrón para otros botones si los hay
        for btn_name in ['btn_idioma', 'btn_info', 'btn_salir']:
            if not hasattr(self, btn_name):
                continue
            
            btn = getattr(self, btn_name, None)
            if btn is None:
                continue
            
            try:
                if not btn.winfo_exists():
                    continue
                btn.configure(width=32, height=32, font=("Segoe UI Emoji", 11))
            except (tk.TclError, AttributeError):
                continue
            except Exception:
                continue

    # ─────────────────────────────────────────────────────────
    # DECORACIÓN
    # ─────────────────────────────────────────────────────────

    def _draw_circles(self, event=None):

        w = self.left.winfo_width()
        h = self.left.winfo_height()

        if w < 10:
            return

        if self._circles_canvas:
            self._circles_canvas.destroy()

        canvas = tk.Canvas(
            self.left,
            bg=self.c['sidebar'],
            highlightthickness=0,
            width=w,
            height=h
        )

        canvas.place(x=0, y=0, relwidth=1.0, relheight=1.0)

        canvas.lower("all")

        circle_colors = ["#1A3560", "#162E55", "#12264A"]

        for r, color in zip([180, 110, 55], circle_colors):

            canvas.create_oval(
                w - r,
                -r,
                w + r,
                r,
                outline=color,
                width=1
            )

        for r, color in zip([200, 120], ["#1A3560", "#162E55"]):

            canvas.create_oval(
                -r,
                h - r,
                r,
                h + r,
                outline=color,
                width=1
            )

        self._circles_canvas = canvas

        self._left_inner.lift()

    # ─────────────────────────────────────────────
    # PANEL IZQUIERDO
    # ─────────────────────────────────────────────

    def _build_left(self):

        self._left_inner = ctk.CTkFrame(
            self.left,
            fg_color="transparent"
        )

        self._left_inner.place(
            relx=0.5,
            rely=0.5,
            anchor="center",
            relwidth=0.88
        )

        # ─────────────────────────────────────────
        # LOGO
        # ─────────────────────────────────────────

        try:

            img = Image.open(LOGO_PATH)

            self._logo_img = ctk.CTkImage(
                light_image=img,
                dark_image=img,
                size=(80, 62)
            )

            ctk.CTkLabel(
                self._left_inner,
                image=self._logo_img,
                text=""
            ).pack(pady=(0, 18))

        except Exception:

            icon_frame = ctk.CTkFrame(
                self._left_inner,
                width=64,
                height=64,
                corner_radius=32,
                fg_color=self.c['header_hover'],
                border_width=1,
                border_color=self.c['primary']
            )

            icon_frame.pack(pady=(0, 18))
            icon_frame.pack_propagate(False)

            ctk.CTkLabel(
                icon_frame,
                text="🛡",
                font=("Segoe UI Emoji", 28),
                text_color=self.c['primary']
            ).place(relx=0.5, rely=0.5, anchor="center")

        # ─────────────────────────────────────────
        # TÍTULO
        # ─────────────────────────────────────────

        ctk.CTkLabel(
            self._left_inner,
            text=t("titulo_sistema"),
            font=("Georgia", 18, "bold"),
            text_color="#E6F1FB"
        ).pack()

        # ─────────────────────────────────────────
        # SEPARADOR
        # ─────────────────────────────────────────

        div = ctk.CTkFrame(
            self._left_inner,
            fg_color="transparent",
            height=14
        )

        div.pack(fill="x", pady=(2, 18))

        ctk.CTkFrame(
            div,
            fg_color="#1E3D6A",
            height=1,
            corner_radius=0
        ).place(relx=0.0, rely=0.5, relwidth=0.44, anchor="w")

        ctk.CTkFrame(
            div,
            fg_color=self.c['primary'],
            width=6,
            height=6,
            corner_radius=3
        ).place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkFrame(
            div,
            fg_color="#1E3D6A",
            height=1,
            corner_radius=0
        ).place(relx=1.0, rely=0.5, relwidth=0.44, anchor="e")

        # ─────────────────────────────────────────
        # DESCRIPCIÓN
        # ─────────────────────────────────────────

        ctk.CTkLabel(
            self._left_inner,
            text=t("descripcion_login"),
            font=("Segoe UI", 12),
            text_color="#85B7EB",
            justify="center"
        ).pack(pady=(0, 22))

        # ─────────────────────────────────────────
        # FEATURES
        # ─────────────────────────────────────────

        features = [
            ("⊙", t("reconocimiento_facial")),
            ("⊠", t("acceso_seguro")),
            ("≡", t("historial_entradas")),
            ("⊞", t("gestion_usuarios")),
        ]

        for sym, txt in features:

            chip = ctk.CTkFrame(
                self._left_inner,
                fg_color=self.c['header_hover'],
                corner_radius=8,
                border_width=1,
                border_color="#1E3D6A",
            )

            chip.pack(fill="x", pady=5, ipady=8)

            ctk.CTkLabel(
                chip,
                text=sym,
                font=("Courier New", 18, "bold"),
                text_color=self.c['primary'],
                width=6
            ).pack(side="left", padx=(12, 6))

            ctk.CTkLabel(
                chip,
                text=txt,
                font=("Segoe UI", 12),
                text_color="#85B7EB",
                anchor="w"
            ).pack(side="left", padx=(0, 12))

        ctk.CTkLabel(
            self._left_inner,
            text="v1.0.0 · 2026",
            font=("Courier New", 9),
            text_color="#1E3D6A"
        ).pack(pady=(20, 0))

    # ─────────────────────────────────────────────
    # PANEL DERECHO
    # ─────────────────────────────────────────────

    def _build_right(self):

        center = ctk.CTkFrame(
            self.right,
            fg_color="transparent"
        )

        center.place(
            relx=0.5,
            rely=0.5,
            anchor="center",
            relwidth=0.78
        )

        # Ícono

        icon_box = ctk.CTkFrame(
            center,
            width=56,
            height=56,
            corner_radius=14,
            fg_color=self.c['cam_bg'],
            border_width=1,
            border_color=self.c['cam_border']
        )

        icon_box.pack(pady=(0, 16))
        icon_box.pack_propagate(False)

        ctk.CTkLabel(
            icon_box,
            text="✓",
            font=("Segoe UI", 26, "bold"),
            text_color=self.c['primary']
        ).place(relx=0.5, rely=0.5, anchor="center")

        # Título

        ctk.CTkLabel(
            center,
            text=t("acceso_directo"),
            font=("Georgia", 18, "bold"),
            text_color=self.c['text_dark']
        ).pack()

        # Subtítulo

        ctk.CTkLabel(
            center,
            text=t("subtitulo_login"),
            font=("Segoe UI", 12),
            text_color=self.c['text_gray']
        ).pack(pady=(4, 24))

        # Tarjeta sesión

        session_card = ctk.CTkFrame(
            center,
            fg_color=self.c['card_bg'],
            corner_radius=12,
            border_width=1,
            border_color=self.c['border']
        )

        session_card.pack(fill="x", pady=(0, 16))

        session_inner = ctk.CTkFrame(
            session_card,
            fg_color="transparent"
        )

        session_inner.pack(fill="x", padx=2, pady=14)

        # Avatar

        avatar = ctk.CTkFrame(
            session_inner,
            width=36,
            height=36,
            corner_radius=18,
            fg_color="transparent"
        )

        avatar.pack(side="left", padx=(8, 4))
        avatar.pack_propagate(False)

        try:

            avatar_path = os.path.join(BASE_DIR, ASSETS_PATH, LOGO_FILE)

            _img = Image.open(avatar_path)

            self._avatar_img = ctk.CTkImage(
                light_image=_img,
                dark_image=_img,
                size=(36, 36)
            )

            ctk.CTkLabel(
                avatar,
                image=self._avatar_img,
                text=""
            ).place(relx=0.5, rely=0.5, anchor="center")

        except Exception:

            ctk.CTkLabel(
                avatar,
                text="A",
                font=("Segoe UI", 14, "bold"),
                text_color="#E6F1FB"
            ).place(relx=0.5, rely=0.5, anchor="center")

        # Información

        info = ctk.CTkFrame(
            session_inner,
            fg_color="transparent"
        )

        info.pack(side="left")

        ctk.CTkLabel(
            info,
            text=t("administrador"),
            font=("Segoe UI", 15, "bold"),
            text_color=self.c['text_dark']
        ).pack(anchor="w")

        ctk.CTkLabel(
            info,
            text=t("acceso_total"),
            font=("Segoe UI", 10),
            text_color=self.c['text_gray']
        ).pack(anchor="w")

        # Sesión

        ctk.CTkLabel(
            session_card,
            text=t("sesion_automatica"),
            font=("Segoe UI", 10),
            text_color=self.c['text_gray']
        ).pack(pady=(0, 12))

        # Botón entrar

        ctk.CTkButton(
            center,
            text="  " + t("entrar_sistema") + "  →",
            height=48,
            corner_radius=10,
            fg_color=self.c['primary'],
            hover_color=self.c['primary_dark'],
            text_color="#E6F1FB",
            font=FontScale.fb(16),
            command=self.login
        ).pack(fill="x", pady=(0, 20))

        # Separador

        sep = ctk.CTkFrame(
            center,
            fg_color="transparent",
            height=20
        )

        sep.pack(fill="x")

        ctk.CTkFrame(
            sep,
            fg_color=self.c['border'],
            height=1,
            corner_radius=0
        ).place(relx=0.0, rely=0.5, relwidth=0.34, anchor="w")

        ctk.CTkLabel(
            sep,
            text=t("titulo_sistema").upper(),
            font=("Courier New", 12),
            text_color=self.c['text_gray']
        ).place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkFrame(
            sep,
            fg_color=self.c['border'],
            height=1,
            corner_radius=0
        ).place(relx=1.0, rely=0.5, relwidth=0.34, anchor="e")

        # Métricas (eliminadas por configuración del usuario)

        # LOGIN

    def login(self):

        try:

            self.app.show_main_view()

        except Exception as e:

            import traceback

            traceback.print_exc()

            try:

                from tkinter import messagebox

                messagebox.showerror(
                    "Error",
                    f"Fallo al entrar al sistema:\n{e}"
                )

            except Exception:
                pass
