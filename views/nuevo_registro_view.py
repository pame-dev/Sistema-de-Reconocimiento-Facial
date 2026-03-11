# views/nuevo_registro_view.py
import tkinter as tk
from tkinter import messagebox, ttk
import customtkinter as ctk
import cv2
from PIL import Image, ImageTk
import os
from datetime import datetime
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import COLORS, get_db
from database.queries import (
    sp_insertar_usuario,
    sp_insertar_alumno,
    sp_insertar_maestro,
    sp_insertar_personal,
    sp_insertar_biometria,
)

# ── Configuración de roles ───────────────────────────────────────────────────
ROL_CONFIG = {
    "alumno":   {"icono": "🎓", "titulo": "Alumno",   "desc": "Estudiante inscrito",     "color": "#4A90D9"},
    "maestro":  {"icono": "📚", "titulo": "Maestro",  "desc": "Docente del plantel",     "color": "#27AE60"},
    "personal": {"icono": "🏢", "titulo": "Personal", "desc": "Personal administrativo", "color": "#E67E22"},
}

CAMPOS_POR_ROL = {
    "alumno":   [("Grado:",    "gradoAlumno",    True), ("Grupo:",    "grupoAlumno",    True),
                 ("Facultad:", "facultadAlumno", True), ("Carrera:",  "carreraAlumno",  True)],
    "maestro":  [("Grado que imparte:", "gradoImpartidoMaestro", True),
                 ("Materia:",           "materiaImpartidaMaestro", True)],
    "personal": [("Puesto:", "puestoPersonalEscolar", True), ("Área:", "areaPersonalEscolar", True)],
}

CAMPOS_COMUNES = [
    ("Nombre:",           "nombreUsuario",          True),
    ("Apellido Paterno:", "apellidoPaternoUsuario",  True),
    ("Apellido Materno:", "apellidoMaternoUsuario",  False),
    ("Matrícula:",        "matriculaUsuario",        False),
    ("Teléfono:",         "telefonoUsuario",         True),
    ("Correo:",           "correoUsuario",           True),
]

# ── Posturas de captura ──────────────────────────────────────────────────────
POSTURAS = [
    {
        "id":          "frontal",
        "titulo":      "Postura 1 — Frontal",
        "instruccion": "Mira directamente a la cámara,\nmanteniendo la cabeza recta.",
        "imagen":      "assets/posturas/postura_frontal.png",
        "icono":       "😐",
        "fotos":       80,
    },
    {
        "id":          "izquierda",
        "titulo":      "Postura 2 — Girado a la izquierda",
        "instruccion": "Gira la cabeza ligeramente\nhacia tu izquierda (~30°).",
        "imagen":      "assets/posturas/postura_izquierda.png",
        "icono":       "😶",
        "fotos":       80,
    },
    {
        "id":          "derecha",
        "titulo":      "Postura 3 — Girado a la derecha",
        "instruccion": "Gira la cabeza ligeramente\nhacia tu derecha (~30°).",
        "imagen":      "assets/posturas/postura_derecha.png",
        "icono":       "😶",
        "fotos":       80,
    },
    {
        "id":          "perfil_izq",
        "titulo":      "Postura 4 — Perfil izquierdo",
        "instruccion": "Gira la cabeza completamente\nhacia tu izquierda (~60°).",
        "imagen":      "assets/posturas/postura_perfil_izq.png",
        "icono":       "🙂",
        "fotos":       80,
    },
    {
        "id":          "perfil_der",
        "titulo":      "Postura 5 — Perfil derecho",
        "instruccion": "Gira la cabeza completamente\nhacia tu derecha (~60°).",
        "imagen":      "assets/posturas/postura_perfil_der.png",
        "icono":       "🙂",
        "fotos":       80,
    },
    {
        "id":          "arriba",
        "titulo":      "Postura 6 — Ligeramente hacia abajo",
        "instruccion": "Inclina la cabeza ligeramente\nhacia abajo, como si la\ncámara estuviera en la puerta.",
        "imagen":      "assets/posturas/postura_arriba.png",
        "icono":       "🙄",
        "fotos":       80,
    },
]

TOTAL_FOTOS = sum(p["fotos"] for p in POSTURAS)   # 480


