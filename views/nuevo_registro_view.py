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
from camera import Camera
from idiomas import t
from tkcalendar import DateEntry

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
    "alumno":   {"icono": "🎓", "titulo": t("estudiante"), "desc": " ", "color": "#4A90D9"},
    "maestro":  {"icono": "📚", "titulo": t("docente"),    "desc": " ", "color": "#27AE60"},
    "personal": {"icono": "🏢", "titulo": t("personal"),   "desc": "",  "color": "#E67E22"},
}

CAMPOS_POR_ROL = {
    "alumno": [
        (t("grado")+":",    "gradoAlumno",             True),
        (t("grupo")+":",    "grupoAlumno",             True),
        (t("facultad")+":", "facultadAlumno",           True),
        (t("carrera")+":",  "carreraAlumno",            True),
    ],
    "maestro": [
        (t("grado_imparte")+":", "gradoImpartidoMaestro",   True),
        (t("materia")+":",       "materiaImpartidaMaestro",  True),
    ],
    "personal": [
        (t("puesto")+":", "puestoPersonalEscolar", True),
        (t("area")+":",   "areaPersonalEscolar",   True),
    ],
}

CAMPOS_COMUNES = [
    (t("nombre")+":",           "nombreUsuario",          True),
    (t("apellido_paterno")+":", "apellidoPaternoUsuario",  True),
    (t("apellido_materno")+":", "apellidoMaternoUsuario",  False),
    (t("matricula")+":",        "matriculaUsuario",        False),
    (t("telefono")+":",         "telefonoUsuario",         True),
    (t("correo")+":",           "correoUsuario",           True),
    (t("fecha_nacimiento")+":", "fechaNacimientoUsuario",  True),
    (t("tipo_sangre")+":",      "tipoSangreUsuario",  True),
    (t("direccion")+":",        "direccionUsuario",  True),
]

# ── Posturas ──────────────────────────────────────────────────────────────────
POSTURAS = [
    {
        "id":          "frontal",
        "titulo":      t("frontal"),
        "instruccion": t("inst_frontal"),
        "imagen":      "assets/posturas/postura_frontal.png",
        "icono":       "😐",
        "fotos":       60,
    },
    {
        "id":          "izquierda",
        "titulo":      t("izquierda"),
        "instruccion": t("inst_izquierda"),
        "imagen":      "assets/posturas/postura_izquierda.png",
        "icono":       "😶",
        "fotos":       60,
    },
    {
        "id":          "derecha",
        "titulo":      t("derecha"),
        "instruccion": t("inst_derecha"),
        "imagen":      "assets/posturas/postura_derecha.png",
        "icono":       "😶",
        "fotos":       60,
    },
    {
        "id":          "perfil_izq",
        "titulo":      t("perfil_izquierda"),
        "instruccion": t("inst_perfil_izq"),
        "imagen":      "assets/posturas/postura_perfil_izq.png",
        "icono":       "🙂",
        "fotos":       60,
    },
    {
        "id":          "perfil_der",
        "titulo":      t("perfil_derecha"),
        "instruccion": t("inst_perfil_der"),
        "imagen":      "assets/posturas/postura_perfil_der.png",
        "icono":       "🙂",
        "fotos":       60,
    },
]

TOTAL_FOTOS    = sum(p["fotos"] for p in POSTURAS)   # 300
FRAMES_ESTABLE = 8
CAPTURE_DELAY  = 0.04   # segundos entre capturas (~25 fotos/seg)


