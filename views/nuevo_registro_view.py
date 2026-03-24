# views/nuevo_registro_view.py
import tkinter as tk
from tkinter import messagebox, ttk
import customtkinter as ctk
import cv2
from PIL import Image, ImageTk
import os
import time
from datetime import datetime
import sys
import threading
from views.font_scale import FontScale

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import COLORS, get_colors, toggle_theme, get_db
from database.queries import (
    sp_insertar_usuario,
    sp_insertar_alumno,
    sp_insertar_maestro,
    sp_insertar_personal,
    sp_insertar_biometria,
)

# ── Configuración de roles ────────────────────────────────────────────────────
ROL_CONFIG = {
    "alumno":   {"icono": "🎓", "titulo": "Estudiante", "desc": " ",  "color": "#4A90D9"},
    "maestro":  {"icono": "📚", "titulo": "Docente",    "desc": " ",  "color": "#27AE60"},
    "personal": {"icono": "🏢", "titulo": "Personal",   "desc": "",   "color": "#E67E22"},
}

CAMPOS_POR_ROL = {
    "alumno":   [("Grado:",             "gradoAlumno",              True),
                 ("Grupo:",             "grupoAlumno",              True),
                 ("Facultad:",          "facultadAlumno",           True),
                 ("Carrera:",           "carreraAlumno",            True)],
    "maestro":  [("Grado que imparte:", "gradoImpartidoMaestro",    True),
                 ("Materia:",           "materiaImpartidaMaestro",  True)],
    "personal": [("Puesto:",            "puestoPersonalEscolar",    True),
                 ("Área:",              "areaPersonalEscolar",      True)],
}

CAMPOS_COMUNES = [
    ("Nombre:",           "nombreUsuario",         True),
    ("Apellido Paterno:", "apellidoPaternoUsuario", True),
    ("Apellido Materno:", "apellidoMaternoUsuario", False),
    ("Matrícula:",        "matriculaUsuario",       False),
    ("Teléfono:",         "telefonoUsuario",        True),
    ("Correo:",           "correoUsuario",          True),
]

# ── Posturas ──────────────────────────────────────────────────────────────────
POSTURAS = [
    {
        "id":          "frontal",
        "titulo":      "Frontal",
        "instruccion": "Mira directo a la cámara\ncon la cabeza recta",
        "imagen":      "assets/posturas/postura_frontal.png",
        "icono":       "😐",
        "fotos":       60,
    },
    {
        "id":          "izquierda",
        "titulo":      "Girado a la izquierda",
        "instruccion": "Gira la cabeza ligeramente\nhacia tu izquierda (~15°)",
        "imagen":      "assets/posturas/postura_izquierda.png",
        "icono":       "😶",
        "fotos":       60,
    },
    {
        "id":          "derecha",
        "titulo":      "Girado a la derecha",
        "instruccion": "Gira la cabeza ligeramente\nhacia tu derecha (~15°)",
        "imagen":      "assets/posturas/postura_derecha.png",
        "icono":       "😶",
        "fotos":       60,
    },
    {
        "id":          "perfil_izq",
        "titulo":      "Perfil izquierdo",
        "instruccion": "Gira la cabeza completamente\nhacia tu izquierda (~60°)",
        "imagen":      "assets/posturas/postura_perfil_izq.png",
        "icono":       "🙂",
        "fotos":       60,
    },
    {
        "id":          "perfil_der",
        "titulo":      "Perfil derecho",
        "instruccion": "Gira la cabeza completamente\nhacia tu derecha (~60°)",
        "imagen":      "assets/posturas/postura_perfil_der.png",
        "icono":       "🙂",
        "fotos":       60,
    }
]

TOTAL_FOTOS = sum(p["fotos"] for p in POSTURAS)   # 360

# Cuántos frames consecutivos con cara antes de empezar a capturar
FRAMES_ESTABLE = 8
# Delay entre capturas (segundos) — más bajo = más rápido
CAPTURE_DELAY  = 0.04   # ~25 fotos/seg máx