class NuevoRegistroView:
    def __init__(self, parent):
        self.parent   = parent
        self.container = ctk.CTkFrame(parent, fg_color=COLORS['background'])
        self.container.pack(fill="both", expand=True, padx=30, pady=30)

        self.camara        = None
        self.capturando    = False
        self.fotos_temp    = []
        self.rol_actual    = None
        self.entries       = {}

        # Estado de posturas
        self.postura_idx        = 0   # postura actual
        self.fotos_postura      = 0   # fotos tomadas en postura actual
        self.capturando_rafaga  = False
        self.posturas_completadas = []

        self._mostrar_seleccion_rol()

    # ════════════════════════════════════════════════════════════════════════
    # PANTALLA 1 — Selección de rol
    # ════════════════════════════════════════════════════════════════════════

    def _mostrar_seleccion_rol(self):
        self._limpiar_container()

        # Frame centrador que ocupa toda la pantalla
        centro = ctk.CTkFrame(self.container, fg_color="transparent")
        centro.pack(fill="both", expand=True)

        # Centrar contenido vertical y horizontalmente
        inner = ctk.CTkFrame(centro, fg_color="transparent")
        inner.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(
            inner,
            text="📝 Nuevo Registro de Usuario",
            font=("Segoe UI", 30, "bold"),
            text_color=COLORS['text_dark']
        ).pack(pady=(0, 8))

        ctk.CTkLabel(
            inner,
            text="Selecciona el tipo de usuario que deseas registrar",
            font=("Segoe UI", 14),
            text_color=COLORS['text_gray']
        ).pack(pady=(0, 35))

        grid = ctk.CTkFrame(inner, fg_color="transparent")
        grid.pack()

        for idx, (rol_key, cfg) in enumerate(ROL_CONFIG.items()):
            self._crear_tarjeta(grid, rol_key, cfg, 0, idx)

    def _crear_tarjeta(self, parent, rol_key, cfg, row, col):
        color = cfg["color"]
        outer = ctk.CTkFrame(parent, fg_color=color, corner_radius=16)
        outer.grid(row=row, column=col, padx=30, pady=18)
        card  = ctk.CTkFrame(outer, fg_color=COLORS['card_bg'], corner_radius=14)
        card.pack(padx=3, pady=3)

        ctk.CTkLabel(card, text=cfg["icono"], font=("Segoe UI Emoji", 72)).pack(padx=90, pady=(40, 8))
        ctk.CTkLabel(card, text=cfg["titulo"], font=("Segoe UI", 20, "bold"), text_color=color).pack()
        ctk.CTkLabel(card, text=cfg["desc"], font=("Segoe UI", 12), text_color=COLORS['text_gray']).pack(pady=(6, 24))

        ctk.CTkButton(
            card,
            text="Seleccionar",
            fg_color=color,
            hover_color=self._darken(color),
            text_color=COLORS['white'],
            font=("Segoe UI", 12, "bold"),
            corner_radius=10,
            height=40,
            command=lambda r=rol_key: self._seleccionar_rol(r)
        ).pack(pady=(0, 36))

        for w in (outer, card):
            w.bind("<Button-1>", lambda e, r=rol_key: self._seleccionar_rol(r))


    @staticmethod
    def _darken(hex_color, amount=30):
        h    = hex_color.lstrip('#')
        r, g, b = (int(h[i:i+2], 16) for i in (0, 2, 4))
        return f"#{max(0,r-amount):02x}{max(0,g-amount):02x}{max(0,b-amount):02x}"

    def _seleccionar_rol(self, rol_key):
        self.rol_actual = rol_key
        self._mostrar_formulario()

    # ════════════════════════════════════════════════════════════════════════
    # PANTALLA 2 — Formulario
    # ════════════════════════════════════════════════════════════════════════

    def _mostrar_formulario(self):
        self._limpiar_container()
        self.entries = {}

        cfg   = ROL_CONFIG[self.rol_actual]
        color = cfg["color"]

        # Cabecera
        header = ctk.CTkFrame(self.container, fg_color="transparent")
        header.pack(fill="x", pady=(0, 12))

        ctk.CTkButton(
            header,
            text="← Cambiar rol",
            fg_color="transparent",
            hover_color=COLORS['content_bg'],
            text_color=color,
            font=("Segoe UI", 11, "bold"),
            command=self._mostrar_seleccion_rol
        ).pack(side="left")

        badge = ctk.CTkFrame(header, fg_color=color, corner_radius=10)
        badge.pack(side="left", padx=12)
        ctk.CTkLabel(
            badge,
            text=f"  {cfg['icono']}  {cfg['titulo']}  ",
            font=("Segoe UI", 11, "bold"),
            text_color=COLORS['white']
        ).pack(padx=6, pady=4)

        ctk.CTkLabel(
            header,
            text="Paso 1 de 2 — Datos personales",
            font=("Segoe UI", 12),
            text_color=COLORS['text_gray']
        ).pack(side="left", padx=10)

        ttk.Separator(self.container, orient="horizontal").pack(fill="x", pady=(0, 15))

        # Formulario con scroll para evitar que se oculten campos
        form_outer = ctk.CTkFrame(self.container, fg_color="transparent")
        form_outer.pack(fill="both", expand=True)

        scroll = ctk.CTkScrollableFrame(form_outer, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        form_frame = ctk.CTkFrame(
            scroll,
            fg_color=COLORS['card_bg'],
            corner_radius=14,
            border_width=1,
            border_color=COLORS['border'],
            width=920
        )
        form_frame.pack(fill="x", expand=True, padx=24, pady=10)

        self._section_label(form_frame, "Datos personales", color)
        self._add_fields_grid(form_frame, CAMPOS_COMUNES, columns=2)

        campos_rol = CAMPOS_POR_ROL.get(self.rol_actual, [])
        if campos_rol:
            titulos = {"alumno": "Información académica", "maestro": "Información docente",
                       "personal": "Información laboral"}
            self._section_label(form_frame, titulos.get(self.rol_actual, "Datos adicionales"), color)
            self._add_fields_grid(form_frame, campos_rol, columns=2)

        # Botón continuar
        ctk.CTkButton(
            self.container,
            text="Continuar → Captura de fotos",
            fg_color=color,
            hover_color=self._darken(color),
            text_color=COLORS['white'],
            font=("Segoe UI", 13, "bold"),
            corner_radius=10,
            height=42,
            command=self._validar_y_continuar
        ).pack(pady=20)

    def _section_label(self, parent, text, color):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", pady=(14, 6), padx=12)
        ctk.CTkLabel(
            frame,
            text=text,
            text_color=color,
            font=("Segoe UI", 12, "bold")
        ).pack(anchor="w")
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
            text_color=COLORS['text_dark'],
            font=("Segoe UI", 11),
            anchor="w"
        ).pack(anchor="w", pady=(0, 4))
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
        nombre  = self.entries.get('nombreUsuario')
        paterno = self.entries.get('apellidoPaternoUsuario')
        telefono= self.entries.get('telefonoUsuario')
        correo  = self.entries.get('correoUsuario')

        if not nombre or not nombre.get().strip():
            messagebox.showwarning("Campo requerido", "El nombre es obligatorio"); return
        if not paterno or not paterno.get().strip():
            messagebox.showwarning("Campo requerido", "El apellido paterno es obligatorio"); return
        if not telefono or not telefono.get().strip():
            messagebox.showwarning("Campo requerido", "El teléfono es obligatorio"); return
        if not correo or not correo.get().strip():
            messagebox.showwarning("Campo requerido", "El correo es obligatorio"); return

        for _, key, required in CAMPOS_POR_ROL.get(self.rol_actual, []):
            if required and not self.entries.get(key, tk.Entry()).get().strip():
                messagebox.showwarning("Campo requerido", f"El campo '{key}' es obligatorio"); return

        # Guardar valores como strings ANTES de destruir los widgets
        self.valores_form = {key: entry.get().strip() for key, entry in self.entries.items()}

        self._mostrar_captura()

    # ════════════════════════════════════════════════════════════════════════
    # PANTALLA 3 — Captura guiada por posturas
    # ════════════════════════════════════════════════════════════════════════

    def _mostrar_captura(self):
        self._limpiar_container()

        self.fotos_temp           = []
        self.postura_idx          = 0
        self.fotos_postura        = 0
        self.posturas_completadas = []
        self.capturando_rafaga    = False

        cfg   = ROL_CONFIG[self.rol_actual]
        color = cfg["color"]

        # ── Cabecera ──
        header = ctk.CTkFrame(self.container, fg_color="transparent")
        header.pack(fill="x", pady=(0, 10))

        ctk.CTkButton(
            header,
            text="← Volver al formulario",
            fg_color="transparent",
            hover_color=COLORS['content_bg'],
            text_color=color,
            font=("Segoe UI", 11, "bold"),
            command=self._volver_formulario
        ).pack(side="left")

        ctk.CTkLabel(
            header,
            text="Paso 2 de 2 — Captura biométrica",
            font=("Segoe UI", 12),
            text_color=COLORS['text_gray']
        ).pack(side="left", padx=15)

        ttk.Separator(self.container, orient="horizontal").pack(fill="x", pady=(0, 10))

        # ── Progreso general ──
        prog_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        prog_frame.pack(fill="x", pady=(0, 10))

        self.lbl_total = ctk.CTkLabel(
            prog_frame,
            text=f"Total: 0 / {TOTAL_FOTOS}",
            font=("Segoe UI", 11, "bold"),
            text_color=color
        )
        self.lbl_total.pack(side="left", padx=(0, 10))

        self.bar_total = ttk.Progressbar(prog_frame, length=300, maximum=TOTAL_FOTOS)
        self.bar_total.pack(side="left")

        # ── Cuerpo: guía | cámara ──
        body = ctk.CTkFrame(self.container, fg_color="transparent")
        body.pack(fill="both", expand=True)

        # Panel izquierdo — instrucción de postura
        self.panel_guia = ctk.CTkFrame(
            body,
            fg_color=COLORS['card_bg'],
            width=280,
            corner_radius=12,
            border_width=1,
            border_color=COLORS['border']
        )
        self.panel_guia.pack(side="left", fill="y", padx=(0, 15))
        self.panel_guia.pack_propagate(False)
        self._construir_panel_guia(color)

        # Panel derecho — cámara
        cam_panel = ctk.CTkFrame(
            body,
            fg_color=COLORS['card_bg'],
            corner_radius=12,
            border_width=1,
            border_color=COLORS['border']
        )
        cam_panel.pack(side="left", fill="both", expand=True)

        self.video_label = tk.Label(cam_panel, bg=COLORS['content_bg'])
        self.video_label.pack(expand=True, padx=10, pady=10)

        # Controles cámara
        ctrl = ctk.CTkFrame(cam_panel, fg_color="transparent")
        ctrl.pack(fill="x", padx=10, pady=8)

        self.btn_cam = ctk.CTkButton(
            ctrl,
            text="📷 Iniciar Cámara",
            fg_color=color,
            hover_color=self._darken(color),
            text_color=COLORS['white'],
            font=("Segoe UI", 11, "bold"),
            corner_radius=10,
            height=36,
            command=self._iniciar_camara
        )
        self.btn_cam.pack(side="left", padx=5)

        self.btn_tomar = ctk.CTkButton(
            ctrl,
            text="📸 Tomar fotos de esta postura",
            fg_color=COLORS['header'],
            hover_color=COLORS['header_hover'],
            text_color=COLORS['white'],
            font=("Segoe UI", 11, "bold"),
            corner_radius=10,
            height=36,
            state="disabled",
            command=self._iniciar_rafaga
        )
        self.btn_tomar.pack(side="left", padx=5)

        self.btn_repetir = ctk.CTkButton(
            ctrl,
            text="🔁 Repetir postura",
            fg_color=COLORS['accent'],
            hover_color="#D97706",
            text_color=COLORS['white'],
            font=("Segoe UI", 11, "bold"),
            corner_radius=10,
            height=36,
            state="disabled",
            command=self._repetir_postura
        )
        self.btn_repetir.pack(side="left", padx=5)

        self.btn_detener = ctk.CTkButton(
            ctrl,
            text="⏹ Detener",
            fg_color=COLORS['danger'],
            hover_color=COLORS['danger_dark'],
            text_color=COLORS['white'],
            font=("Segoe UI", 11, "bold"),
            corner_radius=10,
            height=36,
            state="disabled",
            command=self._detener_camara
        )
        self.btn_detener.pack(side="left", padx=5)

        # Progreso de postura actual
        pos_prog = ctk.CTkFrame(cam_panel, fg_color="transparent")
        pos_prog.pack(fill="x", padx=10, pady=(0, 8))

        self.lbl_postura_prog = ctk.CTkLabel(
            pos_prog,
            text="Fotos de esta postura: 0 / 80",
            font=("Segoe UI", 11),
            text_color=COLORS['text_dark']
        )
        self.lbl_postura_prog.pack(side="left", padx=5)

        self.bar_postura = ttk.Progressbar(pos_prog, length=220,
                                           maximum=POSTURAS[0]["fotos"])
        self.bar_postura.pack(side="left", padx=5)

        # Estado de ráfaga
        self.lbl_rafaga = ctk.CTkLabel(
            cam_panel,
            text="",
            font=("Segoe UI", 12, "bold"),
            text_color=color
        )
        self.lbl_rafaga.pack(pady=(0, 5))

        # Botón guardar (aparece al final)
        self.btn_guardar = ctk.CTkButton(
            self.container,
            text="💾 Guardar Usuario",
            fg_color=color,
            hover_color=self._darken(color),
            text_color=COLORS['white'],
            font=("Segoe UI", 13, "bold"),
            corner_radius=10,
            height=42,
            state="disabled",
            command=self._guardar_usuario
        )
        self.btn_guardar.pack(pady=15)

    def _construir_panel_guia(self, color):
        """Construye o reconstruye el panel lateral con la postura actual."""
        for w in self.panel_guia.winfo_children():
            w.destroy()

        postura = POSTURAS[self.postura_idx]

        # Título postura
        ctk.CTkLabel(
            self.panel_guia,
            text=postura["titulo"],
            font=("Segoe UI", 12, "bold"),
            text_color=color,
            wraplength=230,
            justify="center"
        ).pack(pady=(15, 8))

        # Imagen de ejemplo (si existe) o ícono grande
        img_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), postura["imagen"])
        img_loaded = False

        if os.path.exists(img_path):
            try:
                img = Image.open(img_path).resize((180, 180), Image.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                lbl_img = tk.Label(self.panel_guia, image=photo, bg=COLORS['card_bg'])
                lbl_img.image = photo   # evitar garbage collection
                lbl_img.pack(pady=8)
                img_loaded = True
            except:
                pass

        if not img_loaded:
            ctk.CTkLabel(
                self.panel_guia,
                text=postura["icono"],
                font=("Segoe UI Emoji", 64)
            ).pack(pady=15)

        # Instrucción
        ctk.CTkLabel(
            self.panel_guia,
            text=postura["instruccion"],
            font=("Segoe UI", 11),
            text_color=COLORS['text_dark'],
            wraplength=220,
            justify="center"
        ).pack(pady=8)

        ttk.Separator(self.panel_guia, orient="horizontal").pack(fill="x", padx=15, pady=10)

        # Mini lista de posturas (completadas / actual / pendientes)
        for i, p in enumerate(POSTURAS):
            if i in self.posturas_completadas:
                icono, fg = "✅", COLORS['primary']
            elif i == self.postura_idx:
                icono, fg = "▶️", color
            else:
                icono, fg = "⬜", COLORS['text_gray']

            ctk.CTkLabel(
                self.panel_guia,
                text=f"{icono} {p['titulo'].split('—')[1].strip()}",
                font=("Segoe UI", 10),
                text_color=fg,
                anchor="w"
            ).pack(fill="x", padx=15, pady=1)

    # ── Cámara ────────────────────────────────────────────────────────────────

    def _iniciar_camara(self):
        try:
            self.camara = cv2.VideoCapture(0)
            if not self.camara.isOpened():
                messagebox.showerror("Error", "No se pudo abrir la cámara"); return

            self.capturando = True
            self.btn_cam.configure(state="disabled")
            self.btn_tomar.configure(state="normal")
            self.btn_detener.configure(state="normal")
            self._actualizar_video()
        except Exception as e:
            messagebox.showerror("Error", f"Error al iniciar cámara: {e}")

    def _actualizar_video(self):
        if not self.capturando or self.camara is None:
            return

        ret, frame = self.camara.read()
        if ret:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w = frame_rgb.shape[:2]
            nw, nh = 420, int(420 / w * h)
            frame_rgb = cv2.resize(frame_rgb, (nw, nh))
            rh, rw = frame_rgb.shape[:2]
            cv2.rectangle(frame_rgb, (rw//4, rh//4), (3*rw//4, 3*rh//4), (0, 255, 0), 2)

            img    = Image.fromarray(frame_rgb)
            imgtk  = ImageTk.PhotoImage(image=img)
            self.video_label.imgtk = imgtk
            self.video_label.config(image=imgtk)

        self.video_label.after(10, self._actualizar_video)

    def _detener_camara(self):
        self.capturando = False
        if self.camara:
            self.camara.release()
            self.camara = None
        if hasattr(self, 'video_label'):
            self.video_label.config(image='')
        if hasattr(self, 'btn_cam'):
            self.btn_cam.configure(state="normal")
            self.btn_tomar.configure(state="disabled")
            self.btn_detener.configure(state="disabled")

    # ── Ráfaga de fotos ───────────────────────────────────────────────────────

    def _iniciar_rafaga(self):
        if self.camara is None or not self.capturando:
            return
        if self.capturando_rafaga:
            return

        self.fotos_postura     = 0
        self.capturando_rafaga = True
        self.btn_tomar.configure(state="disabled")
        self.btn_repetir.configure(state="disabled")

        postura = POSTURAS[self.postura_idx]
        self.lbl_rafaga.configure(text=f"📸 Capturando ráfaga… 0 / {postura['fotos']}")
        self._capturar_siguiente(postura["fotos"])

    def _capturar_siguiente(self, total):
        """Captura una foto y se programa a sí misma para la siguiente."""
        if not self.capturando or self.camara is None:
            self.capturando_rafaga = False
            return

        if self.fotos_postura >= total:
            self._rafaga_completada()
            return

        ret, frame = self.camara.read()
        if ret:
            h, w = frame.shape[:2]
            rostro = cv2.resize(frame[h//4:3*h//4, w//4:3*w//4], (200, 200))
            _, buf = cv2.imencode('.jpg', rostro)
            self.fotos_temp.append(buf.tobytes())
            self.fotos_postura += 1

            # Actualizar barras
            self.bar_postura['value']  = self.fotos_postura
            self.bar_total['value']    = len(self.fotos_temp)
            self.lbl_postura_prog.configure(
                text=f"Fotos de esta postura: {self.fotos_postura} / {total}")
            self.lbl_total.configure(
                text=f"Total: {len(self.fotos_temp)} / {TOTAL_FOTOS}")
            self.lbl_rafaga.configure(
                text=f"📸 Capturando ráfaga… {self.fotos_postura} / {total}")

        # Siguiente foto en 60ms (~16 fps de captura)
        self.video_label.after(30, lambda: self._capturar_siguiente(total))

    def _rafaga_completada(self):
        self.capturando_rafaga = False
        postura = POSTURAS[self.postura_idx]

        self.posturas_completadas.append(self.postura_idx)
        self.lbl_rafaga.configure(text=f"✅ Postura completada ({postura['fotos']} fotos)")
        self.btn_repetir.configure(state="normal")

        # ¿Hay más posturas?
        if self.postura_idx < len(POSTURAS) - 1:
            color = ROL_CONFIG[self.rol_actual]["color"]
            self.btn_tomar.configure(
                text=f"▶ Siguiente postura →",
                state="normal",
                fg_color=color,
                command=self._siguiente_postura
            )
        else:
            # Todas las posturas completadas
            self.btn_tomar.configure(state="disabled")
            self.lbl_rafaga.configure(
                text=f"🎉 ¡Todas las posturas completadas! {len(self.fotos_temp)} fotos en total.")
            self.btn_guardar.configure(state="normal")
            self._construir_panel_guia(ROL_CONFIG[self.rol_actual]["color"])

    def _siguiente_postura(self):
        self.postura_idx   += 1
        self.fotos_postura  = 0
        color = ROL_CONFIG[self.rol_actual]["color"]

        # Actualizar barra de postura
        self.bar_postura.config(maximum=POSTURAS[self.postura_idx]["fotos"])
        self.bar_postura['value'] = 0
        self.lbl_postura_prog.configure(
            text=f"Fotos de esta postura: 0 / {POSTURAS[self.postura_idx]['fotos']}")

        # Restaurar botón tomar
        self.btn_tomar.configure(
            text="📸 Tomar fotos de esta postura",
            fg_color=COLORS['header'],
            command=self._iniciar_rafaga,
            state="normal"
        )
        self.btn_repetir.configure(state="disabled")
        self.lbl_rafaga.configure(text="")

        # Actualizar panel guía
        self._construir_panel_guia(color)

    def _repetir_postura(self):
        """Elimina las fotos de la postura actual y la repite."""
        fotos_a_eliminar = POSTURAS[self.postura_idx]["fotos"]
        if len(self.fotos_temp) >= fotos_a_eliminar:
            self.fotos_temp = self.fotos_temp[:-fotos_a_eliminar]

        # Quitar de completadas
        if self.postura_idx in self.posturas_completadas:
            self.posturas_completadas.remove(self.postura_idx)

        self.fotos_postura = 0
        self.bar_postura['value'] = 0
        self.bar_total['value']   = len(self.fotos_temp)
        self.lbl_total.configure(text=f"Total: {len(self.fotos_temp)} / {TOTAL_FOTOS}")
        self.lbl_postura_prog.configure(
            text=f"Fotos de esta postura: 0 / {POSTURAS[self.postura_idx]['fotos']}")
        self.lbl_rafaga.configure(text="🔁 Postura reiniciada. Presiona 'Tomar fotos' cuando estés listo.")

        color = ROL_CONFIG[self.rol_actual]["color"]
        self.btn_tomar.configure(
            text="📸 Tomar fotos de esta postura",
            fg_color=COLORS['header'],
            command=self._iniciar_rafaga,
            state="normal"
        )
        self.btn_repetir.configure(state="disabled")
        self.btn_guardar.configure(state="disabled")
        self._construir_panel_guia(color)

    # ── Navegación ────────────────────────────────────────────────────────────

    def _volver_formulario(self):
        self._detener_camara()
        self._mostrar_formulario()

    def _limpiar_container(self):
        for w in self.container.winfo_children():
            w.destroy()

    # ── Guardar en BD ─────────────────────────────────────────────────────────


    def _guardar_usuario(self):
        try:
            rol = self.rol_actual
            v   = getattr(self, 'valores_form', {})  # valores guardados como strings

            def val(key, upper=True):
                t = v.get(key, "").strip()
                return t.upper() if upper else t

            nombre    = val('nombreUsuario')
            paterno   = val('apellidoPaternoUsuario')
            materno   = val('apellidoMaternoUsuario')
            matricula = val('matriculaUsuario', upper=False)
            telefono  = val('telefonoUsuario',  upper=False)
            correo    = val('correoUsuario',    upper=False)

            conn    = get_db()
            ahora   = datetime.now()
            
            # ── SI SOLO ESTAMOS RETOMANDO FOTOS ──
            if getattr(self, "modo_retomar_fotos", False):

                user_id = self.user_id_existente

                cursor = conn.cursor()
                cursor.execute("DELETE FROM biometria WHERE fkIdUsuario = ?", (user_id,))

                for foto_bytes in self.fotos_temp:
                    sp_insertar_biometria(conn, user_id, foto_bytes, ahora)

                conn.commit()
                conn.close()

                messagebox.showinfo(
                    "Fotos actualizadas",
                    f"Se actualizaron {len(self.fotos_temp)} fotos del usuario."
                )

                self._detener_camara()
                self._mostrar_seleccion_rol()
                return

            # sp_insertar_usuario
            user_id = sp_insertar_usuario(conn, {
                'nombre':    nombre,
                'paterno':   paterno,
                'materno':   materno,
                'matricula': matricula,
                'rol':       rol,
                'telefono':  telefono,
                'correo':    correo,
            })

            # sp_insertar_<rol>
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

            # sp_insertar_biometria (una por foto)
            for foto_bytes in self.fotos_temp:
                sp_insertar_biometria(conn, user_id, foto_bytes, ahora)

            conn.commit()
            conn.close()

            cfg = ROL_CONFIG[rol]
            messagebox.showinfo("✅ Registro exitoso",
                f"{cfg['icono']} {nombre} {paterno} ({cfg['titulo']})\n"
                f"Registrado con {len(self.fotos_temp)} fotos en {len(POSTURAS)} posturas.")

            self._detener_camara()
            self._mostrar_seleccion_rol()

        except Exception as e:
            messagebox.showerror("Error", f"Error al guardar: {e}")

    def __del__(self):
        if self.camara:
            self.camara.release()