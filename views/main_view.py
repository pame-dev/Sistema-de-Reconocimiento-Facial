# Vista Principal con Menú Lateral
import tkinter as tk
import customtkinter as ctk
import os
import sys
import threading
import time
import cv2
from datetime import datetime
from config import COLORS, SIDEBAR_WIDTH, HEADER_HEIGHT, get_db
from views.nuevo_registro_view import NuevoRegistroView
from views.informacion_escolar_view import InformacionEscolarView
from views.historial_accesos_view import HistorialAccesosView
from PIL import Image, ImageTk

# ── Importar motor de reconocimiento ─────────────────────────────────────────
sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "admin", "biometric_system")
))
from reconocimiento import ReconocerFacial


class MainView:
    """Vista principal con header, menú lateral y área de contenido"""

    def __init__(self, parent, app):
        self.app          = app
        self.menu_visible = False
        self.nav_buttons  = []
        self._active_btn  = None

        # Estado cámara
        self._cam_running = False
        self._cam_thread  = None
        self._cap         = None
        self._engine      = None
        self._cam_photo   = None   # evitar garbage collection

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
        header = ctk.CTkFrame(self.main_frame, fg_color=COLORS['header'],
                              corner_radius=0, height=HEADER_HEIGHT)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        ctk.CTkButton(header, text="☰",
                      font=("Segoe UI", 22, "bold"),
                      fg_color="transparent",
                      hover_color=COLORS['header_hover'],
                      text_color=COLORS['white'],
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
                     text_color=COLORS['white']).pack(side="left")

        ctk.CTkButton(header, text="← Salir",
                      font=("Segoe UI", 12, "bold"),
                      fg_color=COLORS['danger'], hover_color=COLORS['danger_dark'],
                      text_color=COLORS['white'],
                      width=90, height=34, corner_radius=8,
                      command=self.logout).pack(side="right", padx=(0, 12))

        self.lbl_reloj = ctk.CTkLabel(header, text="",
                                       font=("Segoe UI", 12),
                                       text_color=COLORS['white'])
        self.lbl_reloj.pack(side="right", padx=(0, 16))
        self._actualizar_reloj()

    def _actualizar_reloj(self):
        self.lbl_reloj.configure(text=datetime.now().strftime("%d/%m/%Y  %H:%M:%S"))
        self.main_frame.after(1000, self._actualizar_reloj)

    # ── Sidebar ───────────────────────────────────────────────────────────────
    def create_sidebar(self):
        self.sidebar = ctk.CTkFrame(self.body_frame, fg_color=COLORS['sidebar'],
                                    width=SIDEBAR_WIDTH, corner_radius=0)
        self.sidebar.pack_propagate(False)

        mh = ctk.CTkFrame(self.sidebar, fg_color=COLORS['header'],
                           corner_radius=0, height=48)
        mh.pack(fill="x")
        mh.pack_propagate(False)
        ctk.CTkLabel(mh, text="  NAVEGACIÓN",
                     font=("Segoe UI", 11, "bold"),
                     text_color=COLORS['white'], anchor="w").pack(
            fill="both", expand=True, padx=16)

        ctk.CTkLabel(self.sidebar, text="", height=8).pack()

        for icono, texto, cmd in [
            ("🏠", "Inicio",               self.show_home),
            ("➕", "Nuevo Registro",       self.show_nuevo_registro),
            ("📚", "Información Escolar",  self.show_informacion_escolar),
            ("📊", "Historial de Accesos", self.show_historial_accesos),
            ("🔐", "Pantalla de Accesos",  self.show_pantalla_accesos),
        ]:
            self._create_menu_button(icono, texto, cmd)

        ctk.CTkFrame(self.sidebar, fg_color=COLORS['header_hover'],
                     height=1, corner_radius=0).pack(fill="x", padx=16, pady=14)
        ctk.CTkLabel(self.sidebar, text="v1.0.0",
                     font=("Segoe UI", 10),
                     text_color=COLORS['text_gray']).pack(side="bottom", pady=(0, 8))

    def _create_menu_button(self, icono, texto, command):
        btn = ctk.CTkButton(self.sidebar, text=f"  {icono}  {texto}",
                            anchor="w", font=("Segoe UI", 13),
                            fg_color="transparent",
                            hover_color=COLORS['sidebar_hover'],
                            text_color=COLORS['white'],
                            height=44, corner_radius=10)
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
        self.content_frame = ctk.CTkFrame(self.body_frame,
                                           fg_color=COLORS['background'])
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
        self.clear_content()

        outer = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        outer.pack(fill="both", expand=True, padx=30, pady=24)

        stats_row = ctk.CTkFrame(outer, fg_color="transparent")
        stats_row.pack(fill="x", pady=(0, 18))
        stats_row.grid_columnconfigure((0, 1, 2), weight=1, uniform="stat")

        self._stat_total     = self._stat_card(stats_row, "Accesos",     "0", COLORS['primary'], "🔢", 0)
        self._stat_aceptados = self._stat_card(stats_row, "Aceptados", "0", "#27AE60",          "✅", 1)
        self._stat_denegados = self._stat_card(stats_row, "Denegados",   "0", COLORS['danger'],   "❌", 2)
        self._cargar_stats()

        card = ctk.CTkFrame(outer, fg_color=COLORS['card_bg'],
                            corner_radius=18, border_width=1,
                            border_color=COLORS['border'])
        card.pack(fill="both", expand=True)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.place(relx=0.5, rely=0.5, anchor="center")

        try:
            logo_path = os.path.join(os.path.dirname(__file__), "..", "assets", "sentinelSystemIcono.png")
            img = Image.open(logo_path).resize((100, 90), Image.LANCZOS)
            self._home_logo = ctk.CTkImage(light_image=img, dark_image=img, size=(100, 90))
            ctk.CTkLabel(inner, image=self._home_logo, text="").pack(pady=(0, 12))
        except Exception:
            ctk.CTkLabel(inner, text="🔐", font=("Segoe UI Emoji", 56)).pack(pady=(0, 12))

        ctk.CTkLabel(inner, text="Le da la Bienvenida al Sistema",
                     font=("Segoe UI", 24, "bold"),
                     text_color=COLORS['text_dark']).pack()
        ctk.CTkLabel(inner, text="Seleccione una opción del menú para comenzar",
                     font=("Segoe UI", 13),
                     text_color=COLORS['text_gray']).pack(pady=(6, 22))
        ctk.CTkButton(inner, text="➕  Agregar nuevo usuario",
                      fg_color=COLORS['primary'], hover_color=COLORS['primary_dark'],
                      text_color=COLORS['white'],
                      font=("Segoe UI", 13, "bold"),
                      corner_radius=10, height=42, width=260,
                      command=self.show_nuevo_registro).pack()

    def _stat_card(self, parent, titulo, valor, color, icono, col):
        card = ctk.CTkFrame(parent, fg_color=COLORS['card_bg'],
                            corner_radius=14, border_width=1,
                            border_color=COLORS['border'])
        card.grid(row=0, column=col, padx=8, sticky="ew")
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(padx=18, pady=14, fill="x")
        top = ctk.CTkFrame(inner, fg_color="transparent")
        top.pack(fill="x")
        ctk.CTkLabel(top, text=titulo,
                     font=("Segoe UI", 12, "bold"),
                     text_color=color, anchor="w").pack(side="left")
        ctk.CTkLabel(top, text=icono,
                     font=("Segoe UI Emoji", 18)).pack(side="right")
        lbl = ctk.CTkLabel(inner, text=valor,
                           font=("Segoe UI", 34, "bold"),
                           text_color=COLORS['text_dark'], anchor="w")
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
        self.clear_content()
        NuevoRegistroView(self.content_frame)

    def show_informacion_escolar(self):
        self.clear_content()
        vista = InformacionEscolarView(self.content_frame)
        self.content_frame.update()
        vista.cargar_datos()

    def show_historial_accesos(self):
        self.clear_content()
        vista = HistorialAccesosView(self.content_frame)
        self.content_frame.update()
        vista.cargar_datos()

    # ── PANTALLA DE ACCESOS — colores claros ──────────────────────────────────
    def show_pantalla_accesos(self):
        self.clear_content()

        # Fondo blanco / gris claro
        outer = ctk.CTkFrame(self.content_frame, fg_color="#f0f4f8")
        outer.pack(fill="both", expand=True)
        outer.grid_rowconfigure(1, weight=1)
        outer.grid_columnconfigure(0, weight=1)

        # ── Barra superior ────────────────────────────────────────────────────
        bar = ctk.CTkFrame(outer, fg_color="#ffffff",
                           border_color="#d0e4f7", border_width=1,
                           corner_radius=0, height=56)
        bar.grid(row=0, column=0, sticky="ew")
        bar.grid_propagate(False)
        bar.grid_columnconfigure(1, weight=1)

        # Logo + título
        logo_f = ctk.CTkFrame(bar, fg_color="transparent")
        logo_f.grid(row=0, column=0, padx=16, pady=10, sticky="w")
        ctk.CTkLabel(logo_f, text="🛡",
                     font=("Segoe UI Emoji", 22),
                     text_color="#1565c0").pack(side="left", padx=(0, 8))
        ctk.CTkLabel(logo_f, text="Reconocimiento Facial",
                     font=("Segoe UI", 14, "bold"),
                     text_color="#1565c0").pack(side="left")

        # Badges de estado
        mid = ctk.CTkFrame(bar, fg_color="transparent")
        mid.grid(row=0, column=1)

        self._lbl_status = ctk.CTkLabel(mid, text="⬤  Iniciando...",
                                         font=("Segoe UI", 11, "bold"),
                                         text_color="#f59e0b")
        self._lbl_status.pack()

        self._lbl_cam = ctk.CTkLabel(mid, text="⬤  Cámara apagada",
                                      font=("Segoe UI", 10),
                                      text_color="#ef4444")
        self._lbl_cam.pack()

        # Botones
        btns = ctk.CTkFrame(bar, fg_color="transparent")
        btns.grid(row=0, column=2, padx=14, pady=10, sticky="e")

        self._btn_iniciar = ctk.CTkButton(btns, text="▶ Iniciar",
                      fg_color="#16a34a", hover_color="#15803d",
                      text_color="white",
                      font=("Segoe UI", 12, "bold"),
                      width=90, height=32, corner_radius=8,
                      command=self._start_camera)
        self._btn_iniciar.pack(side="left", padx=4)
        self._anim_running = False

        ctk.CTkButton(btns, text="⏹ Detener",
                      fg_color="#dc2626", hover_color="#b91c1c",
                      text_color="white",
                      font=("Segoe UI", 12, "bold"),
                      width=90, height=32, corner_radius=8,
                      command=self._stop_camera).pack(side="left", padx=4)

        ctk.CTkButton(btns, text="⚡  Entrenar",
                      fg_color="#1d4ed8", hover_color="#1e40af",
                      text_color="white",
                      font=("Segoe UI", 12, "bold"),
                      width=90, height=32, corner_radius=8,
                      command=self._train_model).pack(side="left", padx=4)

        # ── Área de cámara ────────────────────────────────────────────────────
        cam_card = ctk.CTkFrame(outer, fg_color="#ffffff",
                                border_color="#bfdbfe", border_width=2,
                                corner_radius=12)
        cam_card.grid(row=1, column=0, sticky="nsew", padx=16, pady=(8, 16))
        cam_card.grid_rowconfigure(0, weight=1)
        cam_card.grid_columnconfigure(0, weight=1)

        self._cam_canvas = tk.Canvas(cam_card, bg="#e8f0fe", highlightthickness=0)
        self._cam_canvas.grid(row=0, column=0, sticky="nsew", padx=3, pady=3)
        self._cam_canvas.bind("<Configure>", lambda e: self._draw_placeholder())

        # Barra inferior info
        info_bar = ctk.CTkFrame(cam_card, fg_color="#f8faff",
                                corner_radius=0, height=30)
        info_bar.grid(row=1, column=0, sticky="ew")
        info_bar.grid_propagate(False)

        self._lbl_resultado = ctk.CTkLabel(info_bar, text="",
                                            font=("Segoe UI", 11, "bold"),
                                            text_color="#16a34a")
        self._lbl_resultado.pack(side="right", padx=14)

        self._lbl_fps = ctk.CTkLabel(info_bar, text="",
                                      font=("Segoe UI", 9),
                                      text_color="#94a3b8")
        self._lbl_fps.pack(side="right", padx=8)

        ctk.CTkLabel(info_bar, text="LBPH  ·  640×480  ·  CLAHE + Bilateral",
                     font=("Segoe UI", 9),
                     text_color="#94a3b8").pack(side="left", padx=14)

        # Iniciar motor
        self._engine = ReconocerFacial()
        self._engine.on_resultado = self._cb_resultado
        self._engine.on_status    = self._cb_status
        threading.Thread(target=self._init_engine, daemon=True).start()

    # ── Motor ─────────────────────────────────────────────────────────────────
    def _init_engine(self):
        ok = self._engine.cargar_modelo()
        if ok:
            n = len(self._engine.nombres)
            self.main_frame.after(0, lambda: self._lbl_status.configure(
                text=f"⬤  Modelo listo · {n} usuarios", text_color="#16a34a"))
        else:
            self.main_frame.after(0, lambda: self._lbl_status.configure(
                text="⬤  Sin modelo — Entrena primero", text_color="#f59e0b"))

    def _train_model(self):
        self._lbl_status.configure(text="⬤  Entrenando...", text_color="#f59e0b")
        def _do():
            ok = self._engine.entrenar()
            if ok:
                n = len(self._engine.nombres)
                self.main_frame.after(0, lambda: self._lbl_status.configure(
                    text=f"⬤  Modelo listo · {n} usuarios", text_color="#16a34a"))
            else:
                self.main_frame.after(0, lambda: self._lbl_status.configure(
                    text="⬤  Error — Sin datos en DB", text_color="#ef4444"))
        threading.Thread(target=_do, daemon=True).start()

    # ── Animación del botón Iniciar ───────────────────────────────────────────
    def _anim_btn(self, step=0):
        """Anima el botón con puntos giratorios mientras inicia."""
        if not self._anim_running:
            return
        frames = ["▷  Iniciando·", "▷  Iniciando··", "▷  Iniciando···", "▷  Iniciando·"]
        try:
            self._btn_iniciar.configure(text=frames[step % 4], fg_color="#d97706")
        except Exception:
            return
        self.main_frame.after(400, self._anim_btn, step + 1)

    # ── Cámara ────────────────────────────────────────────────────────────────
    def _start_camera(self):
        if self._cam_running or not self._engine:
            return

        # Iniciar animación en el botón
        self._anim_running = True
        self._btn_iniciar.configure(state="disabled")
        self._anim_btn()

        self._cap = cv2.VideoCapture(0)
        if not self._cap.isOpened():
            self._lbl_cam.configure(text="⬤  Error: No se pudo abrir cámara",
                                     text_color="#ef4444")
            self._anim_running = False
            self._btn_iniciar.configure(
                text="▶  Iniciar", fg_color="#16a34a", state="normal")
            return
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self._cam_running = True
        self._cam_thread  = threading.Thread(target=self._cam_loop, daemon=True)
        self._cam_thread.start()

        # Detener animación y poner botón en estado "activo"
        self._anim_running = False
        self._btn_iniciar.configure(
            text="● En vivo", fg_color="#15803d",
            hover_color="#166534", state="normal")
        self._lbl_cam.configure(text="⬤  Cámara en línea", text_color="#16a34a")

    def _stop_camera(self):
        self._cam_running  = False
        self._anim_running = False
        if self._cap:
            self._cap.release()
            self._cap = None
        try:
            self._btn_iniciar.configure(
                text="▶  Iniciar", fg_color="#16a34a",
                hover_color="#15803d", state="normal")
            self._lbl_cam.configure(text="⬤  Cámara apagada", text_color="#ef4444")
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

            now  = time.time()
            fps  = 1.0 / max(now - prev, 1e-9)
            prev = now

            self.main_frame.after(0, lambda f=fps: self._lbl_fps.configure(
                text=f"{f:.0f} fps"))

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
            self._cam_photo = photo           # evitar garbage collection
            self._cam_canvas.create_image(0, 0, anchor="nw", image=photo)
        except Exception:
            pass

    def _draw_placeholder(self):
        if self._cam_running:
            return
        try:
            self._cam_canvas.delete("all")
            w = self._cam_canvas.winfo_width()  or 600
            h = self._cam_canvas.winfo_height() or 400

            # Fondo suave
            self._cam_canvas.configure(bg="#e8f0fe")

            # Marco decorativo
            self._cam_canvas.create_rectangle(
                20, 20, w-20, h-20,
                outline="#bfdbfe", width=2, dash=(8, 4))

            # Esquinas
            sz = 20
            for (cx, cy), (dx, dy) in [
                ((20, 20), (1, 1)), ((w-20, 20), (-1, 1)),
                ((20, h-20), (1, -1)), ((w-20, h-20), (-1, -1))
            ]:
                self._cam_canvas.create_line(
                    cx, cy, cx+dx*sz, cy, fill="#1d4ed8", width=3)
                self._cam_canvas.create_line(
                    cx, cy, cx, cy+dy*sz, fill="#1d4ed8", width=3)

            # Icono y texto
            self._cam_canvas.create_text(w//2, h//2 - 22,
                text="🛡  Sentinel System",
                font=("Segoe UI", 18, "bold"), fill="#1d4ed8")
            self._cam_canvas.create_text(w//2, h//2 + 14,
                text="Presiona  ▶ Iniciar  para comenzar",
                font=("Segoe UI", 11), fill="#64748b")
        except Exception:
            pass

    # ── Callbacks ─────────────────────────────────────────────────────────────
    def _cb_resultado(self, nombre, confianza, tipo):
        if tipo == "aceptado":
            txt, color = f"✓  {nombre}  ({confianza:.1f})", "#16a34a"
        else:
            txt, color = f"✕  Desconocido  ({confianza:.1f})", "#dc2626"
        try:
            self.main_frame.after(0, lambda: self._lbl_resultado.configure(
                text=txt, text_color=color))
        except Exception:
            pass

    def _cb_status(self, texto):
        try:
            self.main_frame.after(0, lambda: self._lbl_status.configure(
                text=f"⬤  {texto}", text_color="#1d4ed8"))
        except Exception:
            pass

    # ── Info card ─────────────────────────────────────────────────────────────
    def _info_card(self, icono, titulo, mensaje, color):
        card = ctk.CTkFrame(self.content_frame, fg_color=COLORS['card_bg'],
                            corner_radius=16, border_width=1,
                            border_color=COLORS['border'])
        card.place(relx=0.5, rely=0.5, anchor="center", width=480, height=260)
        ctk.CTkLabel(card, text=icono, font=("Segoe UI Emoji", 48)).pack(pady=(24, 4))
        ctk.CTkLabel(card, text=titulo,
                     font=("Segoe UI", 20, "bold"), text_color=color).pack()
        ctk.CTkLabel(card, text=mensaje,
                     font=("Segoe UI", 12), text_color=COLORS['text_gray'],
                     wraplength=380, justify="center").pack(pady=8)

    # ── Logout ────────────────────────────────────────────────────────────────
    def logout(self):
        self._stop_camera()
        self.app.show_login_view()