class NuevoRegistroView:
    def __init__(self, parent):
        self.colors = get_colors()
        self.parent    = parent
        self.container = ctk.CTkFrame(parent, fg_color=self.colors['background'])
        self.container.pack(fill="both", expand=True, padx=30, pady=30)

        self.camara     = None
        self.capturando = False
        self.fotos_temp = []
        self.rol_actual = None
        self.entries    = {}

        self.postura_idx          = 0
        self.fotos_postura        = 0
        self.capturando_rafaga    = False
        self.posturas_completadas = []

        # Auto-capture state
        self._auto_activo      = False
        self._frames_con_cara  = 0
        self._ultima_captura   = 0.0
        self._countdown        = 0        # cuenta regresiva antes de arrancar
        self._countdown_job    = None
        self._guardando        = False

        self.detector = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        self.detector_frontal = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        self.detector_alt = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_alt2.xml'
        )
        self.detector_perfil = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_profileface.xml'
        )
        self._detectores_por_postura = {
            "frontal":     [self.detector_frontal],
            "izquierda":   [self.detector_alt, self.detector_frontal],
            "derecha":     [self.detector_alt, self.detector_frontal],
            "perfil_izq":  [self.detector_perfil],   #
            "perfil_der":  [self.detector_perfil]
        }

        self.modo_retomar_fotos = False
        self.user_id_existente  = None

        self._mostrar_seleccion_rol()

    # ═════════════════════════════════════════════════════════════════════════
    # PANTALLA 1 — Selección de rol
    # ═════════════════════════════════════════════════════════════════════════
    def _mostrar_seleccion_rol(self):
        self._limpiar_container()
        outer = ctk.CTkFrame(self.container, fg_color="transparent")
        outer.pack(fill="both", expand=True)

        ctk.CTkLabel(outer, text="📝 Nuevo Registro de Usuario",
                     font=("Segoe UI", 22, "bold"),
                     text_color=self.colors['text_dark']).pack(pady=(20, 4))
        ctk.CTkLabel(outer, text="Selecciona el tipo de usuario que deseas registrar",
                     font=("Segoe UI", 12),
                     text_color=self.colors['text_gray']).pack(pady=(0, 16))

        cards_frame = ctk.CTkFrame(outer, fg_color="transparent")
        cards_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        for i in range(3):
            cards_frame.grid_columnconfigure(i, weight=1, uniform="rol")
        cards_frame.grid_rowconfigure(0, weight=1)

        for idx, (rol_key, cfg) in enumerate(ROL_CONFIG.items()):
            self._crear_tarjeta_responsive(cards_frame, rol_key, cfg, col=idx)

    def _crear_tarjeta_responsive(self, parent, rol_key, cfg, col):
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
                     font=("Segoe UI Emoji", 110)).grid(row=0, column=0, pady=(28, 6))

        info = ctk.CTkFrame(card, fg_color="transparent")
        info.grid(row=1, column=0, sticky="ew", padx=16)
        ctk.CTkLabel(info, text=cfg["titulo"], font=("Segoe UI", 30, "bold"),
                     text_color=color, wraplength=160, justify="center").pack()
        ctk.CTkLabel(info, text=cfg["desc"], font=("Segoe UI", 11),
                     text_color=self.colors['text_gray'],
                     wraplength=160, justify="center").pack(pady=(4, 0))

        ctk.CTkButton(card, text="✓ Seleccionar",
                      fg_color=color, hover_color=self._darken(color),
                      text_color=self.colors['white'],
                      font=("Segoe UI", 12, "bold"),
                      corner_radius=10, height=38,
                      command=lambda r=rol_key: self._seleccionar_rol(r),
                      ).grid(row=2, column=0, padx=20, pady=(12, 22), sticky="ew")

        for w in (outer, card):
            w.bind("<Button-1>", lambda e, r=rol_key: self._seleccionar_rol(r))

    @staticmethod
    def _darken(hex_color, amount=30):
        h = hex_color.lstrip('#')
        r, g, b = (int(h[i:i+2], 16) for i in (0, 2, 4))
        return f"#{max(0,r-amount):02x}{max(0,g-amount):02x}{max(0,b-amount):02x}"

    def _seleccionar_rol(self, rol_key):
        self.rol_actual = rol_key
        self._mostrar_formulario()

    # ═════════════════════════════════════════════════════════════════════════
    # PANTALLA 2 — Formulario
    # ═════════════════════════════════════════════════════════════════════════
    def _mostrar_formulario(self):
        self._limpiar_container()
        self.entries = {}
        cfg   = ROL_CONFIG[self.rol_actual]
        color = cfg["color"]

        header = ctk.CTkFrame(self.container, fg_color="transparent")
        header.pack(fill="x", pady=(0, 12))
        ctk.CTkButton(header, text="← Regresar",
                      fg_color="transparent", hover_color=COLORS['content_bg'],
                      text_color=color, font=("Segoe UI", 11, "bold"),
                      command=self._mostrar_seleccion_rol).pack(side="left")

        badge = ctk.CTkFrame(header, fg_color=color, corner_radius=10)
        badge.pack(side="left", padx=12)
        ctk.CTkLabel(badge, text=f"  {cfg['icono']}  {cfg['titulo']}  ",
                     font=("Segoe UI", 11, "bold"),
                     text_color=self.colors['white']).pack(padx=6, pady=4)
        ctk.CTkLabel(header, text="Paso 1/2 — Datos personales",
                     font=("Segoe UI", 12),
                     text_color=self.colors['text_gray']).pack(side="left", padx=10)

        ttk.Separator(self.container, orient="horizontal").pack(fill="x", pady=(0, 15))

        scroll = ctk.CTkScrollableFrame(self.container, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        form_frame = ctk.CTkFrame(scroll, fg_color=self.colors['card_bg'],
                                   corner_radius=14, border_width=1,
                                   border_color=COLORS['border'], width=920)
        form_frame.pack(fill="x", expand=True, padx=24, pady=10)

        self._section_label(form_frame, "Datos personales", color)
        self._add_fields_grid(form_frame, CAMPOS_COMUNES, columns=2)

        campos_rol = CAMPOS_POR_ROL.get(self.rol_actual, [])
        if campos_rol:
            titulos = {"alumno": "Información académica",
                       "maestro": "Información docente",
                       "personal": "Información laboral"}
            self._section_label(form_frame, titulos.get(self.rol_actual, "Datos adicionales"), color)
            self._add_fields_grid(form_frame, campos_rol, columns=2)

        ctk.CTkButton(self.container, text="Continuar → Captura de fotos",
                      fg_color=color, hover_color=self._darken(color),
                      text_color=self.colors['white'],
                      font=FontScale.fb(13), corner_radius=10, height=42,
                      command=self._validar_y_continuar).pack(pady=20)

    def _section_label(self, parent, text, color):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", pady=(14, 6), padx=12)
        ctk.CTkLabel(frame, text=text, text_color=color,
                     font=("Segoe UI", 12, "bold")).pack(anchor="w")
        ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=(3, 0))

    def _add_fields_grid(self, parent, fields, columns=2):
        grid = ctk.CTkFrame(parent, fg_color="transparent")
        grid.pack(fill="x", padx=12, pady=(0, 6))
        for col in range(columns):
            grid.grid_columnconfigure(col, weight=1, uniform="form_col")
        for idx, (label_text, key, required) in enumerate(fields):
            row = idx // columns
            col = idx % columns
            self._add_entry(grid, label_text, key, required, row, col)

    def _add_entry(self, parent, label_text, key, required, row, col):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.grid(row=row, column=col, sticky="ew", padx=8, pady=6)
        ctk.CTkLabel(frame, text=label_text + (" *" if required else ""),
                     text_color=self.colors['text_dark'],
                     font=("Segoe UI", 11), anchor="w").pack(anchor="w", pady=(0, 4))
        entry = ctk.CTkEntry(frame, font=("Segoe UI", 11), height=34,
                              corner_radius=8, border_color=COLORS['border'])
        entry.pack(fill="x", expand=True)
        self.entries[key] = entry

    def _validar_y_continuar(self):
        for key in ['nombreUsuario', 'apellidoPaternoUsuario', 'telefonoUsuario', 'correoUsuario']:
            if not self.entries.get(key, tk.Entry()).get().strip():
                nombres = {'nombreUsuario': 'nombre', 'apellidoPaternoUsuario': 'apellido paterno',
                           'telefonoUsuario': 'teléfono', 'correoUsuario': 'correo'}
                messagebox.showwarning("Campo requerido", f"El {nombres[key]} es obligatorio")
                return
        for _, key, required in CAMPOS_POR_ROL.get(self.rol_actual, []):
            if required and not self.entries.get(key, tk.Entry()).get().strip():
                messagebox.showwarning("Campo requerido", f"El campo '{key}' es obligatorio")
                return
        self.valores_form = {k: e.get().strip() for k, e in self.entries.items()}
        self._camara_lista   = False
        self._camara_preinit = None
        self._mostrar_animacion_camara()

    # ═════════════════════════════════════════════════════════════════════════
    # PANTALLA 3 — Captura automática
    # ═════════════════════════════════════════════════════════════════════════
    def _mostrar_animacion_camara(self):
        self._limpiar_container()
        cfg   = ROL_CONFIG[self.rol_actual]
        color = cfg["color"]
        c     = self.colors

        # ── Inicializar atributos PRIMERO ──────────────────────────────────────
        self._anim_activa    = True
        self._prog_valor     = 0.0
        self._dots_estado    = 0
        self._anim_fase      = 0
        self._anim_radio     = 44
        self._scan_pos       = 0.0

        outer = ctk.CTkFrame(self.container, fg_color="transparent")
        outer.pack(fill="both", expand=True)

        card = ctk.CTkFrame(outer, fg_color=c['card_bg'], corner_radius=18,
                            border_width=1, border_color=COLORS['border'],
                            width=340, height=320)
        card.place(relx=0.5, rely=0.45, anchor="center")
        card.pack_propagate(False)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(expand=True)

        self._cam_canvas = tk.Canvas(inner, width=110, height=110,
                                    bg=c['card_bg'], highlightthickness=0)
        self._cam_canvas.pack(pady=(22, 8))
        self._dibujar_icono_camara(color)  

        ctk.CTkLabel(inner, text="Iniciando cámara",
                    font=("Segoe UI", 15, "bold"),
                    text_color=c['text_dark']).pack()

        # Tres puntos animados
        self._dots_label = ctk.CTkLabel(inner, text="",
                                        font=("Segoe UI", 18),
                                        text_color=color)
        self._dots_label.pack(pady=2)

        # Barra de progreso falsa
        self._prog_anim = ctk.CTkProgressBar(inner, width=220, height=6,
                                            corner_radius=3,
                                            progress_color=color,
                                            fg_color=COLORS['border'])
        self._prog_anim.set(0)
        self._prog_anim.pack(pady=(8, 4))

        self._lbl_sub_anim = ctk.CTkLabel(inner, text="Preparando captura biométrica...",
                                        font=("Segoe UI", 10),
                                        text_color=c['text_gray'])
        self._lbl_sub_anim.pack(pady=(0, 20))

        self._anim_activa    = True
        self._prog_valor     = 0.0
        self._dots_estado    = 0
        self._anim_fase      = 0   # 0=creciendo, 1=decrece anillo
        self._anim_radio     = 44

        self._tick_anim_dots()
        self._tick_anim_prog()
        self._tick_anim_ring()

        # Iniciar cámara en background y pasar a _mostrar_captura cuando esté lista
        threading.Thread(target=self._init_camara_bg, daemon=True).start()

    def _dibujar_icono_camara(self, color):
        cv = self._cam_canvas
        cv.delete("all")
        cx, cy = 55, 58

        # Anillo exterior pulsante
        r = self._anim_radio
        cv.create_oval(cx-r, cy-r, cx+r, cy+r,
                    outline=color, width=2)

        # Cuerpo de cámara
        cv.create_rectangle(cx-22, cy-14, cx+22, cy+14,
                            outline=color, width=2, fill="")
        # Objetivo
        cv.create_oval(cx-9, cy-9, cx+9, cy+9,
                    outline=color, width=1.5, fill="")
        cv.create_oval(cx-4, cy-4, cx+4, cy+4,
                    fill=color, outline="")
        # Flash
        cv.create_rectangle(cx+14, cy-14, cx+22, cy-8,
                            outline=color, width=1.5, fill="")

        # Línea de escaneo animada
        scan_y = cy - 12 + int((self._scan_pos if hasattr(self, '_scan_pos') else 0) * 24)
        cv.create_line(cx-18, scan_y, cx+18, scan_y,
                    fill=color, width=1)

    def _tick_anim_ring(self):
        if not self._anim_activa:
            return
        if self._anim_fase == 0:
            self._anim_radio = min(50, self._anim_radio + 1)
            if self._anim_radio >= 50:
                self._anim_fase = 1
        else:
            self._anim_radio = max(42, self._anim_radio - 1)
            if self._anim_radio <= 42:
                self._anim_fase = 0

        if not hasattr(self, '_scan_pos'):
            self._scan_pos = 0.0
        self._scan_pos = (self._scan_pos + 0.06) % 1.0

        color = ROL_CONFIG[self.rol_actual]["color"]
        self._dibujar_icono_camara(color)
        self.container.after(40, self._tick_anim_ring)

    def _tick_anim_dots(self):
        if not self._anim_activa:
            return
        puntos = ["   ", "•  ", "•• ", "•••"]
        self._dots_label.configure(text=puntos[self._dots_estado % 4])
        self._dots_estado += 1
        self.container.after(400, self._tick_anim_dots)

    def _tick_anim_prog(self):
        if not self._anim_activa:
            return
        # Progreso falso que se frena cerca del 90% y espera a la cámara
        target = 0.88 if not getattr(self, '_camara_lista', False) else 1.0
        delta  = (target - self._prog_valor) * 0.06
        self._prog_valor = min(target, self._prog_valor + max(delta, 0.003))
        try:
            self._prog_anim.set(self._prog_valor)
        except Exception:
            pass
        if self._prog_valor < 0.999:
            self.container.after(60, self._tick_anim_prog)
        else:
            self.container.after(300, self._mostrar_captura)

    def _init_camara_bg(self):
        """Abre la cámara en un hilo y señala cuando está lista."""
        try:
            cap = cv2.VideoCapture(0)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            # Guardamos el objeto ya abierto para reutilizarlo
            self._camara_preinit = cap if cap.isOpened() else None
        except Exception:
            self._camara_preinit = None
        self._camara_lista = True
            
    def _mostrar_captura(self):          # ← ESTA LÍNEA FALTABA
        self._anim_activa = False        # ← ESTA TAMBIÉN
        self._limpiar_container()
        self._reset_estado_captura()

        cfg   = ROL_CONFIG[self.rol_actual]
        color = cfg["color"]
        c     = self.colors

        # ── Header ────────────────────────────────────────────────────────────
        header = ctk.CTkFrame(self.container, fg_color="transparent")
        header.pack(fill="x", pady=(0, 8))

        ctk.CTkButton(header, text="← Volver al formulario",
                      fg_color="transparent", hover_color=COLORS['content_bg'],
                      text_color=color, font=("Segoe UI", 11, "bold"),
                      command=self._volver_formulario).pack(side="left")
        ctk.CTkLabel(header, text="Paso 2/2 — Captura biométrica automática",
                     font=("Segoe UI", 12), text_color=c['text_gray']).pack(side="left", padx=15)

        ttk.Separator(self.container, orient="horizontal").pack(fill="x", pady=(0, 8))

        # ── Barra de progreso global (solo barra, sin números) ────────────────
        prog_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        prog_frame.pack(fill="x", padx=4, pady=(0, 6))

        self.bar_total_ctk = ctk.CTkProgressBar(prog_frame, height=12,
                                                  corner_radius=6,
                                                  progress_color=color,
                                                  fg_color=COLORS['border'])
        self.bar_total_ctk.set(0)
        self.bar_total_ctk.pack(fill="x", padx=8)

        # ── Cuerpo: panel guía izq + cámara der ───────────────────────────────
        body = ctk.CTkFrame(self.container, fg_color="transparent")
        body.pack(fill="both", expand=True)

        # Panel guía
        self.panel_guia = ctk.CTkFrame(body, fg_color=c['card_bg'],
                                        width=260, corner_radius=12,
                                        border_width=1, border_color=COLORS['border'])
        self.panel_guia.pack(side="left", fill="y", padx=(0, 10))
        self.panel_guia.pack_propagate(False)

        # Panel cámara
        cam_panel = ctk.CTkFrame(body, fg_color=c['card_bg'],
                                  corner_radius=12, border_width=1,
                                  border_color=COLORS['border'])
        cam_panel.pack(side="left", fill="both", expand=True)

        # Video
        self.video_label = tk.Label(cam_panel, bg=COLORS['content_bg'])
        self.video_label.pack(fill="both", expand=True, padx=8, pady=(8, 4))

        # Barra de progreso de postura actual (delgada, bajo el video)
        self.bar_postura_ctk = ctk.CTkProgressBar(cam_panel, height=8,
                                                    corner_radius=4,
                                                    progress_color=color,
                                                    fg_color=COLORS['border'])
        self.bar_postura_ctk.set(0)
        self.bar_postura_ctk.pack(fill="x", padx=8, pady=(0, 4))

        # Panel de estado — feedback en tiempo real
        estado_panel = ctk.CTkFrame(cam_panel, fg_color=c['content_bg'],
                                     corner_radius=8)
        estado_panel.pack(fill="x", padx=8, pady=(0, 8))

        self.lbl_estado = ctk.CTkLabel(estado_panel,
                                        text="🎥  Iniciando cámara...",
                                        font=("Segoe UI", 13, "bold"),
                                        text_color=c['text_gray'])
        self.lbl_estado.pack(pady=6)

        self.lbl_sub_estado = ctk.CTkLabel(estado_panel,
                                            text="",
                                            font=("Segoe UI", 10),
                                            text_color=c['text_gray'])
        self.lbl_sub_estado.pack(pady=(0, 6))

        # Botón de pausa/reanudar (por si acaso)
        self._btn_pausar = ctk.CTkButton(cam_panel, text="⏸ Pausar",
                                          fg_color=c['accent'], hover_color="#D97706",
                                          text_color="#ffffff",
                                          font=("Segoe UI", 11, "bold"),
                                          corner_radius=8, height=32, width=110,
                                          command=self._toggle_pausa)
        self._btn_pausar.pack(side="right", padx=8, pady=(0, 8))
        self._pausado = False

        # Construir guía y arrancar cámara
        self._construir_panel_guia(color)
        self._iniciar_camara_auto()

    def _reset_estado_captura(self):
        self.fotos_temp           = []
        self.postura_idx          = 0
        self.fotos_postura        = 0
        self.posturas_completadas = []
        self.capturando_rafaga    = False
        self._auto_activo         = False
        self._frames_con_cara     = 0
        self._ultima_captura      = 0.0
        self._countdown           = 0
        self._guardando           = False
        self._pausado             = False
        if self._countdown_job:
            try:
                self.container.after_cancel(self._countdown_job)
            except Exception:
                pass
            self._countdown_job = None

    # ── Panel guía lateral ────────────────────────────────────────────────────
    def _construir_panel_guia(self, color):
        for w in self.panel_guia.winfo_children():
            w.destroy()

        postura = POSTURAS[self.postura_idx]
        c       = self.colors

        # Título de postura actual
        ctk.CTkLabel(self.panel_guia,
                     text=f"Postura {self.postura_idx + 1} / {len(POSTURAS)}",
                     font=("Segoe UI", 10), text_color=c['text_gray']).pack(pady=(12, 0))
        ctk.CTkLabel(self.panel_guia,
                     text=postura["titulo"],
                     font=("Segoe UI", 13, "bold"),
                     text_color=color, wraplength=220, justify="center").pack(pady=(2, 8))

        # Imagen de referencia
        img_path   = os.path.join(os.path.dirname(os.path.dirname(__file__)), postura["imagen"])
        img_loaded = False
        if os.path.exists(img_path):
            try:
                img   = Image.open(img_path).resize((160, 160), Image.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                lbl_img       = tk.Label(self.panel_guia, image=photo,
                                          bg=COLORS['card_bg'])
                lbl_img.image = photo
                lbl_img.pack(pady=4)
                img_loaded = True
            except Exception:
                pass
        if not img_loaded:
            ctk.CTkLabel(self.panel_guia,
                         text=postura["icono"],
                         font=("Segoe UI Emoji", 54)).pack(pady=8)

        # Instrucción
        ctk.CTkLabel(self.panel_guia,
                     text=postura["instruccion"],
                     font=("Segoe UI", 10),
                     text_color=c['text_dark'],
                     wraplength=210, justify="center").pack(pady=(4, 10))

        # Separador
        ctk.CTkFrame(self.panel_guia, fg_color=COLORS['border'],
                     height=1, corner_radius=0).pack(fill="x", padx=14, pady=4)

        # Lista de todas las posturas
        for i, p in enumerate(POSTURAS):
            if i in self.posturas_completadas:
                icono, fg = "✅", COLORS['primary']
            elif i == self.postura_idx:
                icono, fg = "▶", color
            else:
                icono, fg = "○", COLORS['text_gray']

            ctk.CTkLabel(self.panel_guia,
                         text=f" {icono}  {p['titulo']}",
                         font=("Segoe UI", 10),
                         text_color=fg, anchor="w").pack(fill="x", padx=14, pady=1)

    # ── Cámara automática ─────────────────────────────────────────────────────
    def _iniciar_camara_auto(self):
        try:
            # Reutilizar la cámara ya abierta durante la animación si existe
            if getattr(self, '_camara_preinit', None) and self._camara_preinit.isOpened():
                self.camara = self._camara_preinit
                self._camara_preinit = None
            else:
                self.camara = cv2.VideoCapture(0)
                if not self.camara.isOpened():
                    self._set_estado("❌  No se pudo abrir la cámara",
                                    "Verifica que la cámara esté conectada", "danger")
                    return
                self.camara.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
                self.camara.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

            self.capturando   = True
            self._auto_activo = True
            self._iniciar_countdown()
        except Exception as e:
            self._set_estado("❌  Error al iniciar cámara", str(e), "danger")
            try:
                self.camara = cv2.VideoCapture(0)
                if not self.camara.isOpened():
                    self._set_estado("❌  No se pudo abrir la cámara",
                                    "Verifica que la cámara esté conectada", "danger")
                    return
                self.camara.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
                self.camara.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                self.capturando   = True
                self._auto_activo = True
                self._iniciar_countdown()
            except Exception as e:
                self._set_estado("❌  Error al iniciar cámara", str(e), "danger")

    def _iniciar_countdown(self):
        """3-2-1 antes de empezar a capturar la primera postura."""
        self._countdown = 3
        color = ROL_CONFIG[self.rol_actual]["color"]
        self._set_estado(
            f"📷  Prepárate — postura: {POSTURAS[self.postura_idx]['titulo']}",
            f"Comenzando en {self._countdown}...",
            "info")
        self._tick_countdown()

    def _tick_countdown(self):
        if not self.capturando:
            return
        if self._countdown > 0:
            self._set_sub(f"Comenzando en {self._countdown}...")
            self._countdown -= 1
            self._countdown_job = self.container.after(900, self._tick_countdown)
        else:
            self._set_sub("¡Manten la posición!")
            self._auto_activo = True
            self._actualizar_video()

    def _toggle_pausa(self):
        self._pausado = not self._pausado
        if self._pausado:
            self._btn_pausar.configure(text="▶ Reanudar", fg_color=COLORS['primary'])
            self._set_estado("⏸  Pausado", "Presiona Reanudar para continuar", "gray")
        else:
            self._btn_pausar.configure(text="⏸ Pausar", fg_color=self.colors['accent'])
            self._set_estado("🎥  Reanudando...", "", "info")

    def _detectar_cara(self, frame, gray, postura_id):
        """Detecta cara según la postura. Devuelve lista de (x,y,w,h) o []."""

        # Parámetros según dificultad de la postura
        PARAMS = {
            "frontal":    dict(scaleFactor=1.1, minNeighbors=5, minSize=(70, 70)),
            "izquierda":  dict(scaleFactor=1.05, minNeighbors=3, minSize=(55, 55)),
            "derecha":    dict(scaleFactor=1.05, minNeighbors=3, minSize=(55, 55)),
            "perfil_izq": dict(scaleFactor=1.1,  minNeighbors=4, minSize=(55, 55)),
            "perfil_der": dict(scaleFactor=1.1,  minNeighbors=4, minSize=(55, 55)),
        }
        p = PARAMS.get(postura_id, PARAMS["frontal"])

        if postura_id in ("izquierda", "derecha"):
            # Para giros leves: intentar frontal + alt2 en frame normal Y espejado
            # así cubrimos ambas direcciones independientemente de cómo esté parado
            for det in [self.detector_alt, self.detector_frontal]:
                # Frame normal
                caras = det.detectMultiScale(gray, **p)
                if len(caras) > 0:
                    return list(caras)
                # Frame espejado (el giro leve puede verse mejor espejado)
                gray_flip = cv2.flip(gray, 1)
                caras = det.detectMultiScale(gray_flip, **p)
                if len(caras) > 0:
                    flip_w = gray_flip.shape[1]
                    return [(flip_w - x - w, y, w, h) for (x, y, w, h) in caras]
            return []

        elif postura_id == "perfil_izq":
            # profileface detecta perfil mirando a la derecha de la imagen
            # perfil_izq = persona girada a su izquierda = en cámara mira a la derecha
            # → espejamos para que quede mirando a la izquierda del frame
            gray_flip = cv2.flip(gray, 1)
            caras = self.detector_perfil.detectMultiScale(gray_flip, **p)
            if len(caras) > 0:
                flip_w = gray_flip.shape[1]
                return [(flip_w - x - w, y, w, h) for (x, y, w, h) in caras]
            return []

        elif postura_id == "perfil_der":
            # perfil_der = persona girada a su derecha = en cámara mira a la izquierda
            # → frame directo, que es lo que profileface detecta nativamente
            caras = self.detector_perfil.detectMultiScale(gray, **p)
            return list(caras) if len(caras) > 0 else []

        else:  # frontal
            caras = self.detector_frontal.detectMultiScale(gray, **p)
            return list(caras) if len(caras) > 0 else []
        """Detecta cara según la postura. Devuelve lista de (x,y,w,h) o []."""
        detectores = self._detectores_por_postura.get(postura_id, [self.detector_frontal])

        # Para el perfil derecho, espejamos el frame para reutilizar el detector de perfil izq.
        if postura_id == "perfil_izq":
            gray_proc = cv2.flip(gray, 1)
            flip_w    = gray_proc.shape[1]
        else:
            gray_proc = gray
            flip_w    = None

        caras = []
        for det in detectores:
            caras = det.detectMultiScale(
                gray_proc, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60)
            )
            if len(caras) > 0:
                break   # primer detector que encuentre algo, suficiente

        if len(caras) == 0:
            return []

        # Si espejamos, convertimos coordenadas de vuelta al frame original
        if flip_w is not None:
            caras_orig = []
            for (x, y, w, h) in caras:
                caras_orig.append((flip_w - x - w, y, w, h))
            return caras_orig

        return list(caras)

    # ── Loop de video + captura automática ────────────────────────────────────
    def _actualizar_video(self):
        if not self.capturando or self.camara is None:
            return
        if self._guardando:
            return

        ret, frame = self.camara.read()
        if not ret:
            self.video_label.after(30, self._actualizar_video)
            return

        color = ROL_CONFIG[self.rol_actual]["color"]

        # Detección de cara
        gray       = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        postura_id = POSTURAS[self.postura_idx]["id"]
        caras      = self._detectar_cara(frame, gray, postura_id)

        cara_detectada = len(caras) > 0
        ahora          = time.time()

        if cara_detectada:
            self._frames_con_cara += 1
            x, y, w, h = max(caras, key=lambda c: c[2]*c[3])

            # Dibujar rectángulo alrededor de la cara
            listo = self._frames_con_cara >= FRAMES_ESTABLE
            rect_color = (0, 220, 0) if listo else (0, 180, 255)
            cv2.rectangle(frame, (x, y), (x+w, y+h), rect_color, 2)

            # ── Captura automática ────────────────────────────────────────────
            if (not self._pausado
                    and self._auto_activo
                    and listo
                    and (ahora - self._ultima_captura) >= CAPTURE_DELAY):

                rostro = frame[y:y+h, x:x+w]
                rostro = cv2.resize(rostro, (200, 200))
                _, buf = cv2.imencode('.jpg', rostro,
                                      [cv2.IMWRITE_JPEG_QUALITY, 90])
                self.fotos_temp.append(buf.tobytes())
                self.fotos_postura  += 1
                self._ultima_captura = ahora

                total_fotos    = POSTURAS[self.postura_idx]["fotos"]
                progreso_pos   = self.fotos_postura / total_fotos
                progreso_total = len(self.fotos_temp) / TOTAL_FOTOS

                # Actualizar barras
                try:
                    self.bar_postura_ctk.set(progreso_pos)
                    self.bar_total_ctk.set(progreso_total)
                except Exception:
                    pass

                # Feedback de estado
                restantes = total_fotos - self.fotos_postura
                if restantes > 0:
                    self._set_estado(
                        f"✅  Capturando — {POSTURAS[self.postura_idx]['titulo']}",
                        f"Mantén la posición... {int(progreso_pos*100)}% de esta postura",
                        "ok")
                else:
                    # Postura completada
                    self._postura_completada()
                    return

        else:
            self._frames_con_cara = 0
            # Sin cara — avisar
            if not self._pausado and self._auto_activo:
                self._set_estado(
                    "⚠️  No se detecta tu cara",
                    "Acércate o ajusta la iluminación",
                    "warn")
            cv2.putText(frame, "Sin cara detectada", (12, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (30, 30, 220), 2)

        # Mostrar frame en la UI
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h_f, w_f  = frame_rgb.shape[:2]
        try:
            lw = self.video_label.winfo_width()  or 480
            lh = self.video_label.winfo_height() or 360
        except Exception:
            lw, lh = 480, 360
        scale  = min(lw / w_f, lh / h_f, 1.0)
        nw, nh = max(1, int(w_f * scale)), max(1, int(h_f * scale))
        frame_rgb = cv2.resize(frame_rgb, (nw, nh))
        img   = Image.fromarray(frame_rgb)
        imgtk = ImageTk.PhotoImage(image=img)
        try:
            self.video_label.imgtk = imgtk
            self.video_label.config(image=imgtk)
        except Exception:
            pass

        self.video_label.after(15, self._actualizar_video)

    # ── Postura completada ────────────────────────────────────────────────────
    def _postura_completada(self):
        self._auto_activo = False
        color = ROL_CONFIG[self.rol_actual]["color"]

        self.posturas_completadas.append(self.postura_idx)
        self.bar_postura_ctk.set(1.0)

        if self.postura_idx < len(POSTURAS) - 1:
            # Hay más posturas — transición con pausa de 1.8 s
            siguiente = POSTURAS[self.postura_idx + 1]
            self._set_estado(
                f"✅  ¡Postura completada!",
                f"Prepárate para: {siguiente['titulo']} — cambiando en 2s...",
                "ok")
            self.container.after(1800, self._pasar_a_siguiente_postura)
        else:
            # Todas listas — guardar
            self.bar_total_ctk.set(1.0)
            self._set_estado(
                "🎉  ¡Todas las posturas completadas!",
                "Guardando usuario automáticamente...",
                "ok")
            self.container.after(800, self._guardar_automatico)

    def _pasar_a_siguiente_postura(self):
        if not self.capturando:
            return
        self.postura_idx   += 1
        self.fotos_postura  = 0
        self._frames_con_cara = 0
        self._countdown     = 3

        color = ROL_CONFIG[self.rol_actual]["color"]
        self.bar_postura_ctk.set(0)
        self._construir_panel_guia(color)

        postura = POSTURAS[self.postura_idx]
        self._set_estado(
            f"🔄  Nueva postura: {postura['titulo']}",
            f"Comenzando en {self._countdown}...",
            "info")

        self._tick_countdown_postura()

    def _tick_countdown_postura(self):
        if not self.capturando:
            return
        if self._countdown > 0:
            self._set_sub(f"Comenzando en {self._countdown}...")
            self._countdown -= 1
            self._countdown_job = self.container.after(900, self._tick_countdown_postura)
        else:
            self._set_sub("¡Mantén la posición!")
            self._auto_activo = True
            self._actualizar_video()

    # ── Estado UI ─────────────────────────────────────────────────────────────
    def _set_estado(self, texto, subtexto="", tipo="info"):
        COLORES = {
            "ok":     "#16a34a",
            "warn":   "#d97706",
            "danger": "#dc2626",
            "info":   self.colors['info'],
            "gray":   self.colors['text_gray'],
        }
        color = COLORES.get(tipo, self.colors['text_gray'])
        try:
            self.lbl_estado.configure(text=texto, text_color=color)
            self.lbl_sub_estado.configure(text=subtexto, text_color=self.colors['text_gray'])
        except Exception:
            pass

    def _set_sub(self, texto):
        try:
            self.lbl_sub_estado.configure(text=texto)
        except Exception:
            pass

    # ── Guardado automático ───────────────────────────────────────────────────
    def _guardar_automatico(self):
        self._guardando = True
        self._detener_camara_silencio()
        threading.Thread(target=self._guardar_en_bd, daemon=True).start()

    def _guardar_en_bd(self):
        try:
            rol = self.rol_actual
            v   = getattr(self, 'valores_form', {})

            def val(key, upper=True):
                t = v.get(key, "").strip()
                return t.upper() if upper else t

            conn  = get_db()
            ahora = datetime.now()

            if self.modo_retomar_fotos:
                user_id = self.user_id_existente
                cursor  = conn.cursor()
                cursor.execute("DELETE FROM biometria WHERE fkIdUsuario = ?", (user_id,))
                for foto_bytes in self.fotos_temp:
                    sp_insertar_biometria(conn, user_id, foto_bytes, ahora)
                conn.commit()
                conn.close()
                self.container.after(0, lambda: self._fin_guardado(
                    "Fotos actualizadas",
                    f"Se actualizaron {len(self.fotos_temp)} fotos del usuario."
                ))
                return

            user_id = sp_insertar_usuario(conn, {
                'nombre':    val('nombreUsuario'),
                'paterno':   val('apellidoPaternoUsuario'),
                'materno':   val('apellidoMaternoUsuario'),
                'matricula': val('matriculaUsuario', upper=False),
                'rol':       rol,
                'telefono':  val('telefonoUsuario',  upper=False),
                'correo':    val('correoUsuario',    upper=False),
            })

            if rol == "alumno":
                sp_insertar_alumno(conn, user_id, {
                    'grado':    val('gradoAlumno', upper=False),
                    'grupo':    val('grupoAlumno', upper=False),
                    'facultad': val('facultadAlumno'),
                    'carrera':  val('carreraAlumno'),
                })
            elif rol == "maestro":
                sp_insertar_maestro(conn, user_id, {
                    'grado':   val('gradoImpartidoMaestro', upper=False),
                    'materia': val('materiaImpartidaMaestro'),
                })
            elif rol == "personal":
                sp_insertar_personal(conn, user_id, {
                    'puesto': val('puestoPersonalEscolar'),
                    'area':   val('areaPersonalEscolar'),
                })

            for foto_bytes in self.fotos_temp:
                sp_insertar_biometria(conn, user_id, foto_bytes, ahora)

            conn.commit()
            conn.close()

            cfg = ROL_CONFIG[rol]
            nombre_completo = f"{val('nombreUsuario')} {val('apellidoPaternoUsuario')}"
            self.container.after(0, lambda: self._fin_guardado(
                "✅ Registro exitoso",
                f"{cfg['icono']} {nombre_completo} ({cfg['titulo']})\n"
                f"Registrado con {len(self.fotos_temp)} fotos."
            ))

        except Exception as e:
            self.container.after(0, lambda: messagebox.showerror("Error", f"Error al guardar: {e}"))
            self._guardando = False

    def _fin_guardado(self, titulo, mensaje):
        messagebox.showinfo(titulo, mensaje)
        self._guardando = False
        self._mostrar_seleccion_rol()

    # ── Cámara helpers ────────────────────────────────────────────────────────
    def _detener_camara_silencio(self):
        self.capturando   = False
        self._auto_activo = False
        if self.camara:
            self.camara.release()
            self.camara = None

    def _detener_camara(self):
        self._detener_camara_silencio()
        try:
            self.video_label.config(image='')
        except Exception:
            pass

    def _volver_formulario(self):
        self._detener_camara()
        self._mostrar_formulario()

    def _limpiar_container(self):
        self._detener_camara_silencio()
        for w in self.container.winfo_children():
            w.destroy()

    def __del__(self):
        if self.camara:
            self.camara.release()