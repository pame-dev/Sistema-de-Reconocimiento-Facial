# Vista Principal con Menú Lateral
import tkinter as tk
import customtkinter as ctk
import os
import sys
import subprocess
from datetime import datetime
from config import COLORS, SIDEBAR_WIDTH, HEADER_HEIGHT, get_db
from views.nuevo_registro_view import NuevoRegistroView
from views.informacion_escolar_view import InformacionEscolarView
from views.historial_accesos_view import HistorialAccesosView
from PIL import Image, ImageTk


class MainView:
    """Vista principal con header, menú lateral y área de contenido"""

    def __init__(self, parent, app):
        self.app          = app
        self.menu_visible = False
        self.nav_buttons  = []
        self._active_btn  = None

        self.main_frame = ctk.CTkFrame(parent, fg_color=COLORS['background'])
        self.main_frame.pack(fill="both", expand=True)

        self.create_header()

        self.body_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.body_frame.pack(fill="both", expand=True)

        self.create_sidebar()
        self.create_content_area()
        self.show_home()

    # ── Header ────────────────────────────────────────────────────────────────

    def create_header(self):
        header = ctk.CTkFrame(
            self.main_frame,
            fg_color=COLORS['header'],
            corner_radius=0,
            height=HEADER_HEIGHT
        )
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        ctk.CTkButton(
            header,
            text="☰",
            font=("Segoe UI", 22, "bold"),
            fg_color="transparent",
            hover_color=COLORS['header_hover'],
            text_color=COLORS['white'],
            width=52,
            height=44,
            corner_radius=8,
            command=self.toggle_menu
        ).pack(side="left", padx=(8, 0))

        title_frame = ctk.CTkFrame(header, fg_color="transparent")
        title_frame.pack(side="left", padx=12)

        try:
            logo_path = os.path.join(
                os.path.dirname(__file__), "..", "assets", "sentinelSystemIcono.ico"
            )
            img = Image.open(logo_path).resize((32, 32), Image.LANCZOS)
            self._header_logo = ctk.CTkImage(light_image=img, dark_image=img, size=(32, 32))
            ctk.CTkLabel(title_frame, image=self._header_logo, text="").pack(side="left", padx=(0, 8))
        except Exception:
            pass

        ctk.CTkLabel(
            title_frame,
            text="Sentinel System — Panel Principal",
            font=("Segoe UI", 18, "bold"),
            text_color=COLORS['white']
        ).pack(side="left")

        # Botón cerrar sesión
        ctk.CTkButton(
            header,
            text="⏻  Salir",
            font=("Segoe UI", 12, "bold"),
            fg_color=COLORS['danger'],
            hover_color=COLORS['danger_dark'],
            text_color=COLORS['white'],
            width=90,
            height=34,
            corner_radius=8,
            command=self.logout
        ).pack(side="right", padx=(0, 12))

        # Reloj
        self.lbl_reloj = ctk.CTkLabel(
            header,
            text="",
            font=("Segoe UI", 12),
            text_color=COLORS['white']
        )
        self.lbl_reloj.pack(side="right", padx=(0, 16))
        self._actualizar_reloj()

    def _actualizar_reloj(self):
        now = datetime.now().strftime("%d/%m/%Y  %H:%M:%S")
        self.lbl_reloj.configure(text=now)
        self.main_frame.after(1000, self._actualizar_reloj)

    # ── Sidebar ───────────────────────────────────────────────────────────────

    def create_sidebar(self):
        self.sidebar = ctk.CTkFrame(
            self.body_frame,
            fg_color=COLORS['sidebar'],
            width=SIDEBAR_WIDTH,
            corner_radius=0
        )
        self.sidebar.pack_propagate(False)

        menu_header = ctk.CTkFrame(
            self.sidebar, fg_color=COLORS['header'], corner_radius=0, height=48
        )
        menu_header.pack(fill="x")
        menu_header.pack_propagate(False)
        ctk.CTkLabel(
            menu_header,
            text="  NAVEGACIÓN",
            font=("Segoe UI", 11, "bold"),
            text_color=COLORS['white'],
            anchor="w"
        ).pack(fill="both", expand=True, padx=16)

        ctk.CTkLabel(self.sidebar, text="", height=8).pack()

        menu_items = [
            ("🏠", "Inicio",               self.show_home),
            ("➕", "Nuevo Registro",       self.show_nuevo_registro),
            ("📚", "Información Escolar",  self.show_informacion_escolar),
            ("📊", "Historial de Accesos", self.show_historial_accesos),
            ("🔐", "Pantalla de Accesos",  self.show_pantalla_accesos),
        ]

        for icono, texto, cmd in menu_items:
            self._create_menu_button(icono, texto, cmd)

        ctk.CTkFrame(
            self.sidebar, fg_color=COLORS['header_hover'], height=1, corner_radius=0
        ).pack(fill="x", padx=16, pady=14)

        ctk.CTkLabel(
            self.sidebar,
            text="v1.0.0",
            font=("Segoe UI", 10),
            text_color=COLORS['text_gray']
        ).pack(side="bottom", pady=(0, 8))

    def _create_menu_button(self, icono, texto, command):
        btn = ctk.CTkButton(
            self.sidebar,
            text=f"  {icono}  {texto}",
            anchor="w",
            font=("Segoe UI", 13),
            fg_color="transparent",
            hover_color=COLORS['sidebar_hover'],
            text_color=COLORS['white'],
            height=44,
            corner_radius=10,
        )
        btn.configure(command=lambda c=command: self._nav(c, btn))
        btn.pack(fill="x", padx=10, pady=2)
        self.nav_buttons.append(btn)

    def _nav(self, command, btn):
        if self._active_btn and self._active_btn != btn:
            self._active_btn.configure(fg_color="transparent")
        btn.configure(fg_color=COLORS['sidebar_hover'])
        self._active_btn = btn
        self._close_sidebar()
        command()

    def _close_sidebar(self):
        if self.menu_visible:
            self.sidebar.pack_forget()
            self.menu_visible = False

    # ── Content ───────────────────────────────────────────────────────────────

    def create_content_area(self):
        self.content_frame = ctk.CTkFrame(
            self.body_frame, fg_color=COLORS['background']
        )
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

    # ── Home ──────────────────────────────────────────────────────────────────

    def show_home(self):
        self.clear_content()

        outer = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        outer.pack(fill="both", expand=True, padx=30, pady=24)

        # ── Fila de estadísticas ──
        stats_row = ctk.CTkFrame(outer, fg_color="transparent")
        stats_row.pack(fill="x", pady=(0, 18))
        stats_row.grid_columnconfigure((0, 1, 2), weight=1, uniform="stat")

        self._stat_total     = self._stat_card(stats_row, "Accesos totales",     "0", COLORS['primary'], "🔢", 0)
        self._stat_aceptados = self._stat_card(stats_row, "Accesos conseguidos", "0", "#27AE60",          "✅", 1)
        self._stat_denegados = self._stat_card(stats_row, "Accesos denegados",   "0", COLORS['danger'],   "❌", 2)

        self._cargar_stats()

        # ── Card de bienvenida ──
        card = ctk.CTkFrame(
            outer,
            fg_color=COLORS['card_bg'],
            corner_radius=18,
            border_width=1,
            border_color=COLORS['border']
        )
        card.pack(fill="both", expand=True)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.place(relx=0.5, rely=0.5, anchor="center")

        try:
            logo_path = os.path.join(
                os.path.dirname(__file__), "..", "assets", "sentinelSystemIcono.png"
            )
            img = Image.open(logo_path).resize((100, 90), Image.LANCZOS)
            self._home_logo = ctk.CTkImage(light_image=img, dark_image=img, size=(100, 90))
            ctk.CTkLabel(inner, image=self._home_logo, text="").pack(pady=(0, 12))
        except Exception:
            ctk.CTkLabel(inner, text="🔐", font=("Segoe UI Emoji", 56)).pack(pady=(0, 12))

        ctk.CTkLabel(
            inner,
            text="Le da la Bienvenida al Sistema",
            font=("Segoe UI", 24, "bold"),
            text_color=COLORS['text_dark']
        ).pack()

        ctk.CTkLabel(
            inner,
            text="Seleccione una opción del menú para comenzar",
            font=("Segoe UI", 13),
            text_color=COLORS['text_gray']
        ).pack(pady=(6, 22))

        ctk.CTkButton(
            inner,
            text="➕  Agregar nuevo usuario",
            fg_color=COLORS['primary'],
            hover_color=COLORS['primary_dark'],
            text_color=COLORS['white'],
            font=("Segoe UI", 13, "bold"),
            corner_radius=10,
            height=42,
            width=260,
            command=self.show_nuevo_registro
        ).pack()

    def _stat_card(self, parent, titulo, valor, color, icono, col):
        card = ctk.CTkFrame(
            parent,
            fg_color=COLORS['card_bg'],
            corner_radius=14,
            border_width=1,
            border_color=COLORS['border']
        )
        card.grid(row=0, column=col, padx=8, sticky="ew")

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(padx=18, pady=14, fill="x")

        top = ctk.CTkFrame(inner, fg_color="transparent")
        top.pack(fill="x")

        ctk.CTkLabel(
            top,
            text=titulo,
            font=("Segoe UI", 12, "bold"),
            text_color=color,
            anchor="w"
        ).pack(side="left")

        ctk.CTkLabel(
            top,
            text=icono,
            font=("Segoe UI Emoji", 18)
        ).pack(side="right")

        lbl_valor = ctk.CTkLabel(
            inner,
            text=valor,
            font=("Segoe UI", 34, "bold"),
            text_color=COLORS['text_dark'],
            anchor="w"
        )
        lbl_valor.pack(anchor="w", pady=(4, 0))

        return lbl_valor

    def _cargar_stats(self):
        try:
            conn = get_db()
            if not conn:
                return
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM accesos")
            total = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM accesos WHERE estado_acceso = 'aceptado'")
            aceptados = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM accesos WHERE estado_acceso = 'denegado'")
            denegados = cursor.fetchone()[0]
            conn.close()

            self._stat_total.configure(text=str(total))
            self._stat_aceptados.configure(text=str(aceptados))
            self._stat_denegados.configure(text=str(denegados))
        except Exception:
            pass

    # ── Vistas ────────────────────────────────────────────────────────────────

    def show_nuevo_registro(self):
        self.clear_content()
        NuevoRegistroView(self.content_frame)

    def show_informacion_escolar(self):
        self.clear_content()
        vista = InformacionEscolarView(self.content_frame)
        self.content_frame.update()
        vista.cargar_datos()

    def show_pantalla_accesos(self):
        try:
            script_path = os.path.abspath(os.path.join(
                os.path.dirname(__file__), "..", "admin", "biometric_system", "reconocimiento.py"
            ))
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

            if not os.path.exists(script_path):
                raise FileNotFoundError(f"No se encontró: {script_path}")

            subprocess.Popen(
                [sys.executable, script_path],
                cwd=project_root,
                creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
            )
            self.clear_content()
            self._info_card("📹", "Sistema Iniciado",
                            "La cámara de reconocimiento facial se ha abierto en una nueva ventana.",
                            COLORS['primary'])
        except Exception as e:
            self.clear_content()
            self._info_card("⚠️", "Error al iniciar", str(e), COLORS['danger'])

    def _info_card(self, icono, titulo, mensaje, color):
        card = ctk.CTkFrame(
            self.content_frame,
            fg_color=COLORS['card_bg'],
            corner_radius=16,
            border_width=1,
            border_color=COLORS['border']
        )
        card.place(relx=0.5, rely=0.5, anchor="center", width=480, height=260)
        ctk.CTkLabel(card, text=icono, font=("Segoe UI Emoji", 48)).pack(pady=(24, 4))
        ctk.CTkLabel(card, text=titulo, font=("Segoe UI", 20, "bold"), text_color=color).pack()
        ctk.CTkLabel(
            card, text=mensaje,
            font=("Segoe UI", 12),
            text_color=COLORS['text_gray'],
            wraplength=380,
            justify="center"
        ).pack(pady=8)

    def show_historial_accesos(self):
        self.clear_content()
        vista = HistorialAccesosView(self.content_frame)
        self.content_frame.update()
        vista.cargar_datos()

    def logout(self):
        self.app.show_login_view()