class NuevoRegistroView:
    def __init__(self, parent, initial_state=None):
        self.colors    = get_colors()
        self.parent    = parent
        self.container = ctk.CTkFrame(parent, fg_color=self.colors['background'])
        self.container.pack(fill="both", expand=True, padx=30, pady=30)

        self.camara    = None
        self.capturando = False
        self.fotos_temp = []   # list[bytes] — JPG en color (BGR→RGB guardado como JPG)
        self.rol_actual = None
        self.entries    = {}

        self.postura_idx          = 0
        self.fotos_postura        = 0
        self.posturas_completadas = []

        self._auto_activo     = False
        self._frames_con_cara = 0
        self._ultima_captura  = 0.0
        self._countdown       = 0
        self._countdown_job   = None
        self._guardando       = False
        self._pausado         = False

        # ── Detectores Haar ────────────────────────────────────────────────────
        self.detector_frontal = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        self.detector_alt = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_alt2.xml'
        )
        self.detector_perfil = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_profileface.xml'
        )

        self.modo_retomar_fotos = False
        self.user_id_existente  = None
        self.valores_form       = {}

        # Restaurar estado si viene de un recargo de vista
        estado = initial_state or {}
        self.rol_actual = estado.get("rol_actual")
        if self.rol_actual in ROL_CONFIG:
            self.valores_form = dict(estado.get("valores_form") or {})
            self._mostrar_formulario()
        else:
            self._mostrar_seleccion_rol()

    def export_state(self):
        """Exporta el estado del formulario para restaurarlo tras recargar la vista."""
        valores = dict(getattr(self, 'valores_form', {}) or {})
        for key, entry in getattr(self, 'entries', {}).items():
            try:
                valores[key] = entry.get().strip()
            except Exception:
                pass
        return {
            "rol_actual":  self.rol_actual,
            "valores_form": valores,
        }

    # ═════════════════════════════════════════════════════════════════════════
    # PANTALLA 1 — Selección de rol
    # ═════════════════════════════════════════════════════════════════════════
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
                     font=("Segoe UI Emoji", 110)).grid(row=0, column=0, pady=(28, 6))

        info = ctk.CTkFrame(card, fg_color="transparent")
        info.grid(row=1, column=0, sticky="ew", padx=16)
        ctk.CTkLabel(info, text=cfg["titulo"], font=("Segoe UI", 30, "bold"),
                     text_color=color, wraplength=160, justify="center").pack()
        ctk.CTkLabel(info, text=cfg["desc"], font=("Segoe UI", 11),
                     text_color=self.colors['text_gray'],
                     wraplength=160, justify="center").pack(pady=(4, 0))

        ctk.CTkButton(card, text=t("seleccionar"),
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
        ctk.CTkButton(header, text=t("regresar"),
                      fg_color="transparent", hover_color=COLORS['content_bg'],
                      text_color=color, font=("Segoe UI", 11, "bold"),
                      command=self._mostrar_seleccion_rol).pack(side="left")

        badge = ctk.CTkFrame(header, fg_color=color, corner_radius=10)
        badge.pack(side="left", padx=12)
        ctk.CTkLabel(badge, text=f"  {cfg['icono']}  {cfg['titulo']}  ",
                     font=("Segoe UI", 11, "bold"),
                     text_color=self.colors['white']).pack(padx=6, pady=4)
        ctk.CTkLabel(header, text=t("paso_datos"),
                     font=("Segoe UI", 12),
                     text_color=self.colors['text_gray']).pack(side="left", padx=10)

        ttk.Separator(self.container, orient="horizontal").pack(fill="x", pady=(0, 15))

        scroll = ctk.CTkScrollableFrame(self.container, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        form_frame = ctk.CTkFrame(scroll, fg_color=self.colors['card_bg'],
                                   corner_radius=14, border_width=1,
                                   border_color=COLORS['border'], width=920)
        form_frame.pack(fill="x", expand=True, padx=24, pady=10)

        self._section_label(form_frame, t("datos_personales"), color)
        self._add_fields_grid(form_frame, CAMPOS_COMUNES, columns=2)

        campos_rol = CAMPOS_POR_ROL.get(self.rol_actual, [])
        if campos_rol:
            titulos = {
                "alumno":   t("info_academica"),
                "maestro":  t("info_docente"),
                "personal": t("info_laboral"),
            }
            self._section_label(form_frame,
                                titulos.get(self.rol_actual, "Datos adicionales"), color)
            self._add_fields_grid(form_frame, campos_rol, columns=2)

        ctk.CTkButton(self.container, text=t("continuar_fotos"),
                      fg_color=color, hover_color=self._darken(color),
                      text_color=self.colors['white'],
                      font=FontScale.fb(13), corner_radius=10, height=42,
                      command=self._validar_y_continuar).pack(pady=20)

        # Restaurar valores si los hay
        if hasattr(self, 'valores_form') and self.valores_form:
            for key, entry in self.entries.items():
                if key in self.valores_form:
                    entry.delete(0, "end")
                    entry.insert(0, self.valores_form[key])

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

        ctk.CTkLabel(
            frame,
            text=label_text + (" *" if required else ""),
            text_color=self.colors['text_dark'],
            font=("Segoe UI", 11),
            anchor="w"
        ).pack(anchor="w", pady=(0, 4))

        #Campo especial: Fecha de nacimiento
        if key == "fechaNacimientoUsuario":
            entry = DateEntry(
                frame,
                date_pattern='dd-mm-yyyy',
                maxdate=datetime.now(),
                font=("Segoe UI", 11)
            )
            entry.pack(fill="x", expand=True)

        # Campo especial: Tipo de sangre
        elif key == "tipoSangreUsuario":
            entry = ttk.Combobox(
                frame,
                values=[
                    "A+", "A-",
                    "B+", "B-",
                    "AB+", "AB-",
                    "O+", "O-"
                ],
                state="readonly",
                font=("Segoe UI", 11)
            )
            entry.pack(fill="x", expand=True)

        # 🔹 Campos normales
        else:
            entry = ctk.CTkEntry(
                frame,
                font=("Segoe UI", 11),
                height=34,
                corner_radius=8,
                border_color=COLORS['border']
            )
            entry.pack(fill="x", expand=True)

        self.entries[key] = entry

    def _validar_y_continuar(self):
        requeridos = {
            'nombreUsuario':          'nombre',
            'apellidoPaternoUsuario': 'apellido paterno',
            'telefonoUsuario':        'teléfono',
            'correoUsuario':          'correo',
        }
        for key, nombre in requeridos.items():
            if not self.entries.get(key, tk.Entry()).get().strip():
                messagebox.showwarning(t("campo_requerido"),
                                       t("nombre_obligatorio"))
                return

        for _, key, required in CAMPOS_POR_ROL.get(self.rol_actual, []):
            if required and not self.entries.get(key, tk.Entry()).get().strip():
                messagebox.showwarning(t("campo_requerido"),
                                       f"El campo '{key}' es obligatorio")
                return

        self.valores_form  = {k: e.get().strip() for k, e in self.entries.items()}
        self._camara_lista = False
        self._mostrar_animacion_camara()

    # ═════════════════════════════════════════════════════════════════════════
    # PANTALLA 3 — Animación carga cámara
    # ═════════════════════════════════════════════════════════════════════════
    def _mostrar_animacion_camara(self):
        self._limpiar_container()
        cfg   = ROL_CONFIG[self.rol_actual]
        color = cfg["color"]
        c     = self.colors

        self._anim_activa = True
        self._prog_valor  = 0.0
        self._dots_estado = 0
        self._anim_fase   = 0
        self._anim_radio  = 44
        self._scan_pos    = 0.0

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

        ctk.CTkLabel(inner, text=t("iniciando_camara"),
                     font=("Segoe UI", 15, "bold"),
                     text_color=c['text_dark']).pack()

        self._dots_label = ctk.CTkLabel(inner, text="",
                                         font=("Segoe UI", 18), text_color=color)
        self._dots_label.pack(pady=2)

        self._prog_anim = ctk.CTkProgressBar(inner, width=220, height=6,
                                              corner_radius=3,
                                              progress_color=color,
                                              fg_color=COLORS['border'])
        self._prog_anim.set(0)
        self._prog_anim.pack(pady=(8, 4))

        self._lbl_sub_anim = ctk.CTkLabel(inner, text=t("preparando_biometria"),
                                           font=("Segoe UI", 10),
                                           text_color=c['text_gray'])
        self._lbl_sub_anim.pack(pady=(0, 20))

        self._tick_anim_dots()
        self._tick_anim_prog()
        self._tick_anim_ring()

        # La cámara se abre directamente en _iniciar_camara_auto
        self.container.after(200, self._set_camara_lista)

    def _set_camara_lista(self):
        self._camara_lista = True

    def _dibujar_icono_camara(self, color):
        cv = self._cam_canvas
        cv.delete("all")
        cx, cy = 55, 58
        r = self._anim_radio
        cv.create_oval(cx-r, cy-r, cx+r, cy+r, outline=color, width=2)
        cv.create_rectangle(cx-22, cy-14, cx+22, cy+14, outline=color, width=2, fill="")
        cv.create_oval(cx-9, cy-9, cx+9, cy+9, outline=color, width=1.5, fill="")
        cv.create_oval(cx-4, cy-4, cx+4, cy+4, fill=color, outline="")
        cv.create_rectangle(cx+14, cy-14, cx+22, cy-8, outline=color, width=1.5, fill="")
        scan_y = cy - 12 + int(self._scan_pos * 24)
        cv.create_line(cx-18, scan_y, cx+18, scan_y, fill=color, width=1)

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

    # ═════════════════════════════════════════════════════════════════════════
    # PANTALLA 4 — Captura biométrica
    # ═════════════════════════════════════════════════════════════════════════
    def _mostrar_captura(self):
        self._anim_activa = False
        self._limpiar_container()
        self._reset_estado_captura()

        cfg   = ROL_CONFIG[self.rol_actual]
        color = cfg["color"]
        c     = self.colors

        # ── Header ────────────────────────────────────────────────────────────
        header = ctk.CTkFrame(self.container, fg_color="transparent")
        header.pack(fill="x", pady=(0, 8))

        ctk.CTkButton(header, text="← Volver al formulario",
                      fg_color='#16A34A', hover_color="#15803D",
                      text_color="#ffffff",
                      font=("Segoe UI", 15, "bold"),
                      corner_radius=8, height=32,
                      command=self._volver_formulario).pack(side="left")

        ctk.CTkLabel(header, text="Paso 2/2 — Captura biométrica automática",
                     font=("Segoe UI", 12),
                     text_color=c['text_gray']).pack(side="left", padx=15)

        ttk.Separator(self.container, orient="horizontal").pack(fill="x", pady=(0, 8))

        # ── Barra de progreso global ───────────────────────────────────────────
        prog_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        prog_frame.pack(fill="x", padx=4, pady=(0, 6))
        self.bar_total_ctk = ctk.CTkProgressBar(prog_frame, height=12,
                                                  corner_radius=6,
                                                  progress_color=color,
                                                  fg_color=COLORS['border'])
        self.bar_total_ctk.set(0)
        self.bar_total_ctk.pack(fill="x", padx=8)

        # ── Cuerpo ────────────────────────────────────────────────────────────
        body = ctk.CTkFrame(self.container, fg_color="transparent")
        body.pack(fill="both", expand=True)

        self.panel_guia = ctk.CTkFrame(body, fg_color=c['card_bg'],
                                        width=260, corner_radius=12,
                                        border_width=1, border_color=COLORS['border'])
        self.panel_guia.pack(side="left", fill="y", padx=(0, 10))
        self.panel_guia.pack_propagate(False)

        cam_panel = ctk.CTkFrame(body, fg_color=c['card_bg'],
                                  corner_radius=12, border_width=1,
                                  border_color=COLORS['border'])
        cam_panel.pack(side="left", fill="both", expand=True)

        self.video_label = tk.Label(cam_panel, bg=COLORS['content_bg'])
        self.video_label.pack(fill="both", expand=True, padx=8, pady=(8, 4))

        self.bar_postura_ctk = ctk.CTkProgressBar(cam_panel, height=8,
                                                    corner_radius=4,
                                                    progress_color=color,
                                                    fg_color=COLORS['border'])
        self.bar_postura_ctk.set(0)
        self.bar_postura_ctk.pack(fill="x", padx=8, pady=(0, 4))

        estado_panel = ctk.CTkFrame(cam_panel, fg_color=c['content_bg'], corner_radius=8)
        estado_panel.pack(fill="x", padx=8, pady=(0, 8))

        self.lbl_estado = ctk.CTkLabel(estado_panel,
                                        text=t("iniciando_camara_estado"),
                                        font=("Segoe UI", 13, "bold"),
                                        text_color=c['text_gray'])
        self.lbl_estado.pack(pady=6)

        self.lbl_sub_estado = ctk.CTkLabel(estado_panel, text="",
                                            font=("Segoe UI", 10),
                                            text_color=c['text_gray'])
        self.lbl_sub_estado.pack(pady=(0, 6))

        # Botones inferiores
        btn_row = ctk.CTkFrame(cam_panel, fg_color="transparent")
        btn_row.pack(fill="x", padx=8, pady=(0, 8))

        self._btn_pausar = ctk.CTkButton(btn_row, text=t("pausar"),
                                          fg_color=c['accent'], hover_color="#D97706",
                                          text_color="#ffffff",
                                          font=("Segoe UI", 11, "bold"),
                                          corner_radius=8, height=32, width=110,
                                          command=self._toggle_pausa)
        self._btn_pausar.pack(side="right", padx=(4, 0))

        ctk.CTkButton(btn_row, text=t("cancelar"),
                      fg_color="#DC2626", hover_color="#B91C1C",
                      text_color="#ffffff",
                      font=("Segoe UI", 11, "bold"),
                      corner_radius=8, height=32, width=110,
                      command=self._mostrar_seleccion_rol).pack(side="right", padx=(0, 4))

        self._construir_panel_guia(color)
        self._iniciar_camara_auto()

    def _reset_estado_captura(self):
        self.fotos_temp           = []
        self.postura_idx          = 0
        self.fotos_postura        = 0
        self.posturas_completadas = []
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

    # ── Panel guía ────────────────────────────────────────────────────────────
    def _construir_panel_guia(self, color):
        for w in self.panel_guia.winfo_children():
            w.destroy()

        postura = POSTURAS[self.postura_idx]
        c       = self.colors

        ctk.CTkLabel(self.panel_guia,
                     text=f"Postura {self.postura_idx + 1} / {len(POSTURAS)}",
                     font=("Segoe UI", 10), text_color=c['text_gray']).pack(pady=(12, 0))
        ctk.CTkLabel(self.panel_guia, text=postura["titulo"],
                     font=("Segoe UI", 13, "bold"),
                     text_color=color, wraplength=220, justify="center").pack(pady=(2, 8))

        img_path   = os.path.join(os.path.dirname(os.path.dirname(__file__)), postura["imagen"])
        img_loaded = False
        if os.path.exists(img_path):
            try:
                img   = Image.open(img_path).resize((160, 160), Image.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                lbl_img       = tk.Label(self.panel_guia, image=photo, bg=COLORS['card_bg'])
                lbl_img.image = photo
                lbl_img.pack(pady=4)
                img_loaded = True
            except Exception:
                pass
        if not img_loaded:
            ctk.CTkLabel(self.panel_guia, text=postura["icono"],
                         font=("Segoe UI Emoji", 54)).pack(pady=8)

        ctk.CTkLabel(self.panel_guia, text=postura["instruccion"],
                     font=("Segoe UI", 10), text_color=c['text_dark'],
                     wraplength=210, justify="center").pack(pady=(4, 10))

        ctk.CTkFrame(self.panel_guia, fg_color=COLORS['border'],
                     height=1, corner_radius=0).pack(fill="x", padx=14, pady=4)

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

    # ── Cámara ────────────────────────────────────────────────────────────────
    def _iniciar_camara_auto(self):
        try:
            self.camara = Camera()
            self.camara.start()
            time.sleep(0.8)
            self.capturando   = True
            self._auto_activo = True
            self._iniciar_countdown()
        except Exception as e:
            self._set_estado(t("error_iniciar_camara"), str(e), "danger")

    def _iniciar_countdown(self):
        self._countdown = 3
        self._set_estado(
            f"📷 {t('preparate_postura')} {POSTURAS[self.postura_idx]['titulo']}",
            f"{t('comenzando_en')} {self._countdown}...", "info")
        self._tick_countdown()

    def _tick_countdown(self):
        if not self.capturando:
            return
        if self._countdown > 0:
            self._set_sub(f"Comenzando en {self._countdown}...")
            self._countdown -= 1
            self._countdown_job = self.container.after(900, self._tick_countdown)
        else:
            self._set_sub(t("manten_posicion"))
            self._auto_activo = True
            self._actualizar_video()

    def _toggle_pausa(self):
        self._pausado = not self._pausado
        if self._pausado:
            self._btn_pausar.configure(text=t("reanudar"), fg_color=COLORS['primary'])
            self._set_estado(t("pausado"), t("presiona_reanudar"), "gray")
        else:
            self._btn_pausar.configure(text=t("pausar"), fg_color=self.colors['accent'])
            self._set_estado(t("reanudando"), "", "info")

    # ── Detección de cara por postura ──────────────────────────────────────────
    def _filtrar_caras(self, caras, frame_shape):
        """Descarta caras demasiado pequeñas o en los bordes del frame."""
        h_f, w_f = frame_shape[:2]
        area_min = (w_f * 0.10) * (h_f * 0.10)
        resultado = []
        for (x, y, w, h) in caras:
            if w * h < area_min:
                continue
            if x < 8 or y < 8 or (x + w) > w_f - 8:
                continue
            resultado.append((x, y, w, h))
        return resultado

    def _detectar_cara(self, frame, gray, postura_id):
        """Detecta cara según la postura actual. Retorna lista de (x,y,w,h) o []."""
        PARAMS = {
            "frontal":    dict(scaleFactor=1.1,  minNeighbors=7, minSize=(90, 90)),
            "izquierda":  dict(scaleFactor=1.05, minNeighbors=5, minSize=(70, 70)),
            "derecha":    dict(scaleFactor=1.05, minNeighbors=5, minSize=(70, 70)),
            "perfil_izq": dict(scaleFactor=1.1,  minNeighbors=6, minSize=(70, 70)),
            "perfil_der": dict(scaleFactor=1.1,  minNeighbors=6, minSize=(70, 70)),
        }
        p = PARAMS.get(postura_id, PARAMS["frontal"])

        if postura_id in ("izquierda", "derecha"):
            for det in [self.detector_alt, self.detector_frontal]:
                caras = det.detectMultiScale(gray, **p)
                filtradas = self._filtrar_caras(caras, gray.shape)
                if filtradas:
                    return filtradas
            # Intento con flip
            gray_flip = cv2.flip(gray, 1)
            flip_w    = gray_flip.shape[1]
            for det in [self.detector_alt, self.detector_frontal]:
                caras = det.detectMultiScale(gray_flip, **p)
                if len(caras) > 0:
                    caras = [(flip_w - x - w, y, w, h) for (x, y, w, h) in caras]
                    filtradas = self._filtrar_caras(caras, gray.shape)
                    if filtradas:
                        return filtradas
            return []

        elif postura_id == "perfil_izq":
            gray_flip = cv2.flip(gray, 1)
            caras = self.detector_perfil.detectMultiScale(gray_flip, **p)
            if len(caras) > 0:
                flip_w = gray_flip.shape[1]
                caras  = [(flip_w - x - w, y, w, h) for (x, y, w, h) in caras]
                return self._filtrar_caras(caras, gray.shape)
            return []

        elif postura_id == "perfil_der":
            caras = self.detector_perfil.detectMultiScale(gray, **p)
            if len(caras) > 0:
                return self._filtrar_caras(caras, gray.shape)
            # Intento con flip
            gray_flip = cv2.flip(gray, 1)
            caras = self.detector_perfil.detectMultiScale(gray_flip, **p)
            if len(caras) > 0:
                flip_w = gray_flip.shape[1]
                caras  = [(flip_w - x - w, y, w, h) for (x, y, w, h) in caras]
                return self._filtrar_caras(caras, gray.shape)
            return []

        else:  # frontal
            caras = self.detector_frontal.detectMultiScale(gray, **p)
            return self._filtrar_caras(caras, gray.shape) if len(caras) > 0 else []

    # ── Loop de video y captura ────────────────────────────────────────────────
    def _actualizar_video(self):
        if not self.capturando or self.camara is None:
            return
        if self._guardando:
            return

        try:
            frame = self.camara.read()
            if frame is None:
                self.video_label.after(30, self._actualizar_video)
                return
        except Exception:
            self.video_label.after(30, self._actualizar_video)
            return

        gray       = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        postura_id = POSTURAS[self.postura_idx]["id"]
        caras      = self._detectar_cara(frame, gray, postura_id)

        cara_detectada = len(caras) > 0
        ahora          = time.time()

        if cara_detectada:
            self._frames_con_cara += 1
            x, y, w, h = max(caras, key=lambda c: c[2] * c[3])

            listo      = self._frames_con_cara >= FRAMES_ESTABLE
            rect_color = (0, 220, 0) if listo else (0, 180, 255)
            cv2.rectangle(frame, (x, y), (x+w, y+h), rect_color, 2)

            if (not self._pausado
                    and self._auto_activo
                    and listo
                    and (ahora - self._ultima_captura) >= CAPTURE_DELAY):

                # ── IMPORTANTE: guardar en COLOR (BGR) ────────────────────────
                # face_recognition necesita imagen en color para extraer encodings.
                # Guardamos el recorte del rostro en color como JPG.
                rostro_bgr = frame[y:y+h, x:x+w]
                rostro_bgr = cv2.resize(rostro_bgr, (200, 200))
                _, buf = cv2.imencode('.jpg', rostro_bgr,
                                      [cv2.IMWRITE_JPEG_QUALITY, 92])
                self.fotos_temp.append(buf.tobytes())
                self.fotos_postura  += 1
                self._ultima_captura = ahora

                total_fotos    = POSTURAS[self.postura_idx]["fotos"]
                progreso_pos   = self.fotos_postura / total_fotos
                progreso_total = len(self.fotos_temp) / TOTAL_FOTOS

                try:
                    self.bar_postura_ctk.set(progreso_pos)
                    self.bar_total_ctk.set(progreso_total)
                except Exception:
                    pass

                if self.fotos_postura < total_fotos:
                    self._set_estado(
                        f"✅ {t('capturando')} {POSTURAS[self.postura_idx]['titulo']}",
                        f"{t('manten_posicion')} {int(progreso_pos * 100)}%",
                        "ok")
                else:
                    self._postura_completada()
                    return
        else:
            self._frames_con_cara = 0
            if not self._pausado and self._auto_activo:
                self._set_estado(t("no_detecta_cara"), t("acercate_iluminacion"), "warn")
            cv2.putText(frame, t("sin_cara"), (12, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (30, 30, 220), 2)

        # Mostrar frame en UI
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
        img       = Image.fromarray(frame_rgb)
        imgtk     = ImageTk.PhotoImage(image=img)
        try:
            self.video_label.imgtk = imgtk
            self.video_label.config(image=imgtk)
        except Exception:
            pass

        self.video_label.after(15, self._actualizar_video)

    # ── Posturas ──────────────────────────────────────────────────────────────
    def _postura_completada(self):
        self._auto_activo = False
        self.posturas_completadas.append(self.postura_idx)
        self.bar_postura_ctk.set(1.0)

        if self.postura_idx < len(POSTURAS) - 1:
            siguiente = POSTURAS[self.postura_idx + 1]
            self._set_estado(
                t("postura_completada"),
                f"Prepárate para: {siguiente['titulo']} — cambiando en 2s...", "ok")
            self.container.after(1800, self._pasar_a_siguiente_postura)
        else:
            self.bar_total_ctk.set(1.0)
            self._set_estado(t("todas_posturas"), t("guardando_auto"), "ok")
            self.container.after(800, self._guardar_automatico)

    def _pasar_a_siguiente_postura(self):
        if not self.capturando:
            return
        self.postura_idx     += 1
        self.fotos_postura    = 0
        self._frames_con_cara = 0
        self._countdown       = 3
        color = ROL_CONFIG[self.rol_actual]["color"]
        self.bar_postura_ctk.set(0)
        self._construir_panel_guia(color)
        postura = POSTURAS[self.postura_idx]
        self._set_estado(
            f"🔄 {t('nueva_postura')} {postura['titulo']}",
            f"Comenzando en {self._countdown}...", "info")
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

    # ── Guardado en BD ────────────────────────────────────────────────────────
    def _guardar_automatico(self):
        self._guardando = True
        self._detener_camara_silencio()
        threading.Thread(target=self._guardar_en_bd, daemon=True).start()

    def _guardar_en_bd(self):
        try:
            rol = self.rol_actual
            v   = getattr(self, 'valores_form', {})

            def val(key, upper=True):
                texto = v.get(key, "").strip()
                return texto.upper() if upper else texto

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
                    t("fotos_actualizadas"),
                    t("se_actualizaron_fotos").format(len(self.fotos_temp))
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
                'fecha_nacimiento': val('fechaNacimientoUsuario', upper=False),
                'tipo_sangre': val('tipoSangreUsuario', upper=False),
                'direccion': val('direccionUsuario', upper=False)
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

            cfg             = ROL_CONFIG[rol]
            nombre_completo = f"{val('nombreUsuario')} {val('apellidoPaternoUsuario')}"
            self.container.after(0, lambda: self._fin_guardado(
                t("registro_exitoso"),
                f"{cfg['icono']} {nombre_completo} ({cfg['titulo']})\n"
                f"{t('fotos_registradas')} {len(self.fotos_temp)} fotos."
            ))

        except Exception as e:
            self.container.after(0, lambda: messagebox.showerror(
                t("error"), f"{t('error_guardar')} {e}"))
            self._guardando = False

    def _fin_guardado(self, titulo, mensaje):
        messagebox.showinfo(titulo, mensaje)
        self._guardando = False
        self._mostrar_seleccion_rol()

    # ── Helpers cámara ────────────────────────────────────────────────────────
    def _detener_camara_silencio(self):
        self.capturando   = False
        self._auto_activo = False
        if self.camara:
            try:
                self.camara.stop()
            except Exception:
                pass
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
            try:
                self.camara.stop()
            except Exception:
                pass