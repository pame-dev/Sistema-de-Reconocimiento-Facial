# Vista Principal con Menú Lateral
import tkinter as tk
import customtkinter as ctk
import os
import sys
import threading
import time
import cv2
from datetime import datetime
from camera import Camera
from config import COLORS, get_colors, toggle_theme, SIDEBAR_WIDTH, HEADER_HEIGHT, get_db
from views.nuevo_registro_view import NuevoRegistroView
from views.informacion_escolar_view import InformacionEscolarView
from views.historial_accesos_view import HistorialAccesosView
from PIL import Image, ImageTk
from tkinter import messagebox

sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "admin", "biometric_system")
))
from reconocimiento import ReconocerFacial

ZOOM_MIN  = 0.7
ZOOM_MAX  = 2.0
ZOOM_STEP = 0.1

from views.font_scale import FontScale


class MainView:
    def __init__(self, parent, app):
        self.app           = app
        self.parent        = parent
        self.menu_visible  = False
        self.nav_buttons   = []
        self._active_btn   = None
        self._vista_actual = None
        self.parent.winfo_toplevel().focus_force()
        self.colors = get_colors()

        self._cam_running  = False
        self._cam_thread   = None
        self._cap          = None
        self._engine       = None
        self._cam_photo    = None
        self._zoom_popover = None

        # Estado pantalla accesos
        self._panel_reset_job = None
        self._borde_job       = None
        self._historial_items = []
        # Temporizador de ausencia de cara (5 s)
        self._sin_cara_job    = None

        self.main_frame = ctk.CTkFrame(parent, fg_color=self.colors['background'])
        self.main_frame.pack(fill="both", expand=True)

        self.create_header()

        self.body_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.body_frame.pack(fill="both", expand=True)

        self.create_sidebar()
        self.create_content_area()
        self.show_home()
        self._bind_zoom_keys()

    # ══════════════════════════════════════════════════════════════════════════
    # ZOOM
    # ══════════════════════════════════════════════════════════════════════════
    def _bind_zoom_keys(self):
        root = self.parent.winfo_toplevel()
        root.bind_all("<Control-plus>",        lambda e: self._zoom(ZOOM_STEP))
        root.bind_all("<Control-equal>",       lambda e: self._zoom(ZOOM_STEP))
        root.bind_all("<Control-Shift-equal>", lambda e: self._zoom(ZOOM_STEP))
        root.bind_all("<Control-KP_Add>",      lambda e: self._zoom(ZOOM_STEP))
        root.bind_all("<Control-minus>",       lambda e: self._zoom(-ZOOM_STEP))
        root.bind_all("<Control-KP_Subtract>", lambda e: self._zoom(-ZOOM_STEP))
        root.bind_all("<Control-0>",           lambda e: self._zoom_reset())

    def _zoom(self, delta):
        nueva = round(FontScale.get() + delta, 2)
        if not (ZOOM_MIN <= nueva <= ZOOM_MAX):
            return
        FontScale.set(nueva)
        self._actualizar_btn_zoom()
        self._recargar_vista()

    def _zoom_reset(self):
        if FontScale.get() == 1.0:
            return
        FontScale.set(1.0)
        self._actualizar_btn_zoom()
        self._recargar_vista()

    def _actualizar_btn_zoom(self):
        pct = round(FontScale.get() * 100)
        try:
            self._btn_zoom.configure(text=f"🔍 {pct}%")
        except Exception:
            pass
        if self._zoom_popover and self._zoom_popover.winfo_exists():
            try:
                self._zoom_slider.set(pct)
                self._zoom_pct_lbl.configure(text=f"{pct}%")
            except Exception:
                pass

    def _recargar_vista(self):
        vistas = {
            "home":             self.show_home,
            "nuevo_registro":   self.show_nuevo_registro,
            "info_escolar":     self.show_informacion_escolar,
            "historial":        self.show_historial_accesos,
            "pantalla_accesos": self.show_pantalla_accesos,
        }
        vistas.get(self._vista_actual, self.show_home)()

    # ── Popover zoom ──────────────────────────────────────────────────────────
    def _toggle_zoom_popover(self):
        if self._zoom_popover and self._zoom_popover.winfo_exists():
            self._zoom_popover.destroy()
            self._zoom_popover = None
            return

        btn = self._btn_zoom
        x   = btn.winfo_rootx()
        y   = btn.winfo_rooty() + btn.winfo_height() + 6

        pop = tk.Toplevel(self.main_frame)
        pop.overrideredirect(True)
        pop.geometry(f"230x170+{x}+{y}")
        pop.configure(bg="#1e3a5f")
        pop.attributes("-topmost", True)
        self._zoom_popover = pop
        pop.bind("<FocusOut>", lambda e: self._cerrar_popover())

        inner = tk.Frame(pop, bg="#1e3a5f")
        inner.pack(fill="both", expand=True, padx=2, pady=2)

        tk.Label(inner, text="Tamaño de interfaz", bg="#1e3a5f", fg="#93c5fd",
                 font=("Segoe UI", 10, "bold")).pack(pady=(10, 2))
        self._zoom_pct_lbl = tk.Label(inner, text=f"{round(FontScale.get()*100)}%",
            bg="#1e3a5f", fg="#ffffff", font=("Segoe UI", 26, "bold"))
        self._zoom_pct_lbl.pack()
        self._zoom_slider = tk.Scale(inner,
            from_=int(ZOOM_MIN*100), to=int(ZOOM_MAX*100),
            orient="horizontal", resolution=10,
            bg="#1e3a5f", fg="#93c5fd", troughcolor="#1d4ed8",
            highlightthickness=0, bd=0, sliderrelief="flat",
            activebackground="#60a5fa", length=200, showvalue=False,
            command=self._zoom_desde_slider)
        self._zoom_slider.set(round(FontScale.get()*100))
        self._zoom_slider.pack(padx=12, pady=(2, 6))
        btn_row = tk.Frame(inner, bg="#1e3a5f")
        btn_row.pack()
        estilo = dict(bg="#1d4ed8", fg="white", relief="flat",
                      font=("Segoe UI", 14, "bold"),
                      activebackground="#3b82f6", activeforeground="white",
                      cursor="hand2", bd=0, padx=14, pady=3, width=2)
        tk.Button(btn_row, text="−", command=lambda: self._zoom(-ZOOM_STEP), **estilo).pack(side="left", padx=5)
        tk.Button(btn_row, text="↺", command=self._zoom_reset, **estilo).pack(side="left", padx=5)
        tk.Button(btn_row, text="+", command=lambda: self._zoom(ZOOM_STEP), **estilo).pack(side="left", padx=5)
        pop.after(100, pop.focus_set)

    def _cerrar_popover(self):
        try:
            if self._zoom_popover and self._zoom_popover.winfo_exists():
                self._zoom_popover.destroy()
        except Exception:
            pass
        self._zoom_popover = None

    def _zoom_desde_slider(self, val):
        nueva = round(int(val)/100, 2)
        if nueva == FontScale.get():
            return
        FontScale.set(nueva)
        pct = round(FontScale.get()*100)
        try:
            self._zoom_pct_lbl.configure(text=f"{pct}%")
            self._btn_zoom.configure(text=f"🔍 {pct}%")
        except Exception:
            pass
        if hasattr(self, "_slider_job"):
            try:
                self.main_frame.after_cancel(self._slider_job)
            except Exception:
                pass
        self._slider_job = self.main_frame.after(300, self._recargar_vista)

    # ══════════════════════════════════════════════════════════════════════════
    # HEADER
    # ══════════════════════════════════════════════════════════════════════════
    def create_header(self):
        c = self.colors
        header = ctk.CTkFrame(self.main_frame, fg_color=c['header'],
                              corner_radius=0, height=HEADER_HEIGHT)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        ctk.CTkButton(header, text="☰", font=("Segoe UI", 22, "bold"),
                      fg_color="transparent", hover_color=COLORS['header_hover'],
                      text_color=c['white'], width=52, height=44, corner_radius=8,
                      command=self.toggle_menu).pack(side="left", padx=(8, 0))

        title_frame = ctk.CTkFrame(header, fg_color="transparent")
        title_frame.pack(side="left", padx=12)
        try:
            logo_path = os.path.join(os.path.dirname(__file__), "..", "assets", "sentinelSystemIcono.png")
            img = Image.open(logo_path).resize((32, 32), Image.LANCZOS)
            self._header_logo = ctk.CTkImage(light_image=img, dark_image=img, size=(32, 32))
            ctk.CTkLabel(title_frame, image=self._header_logo, text="").pack(side="left", padx=(0, 8))
        except Exception:
            pass
        ctk.CTkLabel(title_frame, text="Sentinel System — Panel Principal",
                     font=("Segoe UI", 18, "bold"), text_color=c['white']).pack(side="left")

        ctk.CTkButton(header, text="← Salir", font=("Segoe UI", 12, "bold"),
                      fg_color=c['danger'], hover_color=COLORS['danger_dark'],
                      text_color=c['white'], width=90, height=34, corner_radius=8,
                      command=self.logout).pack(side="right", padx=(0, 12))

        self.lbl_reloj = ctk.CTkLabel(header, text="", font=("Segoe UI", 12),
                                       text_color=c['white'])
        self.lbl_reloj.pack(side="right", padx=(0, 16))
        self._actualizar_reloj()

        self._btn_zoom = ctk.CTkButton(header,
            text=f"🔍 {round(FontScale.get()*100)}%",
            font=("Segoe UI", 11), fg_color="#1d4ed8", hover_color="#1e40af",
            text_color="white", width=82, height=28, corner_radius=8,
            command=self._toggle_zoom_popover)
        self._btn_zoom.pack(side="right", padx=(0, 8))

        ctk.CTkButton(header, text="🌐", font=("Segoe UI", 14),
                      fg_color="transparent", hover_color=COLORS['header_hover'],
                      text_color=c['white'], width=40, height=34, corner_radius=8,
                      command=self.traducir_app).pack(side="right", padx=(0, 6))

        ctk.CTkButton(header, text="🌙", font=("Segoe UI", 14),
                      fg_color="transparent", hover_color=COLORS['header_hover'],
                      text_color=c['white'], width=40, height=34, corner_radius=8,
                      command=self.modo_oscuro).pack(side="right", padx=(0, 6))

    def _actualizar_reloj(self):
        self.lbl_reloj.configure(text=datetime.now().strftime("%d/%m/%Y  %H:%M:%S"))
        self.main_frame.after(1000, self._actualizar_reloj)

    # ══════════════════════════════════════════════════════════════════════════
    # SIDEBAR
    # ══════════════════════════════════════════════════════════════════════════
    def create_sidebar(self):
        c = self.colors
        self.sidebar = ctk.CTkFrame(self.body_frame, fg_color=c['sidebar'],
                                    width=SIDEBAR_WIDTH, corner_radius=0)
        self.sidebar.pack_propagate(False)

        mh = ctk.CTkFrame(self.sidebar, fg_color=c['header'],
                           corner_radius=0, height=48)
        mh.pack(fill="x")
        mh.pack_propagate(False)
        ctk.CTkLabel(mh, text="  NAVEGACIÓN", font=("Segoe UI", 11, "bold"),
                     text_color=c['white'], anchor="w").pack(fill="both", expand=True, padx=16)

        ctk.CTkLabel(self.sidebar, text="", height=8).pack()
        for icono, texto, cmd in [
            ("🏠", "Inicio",               self.show_home),
            ("➕", "Nuevo Registro",       self.show_nuevo_registro),
            ("📚", "Información Escolar",  self.show_informacion_escolar),
            ("📊", "Historial de Accesos", self.show_historial_accesos),
            ("🔐", "Pantalla de Accesos",  self.show_pantalla_accesos),
        ]:
            self._create_menu_button(icono, texto, cmd)

        ctk.CTkFrame(self.sidebar, fg_color=c['header_hover'],
                     height=1, corner_radius=0).pack(fill="x", padx=16, pady=14)
        ctk.CTkLabel(self.sidebar, text="v1.0.0", font=("Segoe UI", 10),
                     text_color=c['text_gray']).pack(side="bottom", pady=(0, 8))

    def _create_menu_button(self, icono, texto, command):
        c = self.colors
        btn = ctk.CTkButton(self.sidebar, text=f"  {icono}  {texto}",
                            anchor="w", font=("Segoe UI", 13),
                            fg_color="transparent", hover_color=COLORS['sidebar_hover'],
                            text_color=c['white'], height=44, corner_radius=10)
        btn.configure(command=lambda cmd=command: self._nav(cmd, btn))
        btn.pack(fill="x", padx=10, pady=2)
        self.nav_buttons.append(btn)

    def _nav(self, command, btn):
        if self._active_btn and self._active_btn != btn:
            self._active_btn.configure(fg_color="transparent")
        btn.configure(fg_color=self.colors['sidebar_hover'])
        self._active_btn = btn
        self._close_sidebar()
        command()

    def _close_sidebar(self):
        if self.menu_visible:
            self.sidebar.pack_forget()
            self.menu_visible = False

    # ══════════════════════════════════════════════════════════════════════════
    # CONTENT
    # ══════════════════════════════════════════════════════════════════════════
    def create_content_area(self):
        self.content_frame = ctk.CTkFrame(self.body_frame, fg_color=self.colors['background'])
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
        self._stop_camera()
        for w in self.content_frame.winfo_children():
            w.destroy()

    # ══════════════════════════════════════════════════════════════════════════
    # HOME
    # ══════════════════════════════════════════════════════════════════════════
    def show_home(self):
        self._vista_actual = "home"
        self.clear_content()
        c = self.colors

        outer = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        outer.pack(fill="both", expand=True, padx=30, pady=24)

        stats_row = ctk.CTkFrame(outer, fg_color="transparent")
        stats_row.pack(fill="x", pady=(0, 18))
        stats_row.grid_columnconfigure((0, 1, 2), weight=1, uniform="stat")

        self._stat_total     = self._stat_card(stats_row, "Accesos",   "0", COLORS['primary'], "🔢", 0)
        self._stat_aceptados = self._stat_card(stats_row, "Aceptados", "0", "#27AE60",         "✅", 1)
        self._stat_denegados = self._stat_card(stats_row, "Denegados", "0", COLORS['danger'],  "❌", 2)
        self._cargar_stats()

        card = ctk.CTkFrame(outer, fg_color=c['card_bg'], corner_radius=18,
                            border_width=1, border_color=COLORS['border'])
        card.pack(fill="both", expand=True)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.place(relx=0.5, rely=0.5, anchor="center")

        try:
            logo_path = os.path.join(os.path.dirname(__file__), "..", "assets", "sentinelSystemIcono.png")
            img = Image.open(logo_path).resize((90, 90), Image.LANCZOS)
            self._home_logo = ctk.CTkImage(light_image=img, dark_image=img, size=(100, 90))
            ctk.CTkLabel(inner, image=self._home_logo, text="").pack(pady=(0, 12))
        except Exception:
            ctk.CTkLabel(inner, text="🔐", font=FontScale.fb(48)).pack(pady=(0, 12))

        ctk.CTkLabel(inner, text="Le da la Bienvenida al Sistema",
                     font=FontScale.fb(24), text_color=c['text_dark']).pack()
        ctk.CTkLabel(inner, text="Seleccione una opción del menú para comenzar",
                     font=FontScale.f(13), text_color=c['text_gray']).pack(pady=(6, 22))
        ctk.CTkButton(inner, text="➕  Agregar nuevo usuario",
                      fg_color=c['primary'], hover_color=COLORS['primary_dark'],
                      text_color="#ffffff", font=FontScale.fb(13),
                      corner_radius=10, height=42, width=260,
                      command=self.show_nuevo_registro).pack()

    def _stat_card(self, parent, titulo, valor, color, icono, col):
        c = self.colors
        card = ctk.CTkFrame(parent, fg_color=c['card_bg'], corner_radius=14,
                            border_width=1, border_color=COLORS['border'])
        card.grid(row=0, column=col, padx=8, sticky="ew")
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(padx=18, pady=14, fill="x")
        top = ctk.CTkFrame(inner, fg_color="transparent")
        top.pack(fill="x")
        ctk.CTkLabel(top, text=titulo, font=FontScale.fb(12),
                     text_color=color, anchor="w").pack(side="left")
        ctk.CTkLabel(top, text=icono, font=FontScale.f(18)).pack(side="right")
        lbl = ctk.CTkLabel(inner, text=valor, font=FontScale.fb(34),
                           text_color=c['text_dark'], anchor="w")
        lbl.pack(anchor="w", pady=(4, 0))
        return lbl

    def _cargar_stats(self):
        try:
            conn = get_db()
            if not conn:
                return
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM accesos")
            total = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM accesos WHERE estado_acceso='aceptado'")
            aceptados = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM accesos WHERE estado_acceso='denegado'")
            denegados = cur.fetchone()[0]
            conn.close()
            self._stat_total.configure(text=str(total))
            self._stat_aceptados.configure(text=str(aceptados))
            self._stat_denegados.configure(text=str(denegados))
        except Exception:
            pass

    # ══════════════════════════════════════════════════════════════════════════
    # OTRAS VISTAS
    # ══════════════════════════════════════════════════════════════════════════
    def show_nuevo_registro(self):
        self._stop_camera()  # liberar cámara antes de abrir registro
        self._vista_actual = "nuevo_registro"
        self.clear_content()
        NuevoRegistroView(self.content_frame)

    def show_informacion_escolar(self):
        self._vista_actual = "info_escolar"
        self.clear_content()
        vista = InformacionEscolarView(self.content_frame)
        self.content_frame.update()
        vista.cargar_datos()

    def show_historial_accesos(self):
        self._vista_actual = "historial"
        self.clear_content()
        vista = HistorialAccesosView(self.content_frame)
        self.content_frame.update()
        vista.cargar_datos()

    # ══════════════════════════════════════════════════════════════════════════
    # PANTALLA DE ACCESOS
    # ══════════════════════════════════════════════════════════════════════════
    def show_pantalla_accesos(self):
        self._vista_actual    = "pantalla_accesos"
        self._panel_reset_job = None
        self._borde_job       = None
        self._sin_cara_job    = None
        self._historial_items = []
        self.clear_content()
        c = self.colors

        outer = ctk.CTkFrame(self.content_frame, fg_color=c['background'])
        outer.pack(fill="both", expand=True)
        outer.grid_rowconfigure(1, weight=1)
        outer.grid_columnconfigure(0, weight=1)

        # ── Barra superior ────────────────────────────────────────────────────
        bar = ctk.CTkFrame(outer, fg_color=c['bar_bg'],
                           border_color=c['bar_border'], border_width=1,
                           corner_radius=0, height=52)
        bar.grid(row=0, column=0, sticky="ew")
        bar.grid_propagate(False)

        logo_f = ctk.CTkFrame(bar, fg_color="transparent")
        logo_f.pack(side="left", padx=16, pady=8)
        ctk.CTkLabel(logo_f, text="🛡", font=("Segoe UI Emoji", 20),
                     text_color=c['info']).pack(side="left", padx=(0, 8))
        ctk.CTkLabel(logo_f, text="Control de Accesos",
                     font=("Segoe UI", 14, "bold"),
                     text_color=c['info']).pack(side="left")

        self._btn_iniciar = ctk.CTkButton(
            bar, text="▶  Iniciar",
            fg_color="#16a34a", hover_color="#15803d",
            text_color="white", font=("Segoe UI", 12, "bold"),
            width=100, height=32, corner_radius=8,
            command=self._toggle_camera)
        self._btn_iniciar.pack(side="left", padx=12)
        self._anim_running = False

        self._lbl_cam = ctk.CTkLabel(
            bar, text="⬤  Cargando modelo...",
            font=("Segoe UI", 10), text_color=c['accent'])
        self._lbl_cam.pack(side="right", padx=16)

        # ── Cuerpo ────────────────────────────────────────────────────────────
        body = ctk.CTkFrame(outer, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=12, pady=(6, 12))
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=2)

        # ── Panel cámara ──────────────────────────────────────────────────────
        self._cam_card = ctk.CTkFrame(body, fg_color=c['card_bg'],
                                       border_color=c['cam_border'], border_width=3,
                                       corner_radius=14)
        self._cam_card.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        self._cam_card.grid_rowconfigure(0, weight=1)
        self._cam_card.grid_columnconfigure(0, weight=1)

        self._cam_canvas = tk.Canvas(self._cam_card, bg=c['cam_bg'], highlightthickness=0)
        self._cam_canvas.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
        self._cam_canvas.bind("<Configure>", lambda e: self._draw_placeholder())

        # ── Panel información derecho ─────────────────────────────────────────
        info_col = ctk.CTkFrame(body, fg_color="transparent")
        info_col.grid(row=0, column=1, sticky="nsew")
        info_col.grid_rowconfigure(0, weight=1)
        info_col.grid_columnconfigure(0, weight=1)

        self._user_card = ctk.CTkFrame(info_col, fg_color=c['card_bg'],
                                        border_color=c['border'], border_width=1,
                                        corner_radius=14)
        self._user_card.grid(row=0, column=0, sticky="nsew")
        self._construir_panel_espera()

        # Motor
        self._engine = ReconocerFacial()
        self._engine.on_resultado = self._cb_resultado
        self._engine.on_status    = self._cb_status
        self._engine.on_sin_cara  = self._cb_sin_cara
        threading.Thread(target=self._init_engine, daemon=True).start()

    # ── Panel espera ──────────────────────────────────────────────────────────
    def _construir_panel_espera(self):
        for w in self._user_card.winfo_children():
            w.destroy()
        inner = ctk.CTkFrame(self._user_card, fg_color="transparent")
        inner.place(relx=0.5, rely=0.5, anchor="center")
        ctk.CTkLabel(inner, text="👤", font=("Segoe UI Emoji", 52),
                     text_color="#cbd5e1").pack(pady=(0, 10))
        ctk.CTkLabel(inner, text="Esperando reconocimiento",
                     font=("Segoe UI", 14, "bold"),
                     text_color=self.colors['text_gray']).pack()
        ctk.CTkLabel(inner, text="Colócate frente a la cámara",
                     font=("Segoe UI", 10),
                     text_color=self.colors['text_light']).pack(pady=(6, 0))

    # ── Panel usuario reconocido ──────────────────────────────────────────────
    def _construir_panel_usuario(self, nombre, datos_bd, tipo):
        for w in self._user_card.winfo_children():
            w.destroy()

        c           = self.colors
        es_aceptado = (tipo == "aceptado")
        color_tipo  = "#16a34a" if es_aceptado else "#dc2626"
        bg_top      = "#16a34a" if es_aceptado else "#dc2626"
        icono_tipo  = "✓  ACCESO PERMITIDO" if es_aceptado else "✗  ACCESO DENEGADO"
        rol         = datos_bd.get('rol', 'usuario')

        ICONOS_ROL = {"alumno": "🎓", "maestro": "📚", "personal": "🏢"}
        LABEL_ROL  = {"alumno": "Estudiante", "maestro": "Docente", "personal": "Personal Escolar"}
        icono_rol  = ICONOS_ROL.get(rol, "👤")
        label_rol  = LABEL_ROL.get(rol, rol.capitalize())

        # ── Franja superior ────────────────────────────────────────────────────
        top_bar = ctk.CTkFrame(self._user_card, fg_color=bg_top,
                               corner_radius=0, height=50)
        top_bar.pack(fill="x")
        top_bar.pack_propagate(False)
        ctk.CTkLabel(top_bar, text=icono_tipo,
                     font=("Segoe UI", 15, "bold"),
                     text_color="#ffffff").pack(expand=True)

        # ── Scroll con info ────────────────────────────────────────────────────
        scroll = ctk.CTkScrollableFrame(self._user_card, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=14, pady=10)

        def sep():
            ctk.CTkFrame(scroll, fg_color=COLORS['border'],
                         height=1, corner_radius=0).pack(fill="x", pady=6)

        def fila(label_txt, valor, icono_f=""):
            if not valor or valor == '—':
                return
            row = ctk.CTkFrame(scroll, fg_color="transparent")
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=label_txt,
                         font=("Segoe UI", 10),
                         text_color=c['text_gray'],
                         width=100, anchor="w").pack(side="left")
            ctk.CTkLabel(row, text=str(valor),
                         font=("Segoe UI", 10, "bold"),
                         text_color=c['text_dark'],
                         anchor="w", wraplength=150).pack(side="left", fill="x", expand=True)

        # Icono de rol + nombre
        ctk.CTkLabel(scroll, text=icono_rol,
                     font=("Segoe UI Emoji", 40)).pack(pady=(4, 2))

        nombre_display = datos_bd.get('nombre_display', nombre)
        ctk.CTkLabel(scroll, text=nombre_display,
                     font=("Segoe UI", 15, "bold"),
                     text_color=c['text_dark'],
                     wraplength=210, justify="center").pack()

        # Badge de rol
        badge = ctk.CTkFrame(scroll, fg_color=color_tipo, corner_radius=8)
        badge.pack(pady=(4, 6))
        ctk.CTkLabel(badge, text=f"  {label_rol}  ",
                     font=("Segoe UI", 10, "bold"),
                     text_color="#ffffff").pack(padx=4, pady=3)

        sep()

        # ── Datos personales ───────────────────────────────────────────────────
        fila("Matrícula",  datos_bd.get('matricula'))
        fila("Teléfono",   datos_bd.get('telefono'))
        fila("Correo",     datos_bd.get('correo'))

        # ── Datos específicos por rol ──────────────────────────────────────────
        if rol == 'alumno':
            sep()
            ctk.CTkLabel(scroll, text="Información académica",
                         font=("Segoe UI", 10, "bold"),
                         text_color=color_tipo).pack(anchor="w", pady=(0, 4))
            fila("Facultad",  datos_bd.get('facultad'))
            fila("Carrera",   datos_bd.get('carrera'))
            fila("Grado",     datos_bd.get('grado'))
            fila("Grupo",     datos_bd.get('grupo'))

        elif rol == 'maestro':
            sep()
            ctk.CTkLabel(scroll, text="Información docente",
                         font=("Segoe UI", 10, "bold"),
                         text_color=color_tipo).pack(anchor="w", pady=(0, 4))
            fila("Materia",        datos_bd.get('materia'))
            fila("Grado imparte",  datos_bd.get('grado'))

        elif rol == 'personal':
            sep()
            ctk.CTkLabel(scroll, text="Información laboral",
                         font=("Segoe UI", 10, "bold"),
                         text_color=color_tipo).pack(anchor="w", pady=(0, 4))
            fila("Puesto",  datos_bd.get('puesto'))
            fila("Área",    datos_bd.get('area'))

        sep()
        ctk.CTkLabel(scroll, text=f"🕐  {datetime.now().strftime('%H:%M:%S')}",
                     font=("Segoe UI", 11),
                     text_color=c['text_gray']).pack()


    # ── Animación borde de cámara ─────────────────────────────────────────────
    def _animar_borde(self, color_hex, pasos=6):
        if self._borde_job:
            try:
                self.main_frame.after_cancel(self._borde_job)
            except Exception:
                pass
        c = self.colors

        def _tick(n):
            if n <= 0:
                try:
                    self._cam_card.configure(border_color=c['cam_border'])
                except Exception:
                    pass
                return
            try:
                self._cam_card.configure(
                    border_color=color_hex if n % 2 == 0 else c['cam_border'])
            except Exception:
                return
            self._borde_job = self.main_frame.after(180, _tick, n - 1)

        _tick(pasos)

    # ── Reset panel cuando no hay cara ────────────────────────────────────────
    def _programar_reset_por_ausencia(self):
        if self._sin_cara_job:
            try:
                self.main_frame.after_cancel(self._sin_cara_job)
            except Exception:
                pass
        # Solo resetear después de 3 segundos sin cara
        self._sin_cara_job = self.main_frame.after(5000, self._limpiar_panel_resultado)

    def _cancelar_reset_por_ausencia(self):
        if self._sin_cara_job:
            try:
                self.main_frame.after_cancel(self._sin_cara_job)
            except Exception:
                pass
            self._sin_cara_job = None

    def _limpiar_panel_resultado(self):
        try:
            self._construir_panel_espera()
            self._cam_card.configure(border_color=self.colors['cam_border'])
        except Exception:
            pass

    # ══════════════════════════════════════════════════════════════════════════
    # MOTOR
    # ══════════════════════════════════════════════════════════════════════════
    def _init_engine(self):
        ok = self._engine.cargar_o_reentrenar()
        n  = len(self._engine.nombres) if ok else 0
        try:
            if ok:
                self.main_frame.after(0, lambda: self._lbl_cam.configure(
                    text=f"⬤  Modelo listo · {n} usuarios",
                    text_color=self.colors['primary']))
            else:
                self.main_frame.after(0, lambda: self._lbl_cam.configure(
                    text="⬤  Sin datos — registra usuarios primero",
                    text_color=self.colors['accent']))
        except Exception:
            pass

    # ══════════════════════════════════════════════════════════════════════════
    # CÁMARA
    # ══════════════════════════════════════════════════════════════════════════
    def _toggle_camera(self):
        if self._cam_running:
            self._stop_camera()
        else:
            self._start_camera()

    def _start_camera(self):
        if self._cam_running or not self._engine:
            return
        self._anim_running = True
        self._btn_iniciar.configure(state="disabled")
        self._anim_btn()
        # Evita quedar atascado en "cargando": siempre permitimos
        # que la barra de progreso llegue a 100% para abrir la cámara.
        self._anim_cam_lista = True
        self._mostrar_anim_camara()

    def _abrir_camara(self):
        try:
            self._cap = Camera()
            self._cap.start()

        except Exception:
            self._lbl_cam.configure(
                text="⬤  Error: No se pudo abrir cámara",
                text_color=self.colors['danger']
            )
            self._anim_running = False
            self._btn_iniciar.configure(
                text="▶  Iniciar", fg_color="#16a34a", state="normal"
            )
            return

        self._cam_running = True
        self._cam_thread  = threading.Thread(target=self._cam_loop, daemon=True)
        self._cam_thread.start()

        self._anim_running = False
        self._btn_iniciar.configure(
            text="⏹  Detener",
            fg_color="#dc2626",
            hover_color="#b91c1c",
            state="normal"
        )

        self._lbl_cam.configure(
            text="⬤  Cámara en línea",
            text_color=self.colors['primary']
        )

    def _stop_camera(self):
        self._cam_running  = False
        self._anim_running = False
        if self._cap:
            try:
                if self._cap:
                    self._cap.stop()
                    self._cap = None
            except Exception:
                pass
            self._cap = None
        try:
            self._btn_iniciar.configure(text="▶  Iniciar", fg_color="#16a34a",
                                         hover_color="#15803d", state="normal")
            self._lbl_cam.configure(text="⬤  Cámara apagada",
                                     text_color=self.colors['danger'])
        except Exception:
            pass
        try:
            self.main_frame.after(100, self._draw_placeholder)
        except Exception:
            pass

    def _cam_loop(self):
        while self._cam_running:
            if not self._cap:
                break
            try:
                frame = self._cap.read()
                if frame is None:
                    continue
            except Exception:
                break

            # Recortar frame al centro — solo el área del rostro
            h_f, w_f = frame.shape[:2]
            margen_x = int(w_f * 0.15)
            margen_y = int(h_f * 0.10)
            frame = frame[margen_y:h_f - margen_y, margen_x:w_f - margen_x]

            frame = self._engine.procesar_frame(frame)
            rgb   = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img   = Image.fromarray(rgb)
            try:
                cw = self._cam_canvas.winfo_width()  or 640
                ch = self._cam_canvas.winfo_height() or 480
            except Exception:
                break
            img   = img.resize((cw, ch), Image.BILINEAR)
            photo = ImageTk.PhotoImage(img)
            self.main_frame.after(0, self._show_frame, photo)
        self._cam_running = False

    def _show_frame(self, photo):
        try:
            self._cam_canvas.delete("all")
            self._cam_photo = photo
            self._cam_canvas.create_image(0, 0, anchor="nw", image=photo)
        except Exception:
            pass

    def _draw_placeholder(self):
        if self._cam_running:
            return
        c = self.colors
        try:
            self._cam_canvas.delete("all")
            w = self._cam_canvas.winfo_width()  or 600
            h = self._cam_canvas.winfo_height() or 400
            self._cam_canvas.configure(bg=c['cam_bg'])
            self._cam_canvas.create_rectangle(20, 20, w-20, h-20,
                outline=c['cam_border'], width=2, dash=(8, 4))
            sz = 20
            for (cx2, cy2), (dx, dy) in [
                ((20, 20), (1, 1)), ((w-20, 20), (-1, 1)),
                ((20, h-20), (1, -1)), ((w-20, h-20), (-1, -1))
            ]:
                self._cam_canvas.create_line(cx2, cy2, cx2+dx*sz, cy2, fill=c['info'], width=3)
                self._cam_canvas.create_line(cx2, cy2, cx2, cy2+dy*sz, fill=c['info'], width=3)
            try:
                if not hasattr(self, "_placeholder_logo") or self._placeholder_logo is None:
                    logo_path = os.path.join(os.path.dirname(__file__), "..", "assets", "sentinelSystemIcono.png")
                    img = Image.open(logo_path).resize((100, 100), Image.LANCZOS)
                    self._placeholder_logo = ImageTk.PhotoImage(img)
                self._cam_canvas.create_image(w//2, h//2 - 28, image=self._placeholder_logo)
                self._cam_canvas.create_text(w//2, h//2 + 24,
                    text="Sentinel System", font=("Segoe UI", 22, "bold"), fill=c['info'])
            except Exception:
                self._cam_canvas.create_text(w//2, h//2 - 22,
                    text="🛡  Sentinel System", font=("Segoe UI", 22, "bold"), fill=c['info'])
            self._cam_canvas.create_text(w//2, h//2 + 48,
                text="Presiona  ▶ Iniciar  para comenzar",
                font=("Segoe UI", 16), fill=c['text_gray'])
        except Exception:
            pass

    # ══════════════════════════════════════════════════════════════════════════
    # CALLBACKS
    # ══════════════════════════════════════════════════════════════════════════
    def _cb_resultado(self, nombre, confianza, tipo):
        """Llamado por el motor cuando reconoce (o deniega) a alguien."""
        es_aceptado = (tipo == "aceptado")
        color_borde = "#16a34a" if es_aceptado else "#dc2626"

        def _actualizar():
            try:
                # Cancelar cualquier reset pendiente — acaba de aparecer una cara
                self._cancelar_reset_por_ausencia()
                self._animar_borde(color_borde)

                # Beep (solo Windows)
                try:
                    import winsound
                    winsound.Beep(1000, 200) if es_aceptado else winsound.Beep(400, 500)
                except Exception:
                    pass

                datos_bd = self._get_datos_usuario(nombre)
                self._construir_panel_usuario(nombre, datos_bd, tipo)

            except Exception as e:
                print(f"Error en _cb_resultado: {e}")

        self.main_frame.after(0, _actualizar)

    def _cb_status(self, texto):
        try:
            self.main_frame.after(0, lambda: self._lbl_cam.configure(
                text=f"⬤  {texto}", text_color=self.colors['info']))
        except Exception:
            pass

    def _cb_sin_cara(self):
        """Solo resetear el panel si el último acceso fue aceptado."""
        self.main_frame.after(0, self._programar_reset_por_ausencia)

    # ── Obtener datos completos del usuario desde la BD ───────────────────────
    def _get_datos_usuario(self, nombre_completo):
        """Busca al usuario por nombre completo y devuelve dict con todos sus datos."""
        datos = {'rol': 'usuario', 'nombre_display': nombre_completo}
        try:
            conn = get_db()
            if not conn:
                return datos
            cur = conn.cursor()

            # El nombre en self.nombres es "NOMBRE PATERNO [MATERNO]" (en mayúsculas)
            # Intentar coincidencia exacta primero, luego por primer nombre
            cur.execute("""
                SELECT u.idUsuario,
                       u.nombreUsuario, u.apellidoPaternoUsuario, u.apellidoMaternoUsuario,
                       u.matriculaUsuario, u.telefonoUsuario, u.correoUsuario, u.rolUsuario
                FROM usuarios u
                WHERE UPPER(u.nombreUsuario || ' ' || COALESCE(u.apellidoPaternoUsuario,''))
                      = UPPER(?)
                LIMIT 1
            """, (nombre_completo.strip(),))
            row = cur.fetchone()

            # Si no coincide exacto, buscar por los primeros dos tokens
            if not row:
                partes = nombre_completo.strip().split()
                primer = partes[0] if partes else nombre_completo
                cur.execute("""
                    SELECT u.idUsuario,
                           u.nombreUsuario, u.apellidoPaternoUsuario, u.apellidoMaternoUsuario,
                           u.matriculaUsuario, u.telefonoUsuario, u.correoUsuario, u.rolUsuario
                    FROM usuarios u
                    WHERE UPPER(u.nombreUsuario) = UPPER(?)
                    LIMIT 1
                """, (primer,))
                row = cur.fetchone()

            if not row:
                conn.close()
                return datos

            user_id = row[0]
            rol     = row[7] or 'usuario'
            nombre  = row[1] or ''
            paterno = row[2] or ''
            materno = row[3] or ''

            datos = {
                'id':             user_id,
                'nombre':         nombre,
                'paterno':        paterno,
                'materno':        materno,
                'nombre_display': f"{nombre} {paterno} {materno}".strip(),
                'matricula':      row[4] or '—',
                'telefono':       row[5] or '—',
                'correo':         row[6] or '—',
                'rol':            rol,
            }

            if rol == 'alumno':
                cur.execute("""
                    SELECT facultadAlumno, carreraAlumno, gradoAlumno, grupoAlumno
                    FROM alumnos WHERE fkIdUsuario = ?
                """, (user_id,))
                r = cur.fetchone()
                if r:
                    datos.update({
                        'facultad': r[0] or '—',
                        'carrera':  r[1] or '—',
                        'grado':    r[2] or '—',
                        'grupo':    r[3] or '—',
                    })

            elif rol == 'maestro':
                cur.execute("""
                    SELECT gradoImpartidoMaestro, materiaImpartidaMaestro
                    FROM maestros WHERE fkIdUsuario = ?
                """, (user_id,))
                r = cur.fetchone()
                if r:
                    datos.update({
                        'grado':   r[0] or '—',
                        'materia': r[1] or '—',
                    })

            elif rol == 'personal':
                cur.execute("""
                    SELECT puestoPersonalEscolar, areaPersonalEscolar
                    FROM personal_escolar WHERE fkIdUsuario = ?
                """, (user_id,))
                r = cur.fetchone()
                if r:
                    datos.update({
                        'puesto': r[0] or '—',
                        'area':   r[1] or '—',
                    })

            conn.close()
        except Exception as e:
            print(f"Error _get_datos_usuario: {e}")
        return datos


    # ══════════════════════════════════════════════════════════════════════════
    # ANIMACIÓN INICIO CÁMARA
    # ══════════════════════════════════════════════════════════════════════════
    def _anim_btn(self, step=0):
        if not self._anim_running:
            return
        frames = ["⏳ Iniciando", "⏳ Iniciando.", "⏳ Iniciando..", "⏳ Iniciando..."]
        try:
            self._btn_iniciar.configure(text=frames[step % len(frames)], fg_color="#f59e0b")
        except Exception:
            return
        self.main_frame.after(400, self._anim_btn, step + 1)

    def _mostrar_anim_camara(self):
        self._anim_cam_activa  = True
        self._anim_cam_radio   = 44
        self._anim_cam_fase    = 0
        self._anim_cam_scan    = 0.0
        self._anim_cam_dots    = 0
        self._anim_cam_prog    = 0.0
        self._anim_cam_dots_str = "   "
        self._tick_anim_cam_ring()
        self._tick_anim_cam_dots()
        self._tick_anim_cam_prog()

    def _tick_anim_cam_ring(self):
        if not getattr(self, '_anim_cam_activa', False):
            return
        if self._anim_cam_fase == 0:
            self._anim_cam_radio = min(50, self._anim_cam_radio + 1)
            if self._anim_cam_radio >= 50: self._anim_cam_fase = 1
        else:
            self._anim_cam_radio = max(42, self._anim_cam_radio - 1)
            if self._anim_cam_radio <= 42: self._anim_cam_fase = 0
        self._anim_cam_scan = (self._anim_cam_scan + 0.06) % 1.0
        self._dibujar_anim_camara()
        self.main_frame.after(40, self._tick_anim_cam_ring)

    def _tick_anim_cam_dots(self):
        if not getattr(self, '_anim_cam_activa', False):
            return
        puntos = ["   ", "•  ", "•• ", "•••"]
        self._anim_cam_dots_str = puntos[self._anim_cam_dots % 4]
        self._anim_cam_dots += 1
        self.main_frame.after(400, self._tick_anim_cam_dots)

    def _tick_anim_cam_prog(self):
        if not getattr(self, '_anim_cam_activa', False):
            return
        target = 1.0
        delta  = (target - self._anim_cam_prog) * 0.06
        self._anim_cam_prog = min(target, self._anim_cam_prog + max(delta, 0.003))
        self._dibujar_anim_camara()
        if self._anim_cam_prog < 0.999:
            self.main_frame.after(60, self._tick_anim_cam_prog)
        else:
            self._anim_cam_activa = False
            self.main_frame.after(200, self._abrir_camara)

    def _dibujar_anim_camara(self):
        try:
            cv2canvas = self._cam_canvas
            cv2canvas.delete("all")
            c  = self.colors
            w  = cv2canvas.winfo_width()  or 640
            h  = cv2canvas.winfo_height() or 480
            cx, cy = w // 2, h // 2 - 40
            color  = c['info']

            r = self._anim_cam_radio
            cv2canvas.create_oval(cx-r, cy-r, cx+r, cy+r, outline=color, width=2)
            cv2canvas.create_rectangle(cx-22, cy-14, cx+22, cy+14,
                                       outline=color, width=2, fill="")
            cv2canvas.create_oval(cx-9, cy-9, cx+9, cy+9, outline=color, width=1.5, fill="")
            cv2canvas.create_oval(cx-4, cy-4, cx+4, cy+4, fill=color, outline="")
            cv2canvas.create_rectangle(cx+14, cy-14, cx+22, cy-8, outline=color, width=1.5, fill="")
            scan_y = cy - 12 + int(self._anim_cam_scan * 24)
            cv2canvas.create_line(cx-18, scan_y, cx+18, scan_y, fill=color, width=1)

            dots = self._anim_cam_dots_str
            cv2canvas.create_text(cx, cy + 60,
                text=f"Iniciando cámara {dots}",
                font=("Segoe UI", 14, "bold"), fill=color)

            bar_w = 220
            bar_x = cx - bar_w // 2
            bar_y = cy + 90
            cv2canvas.create_rectangle(bar_x, bar_y, bar_x+bar_w, bar_y+6,
                fill=c['cam_bg'], outline=c['cam_border'], width=1)
            if self._anim_cam_prog > 0:
                cv2canvas.create_rectangle(bar_x, bar_y,
                    bar_x + int(bar_w * self._anim_cam_prog),
                    bar_y + 6, fill=color, outline="")
            cv2canvas.create_text(cx, bar_y + 22,
                text="Preparando reconocimiento facial...",
                font=("Segoe UI", 10), fill=c['text_gray'])
        except Exception:
            pass

    # ══════════════════════════════════════════════════════════════════════════
    # MODO OSCURO / MISC
    # ══════════════════════════════════════════════════════════════════════════
    def modo_oscuro(self):
        toggle_theme()
        self.colors = get_colors()
        self._recargar_vista()
        self.main_frame.configure(fg_color=self.colors['background'])
        self.content_frame.configure(fg_color=self.colors['background'])

    def traducir_app(self):
        messagebox.showinfo("En desarrollo", "La función de traducción está en desarrollo 🚧")

    def logout(self):
        if messagebox.askyesno("Confirmar salida", "¿Estás seguro de que deseas salir?"):
            self._stop_camera()
            self.app.show_login_view()