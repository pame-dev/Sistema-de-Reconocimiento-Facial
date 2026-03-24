# Vista Principal con Menú Lateral
import tkinter as tk
import customtkinter as ctk
import os
import sys
import threading
import time
import cv2
from datetime import datetime
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
    """Vista principal con header, menú lateral y área de contenido"""

    def __init__(self, parent, app):
        self.app          = app
        self.parent       = parent
        self.menu_visible = False
        self.nav_buttons  = []
        self._active_btn  = None
        self._vista_actual = None
        self.parent.winfo_toplevel().focus_force()
        self.colors = get_colors()

        self._cam_running  = False
        self._cam_thread   = None
        self._cap          = None
        self._engine       = None
        self._cam_photo    = None
        self._zoom_popover = None

        self.main_frame = ctk.CTkFrame(parent, fg_color=self.colors['background'])
        self.main_frame.pack(fill="both", expand=True)

        self.create_header()

        self.body_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.body_frame.pack(fill="both", expand=True)

        self.create_sidebar()
        self.create_content_area()
        self.show_home()
        self._bind_zoom_keys()

    # ── Zoom ──────────────────────────────────────────────────────────────────
    def _bind_zoom_keys(self):
        root = self.parent.winfo_toplevel()
        root.bind_all("<Control-plus>",        lambda e: self._zoom(ZOOM_STEP))
        root.bind_all("<Control-equal>",       lambda e: self._zoom(ZOOM_STEP))
        root.bind_all("<Control-Shift-equal>", lambda e: self._zoom(ZOOM_STEP))
        root.bind_all("<Control-KP_Add>",      lambda e: self._zoom(ZOOM_STEP))
        root.bind_all("<Control-minus>",       lambda e: self._zoom(-ZOOM_STEP))
        root.bind_all("<Control-KP_Subtract>", lambda e: self._zoom(-ZOOM_STEP))
        root.bind_all("<Control-0>",           lambda e: self._zoom_reset())

    def _zoom(self, delta: float):
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

    def _zoom_rueda(self, event):
        self._zoom(ZOOM_STEP if event.delta > 0 else -ZOOM_STEP)

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
        fn = vistas.get(self._vista_actual, self.show_home)
        fn()

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

    # ── Header ────────────────────────────────────────────────────────────────
    def create_header(self):
        c = self.colors
        header = ctk.CTkFrame(self.main_frame, fg_color=c['header'],
                              corner_radius=0, height=HEADER_HEIGHT)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        ctk.CTkButton(header, text="☰",
                      font=("Segoe UI", 22, "bold"),
                      fg_color="transparent",
                      hover_color=COLORS['header_hover'],
                      text_color=c['white'],
                      width=52, height=44, corner_radius=8,
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
                     font=("Segoe UI", 18, "bold"),
                     text_color=c['white']).pack(side="left")

        ctk.CTkButton(header, text="← Salir",
                      font=("Segoe UI", 12, "bold"),
                      fg_color=c['danger'], hover_color=COLORS['danger_dark'],
                      text_color=c['white'],
                      width=90, height=34, corner_radius=8,
                      command=self.logout).pack(side="right", padx=(0, 12))

        self.lbl_reloj = ctk.CTkLabel(header, text="",
                                       font=("Segoe UI", 12),
                                       text_color=c['white'])
        self.lbl_reloj.pack(side="right", padx=(0, 16))
        self._actualizar_reloj()

        self._btn_zoom = ctk.CTkButton(header,
            text=f"🔍 {round(FontScale.get()*100)}%",
            font=("Segoe UI", 11),
            fg_color="#1d4ed8", hover_color="#1e40af",
            text_color="white",
            width=82, height=28, corner_radius=8,
            command=self._toggle_zoom_popover)
        self._btn_zoom.pack(side="right", padx=(0, 8))

        ctk.CTkButton(header, text="🌐",
                      font=("Segoe UI", 14),
                      fg_color="transparent", hover_color=COLORS['header_hover'],
                      text_color=c['white'],
                      width=40, height=34, corner_radius=8,
                      command=self.traducir_app).pack(side="right", padx=(0, 6))

        ctk.CTkButton(header, text="🌙",
                      font=("Segoe UI", 14),
                      fg_color="transparent", hover_color=COLORS['header_hover'],
                      text_color=c['white'],
                      width=40, height=34, corner_radius=8,
                      command=self.modo_oscuro).pack(side="right", padx=(0, 6))

    def _actualizar_reloj(self):
        self.lbl_reloj.configure(text=datetime.now().strftime("%d/%m/%Y  %H:%M:%S"))
        self.main_frame.after(1000, self._actualizar_reloj)

    # ── Sidebar ───────────────────────────────────────────────────────────────
    def create_sidebar(self):
        c = self.colors
        self.sidebar = ctk.CTkFrame(self.body_frame, fg_color=c['sidebar'],
                                    width=SIDEBAR_WIDTH, corner_radius=0)
        self.sidebar.pack_propagate(False)

        mh = ctk.CTkFrame(self.sidebar, fg_color=c['header'],
                           corner_radius=0, height=48)
        mh.pack(fill="x")
        mh.pack_propagate(False)
        ctk.CTkLabel(mh, text="  NAVEGACIÓN",
                     font=("Segoe UI", 11, "bold"),
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
        ctk.CTkLabel(self.sidebar, text="v1.0.0",
                     font=("Segoe UI", 10),
                     text_color=c['text_gray']).pack(side="bottom", pady=(0, 8))

    def _create_menu_button(self, icono, texto, command):
        c = self.colors
        btn = ctk.CTkButton(self.sidebar, text=f"  {icono}  {texto}",
                            anchor="w", font=("Segoe UI", 13),
                            fg_color="transparent",
                            hover_color=COLORS['sidebar_hover'],
                            text_color=c['white'],
                            height=44, corner_radius=10)
        btn.configure(command=lambda c=command: self._nav(c, btn))
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

    # ── Content ───────────────────────────────────────────────────────────────
    def create_content_area(self):
        self.content_frame = ctk.CTkFrame(self.body_frame,
                                           fg_color=self.colors['background'])
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

    # ── Home ──────────────────────────────────────────────────────────────────
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

        card = ctk.CTkFrame(outer, fg_color=c['card_bg'],
                            corner_radius=18, border_width=1,
                            border_color=COLORS['border'])
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
                      text_color="#ffffff",
                      font=FontScale.fb(13),
                      corner_radius=10, height=42, width=260,
                      command=self.show_nuevo_registro).pack()

    def _stat_card(self, parent, titulo, valor, color, icono, col):
        c = self.colors
        card = ctk.CTkFrame(parent, fg_color=c['card_bg'],
                            corner_radius=14, border_width=1,
                            border_color=COLORS['border'])
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

    # ── Otras vistas ──────────────────────────────────────────────────────────
    def show_nuevo_registro(self):
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

    # ── Pantalla de Accesos ───────────────────────────────────────────────────
    def show_pantalla_accesos(self):
        self._vista_actual = "pantalla_accesos"
        self.clear_content()
        c = self.colors   # ← siempre lee el tema actual

        outer = ctk.CTkFrame(self.content_frame, fg_color=c['background'])
        outer.pack(fill="both", expand=True)
        outer.grid_rowconfigure(1, weight=1)
        outer.grid_columnconfigure(0, weight=1)

        # ── Barra superior ────────────────────────────────────────────────────
        bar = ctk.CTkFrame(outer,
                           fg_color=c['bar_bg'],
                           border_color=c['bar_border'],
                           border_width=1,
                           corner_radius=0, height=56)
        bar.grid(row=0, column=0, sticky="ew")
        bar.grid_propagate(False)
        bar.grid_columnconfigure(3, weight=1)

        logo_f = ctk.CTkFrame(bar, fg_color="transparent")
        logo_f.grid(row=0, column=0, padx=16, pady=10, sticky="w")
        ctk.CTkLabel(logo_f, text="🛡",
                     font=FontScale.f(22),
                     text_color=c['info']).pack(side="left", padx=(0, 8))
        ctk.CTkLabel(logo_f, text="Reconocimiento Facial",
                     font=FontScale.fb(14),
                     text_color=c['info']).pack(side="left")

        btns = ctk.CTkFrame(bar, fg_color="transparent")
        btns.grid(row=0, column=1, padx=(4, 0), pady=10, sticky="w")

        self._btn_iniciar = ctk.CTkButton(btns, text="▶ Iniciar",
                  fg_color="#16a34a", hover_color="#15803d",
                  text_color="white", font=FontScale.fb(12),
                  width=90, height=32, corner_radius=8,
                  command=self._toggle_camera)
        self._btn_iniciar.pack(side="left", padx=4)
        self._anim_running = False

        mid = ctk.CTkFrame(bar, fg_color="transparent")
        mid.grid(row=0, column=2, padx=(14, 0), pady=8, sticky="w")
        self._lbl_cam = ctk.CTkLabel(mid, text="⬤  Cámara apagada",
                                      font=FontScale.f(10),
                                      text_color=c['danger'])
        self._lbl_cam.pack()

        # ── Tarjeta de cámara ─────────────────────────────────────────────────
        cam_card = ctk.CTkFrame(outer,
                                fg_color=c['card_bg'],
                                border_color=c['cam_border'],
                                border_width=2,
                                corner_radius=12)
        cam_card.grid(row=1, column=0, sticky="nsew", padx=16, pady=(8, 16))
        cam_card.grid_rowconfigure(0, weight=1)
        cam_card.grid_columnconfigure(0, weight=1)

        self._cam_canvas = tk.Canvas(cam_card,
                                     bg=c['cam_bg'],
                                     highlightthickness=0)
        self._cam_canvas.grid(row=0, column=0, sticky="nsew", padx=3, pady=3)
        self._cam_canvas.bind("<Configure>", lambda e: self._draw_placeholder())

        # ── Info bar inferior ─────────────────────────────────────────────────
        info_bar = ctk.CTkFrame(cam_card,
                                fg_color=c['info_bar_bg'],
                                corner_radius=0, height=30)
        info_bar.grid(row=1, column=0, sticky="ew")
        info_bar.grid_propagate(False)

        self._lbl_resultado = ctk.CTkLabel(info_bar, text="",
                                            font=FontScale.fb(11),
                                            text_color=c['primary'])
        self._lbl_resultado.pack(side="right", padx=14)
        self._lbl_fps = ctk.CTkLabel(info_bar, text="",
                                      font=FontScale.f(9),
                                      text_color=c['text_gray'])
        self._lbl_fps.pack(side="right", padx=8)
        ctk.CTkLabel(info_bar, text="LBPH  ·  640×480  ·  CLAHE + Bilateral",
                     font=FontScale.f(9), text_color=c['text_gray']).pack(side="left", padx=14)

        self._engine = ReconocerFacial()
        self._engine.on_resultado = self._cb_resultado
        self._engine.on_status    = self._cb_status
        threading.Thread(target=self._init_engine, daemon=True).start()

    # ── Motor / Cámara ────────────────────────────────────────────────────────
    def _init_engine(self):
        ok = self._engine.cargar_o_reentrenar() 
        n  = len(self._engine.nombres) if ok else 0
        try:
            if ok and self._lbl_cam.winfo_exists():
                self.main_frame.after(0, lambda: self._lbl_cam.configure(
                    text=f"⬤  Modelo listo · {n} usuarios",
                    text_color=self.colors['primary']))
            elif not ok and self._lbl_cam.winfo_exists():
                self.main_frame.after(0, lambda: self._lbl_cam.configure(
                    text="⬤  Sin modelo — Entrena primero",
                    text_color=self.colors['accent']))
        except Exception:
            pass

    def _anim_btn(self, step=0):
        if not self._anim_running:
            return
        frames = ["⏳ Iniciando", "⏳ Iniciando.", "⏳ Iniciando..", "⏳ Iniciando..."]
        try:
            self._btn_iniciar.configure(text=frames[step % len(frames)], fg_color="#f59e0b")
        except Exception:
            return
        self.main_frame.after(400, self._anim_btn, step + 1)

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
        # Iniciar cámara en background mientras se muestra la animación
        self._anim_cam_lista = False
        self._mostrar_anim_camara()
        threading.Thread(target=self._preinit_camara, daemon=True).start()

    def _preinit_camara(self):
        """Abre VideoCapture en background durante la animación."""
        try:
            cap = cv2.VideoCapture(0)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self._cap_preinit = cap if cap.isOpened() else None
        except Exception:
            self._cap_preinit = None
        self._anim_cam_lista = True

    def _abrir_camara(self):
        # Reutilizar la cámara ya abierta durante la animación
        if getattr(self, '_cap_preinit', None) and self._cap_preinit.isOpened():
            self._cap = self._cap_preinit
            self._cap_preinit = None
        else:
            self._cap = cv2.VideoCapture(0)
            if not self._cap.isOpened():
                self._lbl_cam.configure(text="⬤  Error: No se pudo abrir cámara",
                                        text_color=self.colors['danger'])
                self._anim_running = False
                self._btn_iniciar.configure(text="▶ Iniciar",
                                            fg_color="#16a34a", state="normal")
                return
            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        self._cam_running = True
        self._cam_thread  = threading.Thread(target=self._cam_loop, daemon=True)
        self._cam_thread.start()
        self._anim_running = False
        self._btn_iniciar.configure(text="⏹ Detener",
                                    fg_color="#dc2626", hover_color="#b91c1c",
                                    state="normal")
        self._lbl_cam.configure(text="⬤  Cámara en línea",
                                text_color=self.colors['primary'])
        self._cap = cv2.VideoCapture(0)
        if not self._cap.isOpened():
            self._lbl_cam.configure(text="⬤  Error: No se pudo abrir cámara",
                                     text_color=self.colors['danger'])
            self._anim_running = False
            self._btn_iniciar.configure(text="▶ Iniciar", fg_color="#16a34a", state="normal")
            return

        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self._cam_running = True
        self._cam_thread  = threading.Thread(target=self._cam_loop, daemon=True)
        self._cam_thread.start()
        self._anim_running = False
        self._btn_iniciar.configure(text="⏹ Detener",
                                     fg_color="#dc2626", hover_color="#b91c1c",
                                     state="normal")
        self._lbl_cam.configure(text="⬤  Cámara en línea",
                                 text_color=self.colors['primary'])

    def _stop_camera(self):
        self._cam_running  = False
        self._anim_running = False
        if self._cap:
            self._cap.release()
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
        prev = time.time()
        while self._cam_running:
            if not self._cap or not self._cap.isOpened():
                break
            ret, frame = self._cap.read()
            if not ret:
                break
            frame = self._engine.procesar_frame(frame)
            now   = time.time()
            fps   = 1.0 / max(now - prev, 1e-9)
            prev  = now
            self.main_frame.after(0, lambda f=fps: self._lbl_fps.configure(text=f"{f:.0f} fps"))
            rgb   = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img   = Image.fromarray(rgb)
            cw    = self._cam_canvas.winfo_width()  or 640
            ch    = self._cam_canvas.winfo_height() or 480
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

            # Marco punteado
            self._cam_canvas.create_rectangle(20, 20, w-20, h-20,
                outline=c['cam_border'], width=2, dash=(8, 4))

            # Esquinas decorativas
            sz = 20
            corner_color = c['info']
            for (cx, cy), (dx, dy) in [
                ((20, 20), (1, 1)), ((w-20, 20), (-1, 1)),
                ((20, h-20), (1, -1)), ((w-20, h-20), (-1, -1))
            ]:
                self._cam_canvas.create_line(cx, cy, cx+dx*sz, cy,
                    fill=corner_color, width=3)
                self._cam_canvas.create_line(cx, cy, cx, cy+dy*sz,
                    fill=corner_color, width=3)

            # Logo
            try:
                if not hasattr(self, "_placeholder_logo") or self._placeholder_logo is None:
                    logo_path = os.path.join(os.path.dirname(__file__), "..", "assets", "sentinelSystemIcono.png")
                    img = Image.open(logo_path).resize((100, 100), Image.LANCZOS)
                    self._placeholder_logo = ImageTk.PhotoImage(img)
                self._cam_canvas.create_image(w//2, h//2 - 28, image=self._placeholder_logo)
                self._cam_canvas.create_text(w//2, h//2 + 24,
                    text="Sentinel System",
                    font=("Segoe UI", 22, "bold"),
                    fill=c['info'])
            except Exception:
                self._cam_canvas.create_text(w//2, h//2 - 22,
                    text="🛡  Sentinel System",
                    font=("Segoe UI", 22, "bold"),
                    fill=c['info'])

            self._cam_canvas.create_text(w//2, h//2 + 48,
                text="Presiona  ▶ Iniciar  para comenzar",
                font=("Segoe UI", 16),
                fill=c['text_gray'])
        except Exception:
            pass

    # ── Callbacks ─────────────────────────────────────────────────────────────
    def _cb_resultado(self, nombre, confianza, tipo):
        txt   = f"✓  {nombre}  ({confianza:.1f})" if tipo == "aceptado" else f"✕  Desconocido  ({confianza:.1f})"
        color = self.colors['primary'] if tipo == "aceptado" else self.colors['danger']
        try:
            self.main_frame.after(0, lambda: self._lbl_resultado.configure(
                text=txt, text_color=color))
        except Exception:
            pass

    def _cb_status(self, texto):
        try:
            self.main_frame.after(0, lambda: self._lbl_cam.configure(
                text=f"⬤  {texto}", text_color=self.colors['info']))
        except Exception:
            pass

    # ── Modo oscuro — SIN reconstruir MainView ────────────────────────────────
    def modo_oscuro(self):
        toggle_theme()
        # Actualizar colores locales
        self.colors = get_colors()
        # Recargar solo la vista activa (no toda la MainView)
        self._recargar_vista()
        # Actualizar el fondo del frame principal y el content_frame
        self.main_frame.configure(fg_color=self.colors['background'])
        self.content_frame.configure(fg_color=self.colors['background'])

    def _mostrar_anim_camara(self):
        """Muestra animación de carga sobre el canvas mientras abre la cámara."""
        c = self.colors
        self._anim_cam_activa = True
        self._anim_cam_radio  = 44
        self._anim_cam_fase   = 0
        self._anim_cam_scan   = 0.0
        self._anim_cam_dots   = 0
        self._anim_cam_prog   = 0.0
        self._anim_cam_lista  = False
        self._tick_anim_cam_ring()
        self._tick_anim_cam_dots()
        self._tick_anim_cam_prog()

    def _tick_anim_cam_ring(self):
        if not getattr(self, '_anim_cam_activa', False):
            return
        if self._anim_cam_fase == 0:
            self._anim_cam_radio = min(50, self._anim_cam_radio + 1)
            if self._anim_cam_radio >= 50:
                self._anim_cam_fase = 1
        else:
            self._anim_cam_radio = max(42, self._anim_cam_radio - 1)
            if self._anim_cam_radio <= 42:
                self._anim_cam_fase = 0
        self._anim_cam_scan = (self._anim_cam_scan + 0.06) % 1.0
        self._dibujar_anim_camara()
        self.main_frame.after(40, self._tick_anim_cam_ring)

    def _tick_anim_cam_dots(self):
        if not getattr(self, '_anim_cam_activa', False):
            return
        puntos = ["   ", "•  ", "•• ", "•••"]
        self._anim_cam_dots_str = puntos[self._anim_cam_dots % 4]
        self._anim_cam_dots += 1
        self._dibujar_anim_camara()
        self.main_frame.after(400, self._tick_anim_cam_dots)

    def _tick_anim_cam_prog(self):
        if not getattr(self, '_anim_cam_activa', False):
            return
        target = 0.88 if not getattr(self, '_anim_cam_lista', False) else 1.0
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
            cv = self._cam_canvas
            cv.delete("all")
            c  = self.colors
            w  = cv.winfo_width()  or 640
            h  = cv.winfo_height() or 480
            cx, cy = w // 2, h // 2 - 40

            color = self.colors['info']

            # Anillo pulsante
            r = self._anim_cam_radio
            cv.create_oval(cx-r, cy-r, cx+r, cy+r, outline=color, width=2)

            # Cuerpo de cámara
            cv.create_rectangle(cx-22, cy-14, cx+22, cy+14,
                                outline=color, width=2, fill="")
            cv.create_oval(cx-9, cy-9, cx+9, cy+9,
                        outline=color, width=1.5, fill="")
            cv.create_oval(cx-4, cy-4, cx+4, cy+4,
                        fill=color, outline="")
            cv.create_rectangle(cx+14, cy-14, cx+22, cy-8,
                                outline=color, width=1.5, fill="")

            # Línea de escaneo
            scan_y = cy - 12 + int(self._anim_cam_scan * 24)
            cv.create_line(cx-18, scan_y, cx+18, scan_y, fill=color, width=1)

            # Texto
            dots = getattr(self, '_anim_cam_dots_str', '   ')
            cv.create_text(cx, cy + 60,
                        text=f"Iniciando cámara {dots}",
                        font=("Segoe UI", 14, "bold"),
                        fill=color)

            # Barra de progreso
            bar_w  = 220
            bar_h  = 6
            bar_x  = cx - bar_w // 2
            bar_y  = cy + 90
            prog   = self._anim_cam_prog
            cv.create_rectangle(bar_x, bar_y, bar_x + bar_w, bar_y + bar_h,
                                fill=c['cam_bg'], outline=c['cam_border'], width=1)
            if prog > 0:
                cv.create_rectangle(bar_x, bar_y,
                                    bar_x + int(bar_w * prog), bar_y + bar_h,
                                    fill=color, outline="")

            cv.create_text(cx, bar_y + 22,
                        text="Preparando captura biométrica...",
                        font=("Segoe UI", 10),
                        fill=c['text_gray'])
        except Exception:
            pass

    # ── Logout ────────────────────────────────────────────────────────────────
    def logout(self):
        if messagebox.askyesno("Confirmar salida", "¿Estás seguro de que deseas salir?"):
            self._stop_camera()
            self.app.show_login_view()

    def traducir_app(self):
        messagebox.showinfo("En desarrollo", "La función de traducción está en desarrollo 🚧")