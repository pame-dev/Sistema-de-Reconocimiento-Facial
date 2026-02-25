# views/nuevo_registro_view.py
import tkinter as tk
from tkinter import messagebox, ttk
import cv2
from PIL import Image, ImageTk
import os
from datetime import datetime
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import COLORS, get_db

# ── Configuración de roles ───────────────────────────────────────────────────
ROL_CONFIG = {
    "alumno": {
        "icono":  "🎓",
        "titulo": "Alumno",
        "desc":   "Estudiante inscrito",
        "color":  "#4A90D9",
    },
    "maestro": {
        "icono":  "📚",
        "titulo": "Maestro",
        "desc":   "Docente del plantel",
        "color":  "#27AE60",
    },
    "personal": {
        "icono":  "🏢",
        "titulo": "Personal",
        "desc":   "Personal administrativo",
        "color":  "#E67E22",
    },
    "admin": {
        "icono":  "🔑",
        "titulo": "Administrador",
        "desc":   "Acceso total al sistema",
        "color":  "#8E44AD",
    },
}

CAMPOS_POR_ROL = {
    "alumno": [
        ("Grado:",    "gradoAlumno",    True),
        ("Grupo:",    "grupoAlumno",    True),
        ("Facultad:", "facultadAlumno", True),
        ("Carrera:",  "carreraAlumno",  True),
    ],
    "maestro": [
        ("Grado que imparte:", "gradoImpartidoMaestro",   True),
        ("Materia:",           "materiaImpartidaMaestro", True),
    ],
    "personal": [
        ("Puesto:", "puestoPersonalEscolar", True),
        ("Área:",   "areaPersonalEscolar",   True),
    ],
    "admin": [],
}

CAMPOS_COMUNES = [
    ("Nombre:",           "nombreUsuario",          True),
    ("Apellido Paterno:", "apellidoPaternoUsuario",  True),
    ("Apellido Materno:", "apellidoMaternoUsuario",  False),
    ("Matrícula:",        "matriculaUsuario",        False),
    ("Teléfono:",         "telefonoUsuario",         True),
    ("Correo:",           "correoUsuario",           True),
]


class NuevoRegistroView:
    """Vista para registrar nuevos usuarios en el sistema."""

    def __init__(self, parent):
        self.parent = parent
        self.container = tk.Frame(parent, bg=COLORS['white'])
        self.container.pack(fill="both", expand=True, padx=30, pady=30)

        self.camara        = None
        self.capturando    = False
        self.fotos_tomadas = 0
        self.fotos_temp    = []
        self.rol_actual    = None
        self.entries       = {}

        self._mostrar_seleccion_rol()

    # ════════════════════════════════════════════════════════════════════════
    # PANTALLA 1 — Selección de rol
    # ════════════════════════════════════════════════════════════════════════

    def _mostrar_seleccion_rol(self):
        self._limpiar_container()

        tk.Label(
            self.container,
            text="📝 Nuevo Registro de Usuario",
            font=("Arial", 22, "bold"),
            bg=COLORS['white'],
            fg=COLORS['text_dark']
        ).pack(pady=(0, 6))

        tk.Label(
            self.container,
            text="Selecciona el tipo de usuario que deseas registrar",
            font=("Arial", 12),
            bg=COLORS['white'],
            fg=COLORS['text_gray']
        ).pack(pady=(0, 30))

        # Grid 2×2 de tarjetas
        grid = tk.Frame(self.container, bg=COLORS['white'])
        grid.pack()

        for idx, (rol_key, cfg) in enumerate(ROL_CONFIG.items()):
            row, col = divmod(idx, 2)
            self._crear_tarjeta(grid, rol_key, cfg, row, col)

    def _crear_tarjeta(self, parent, rol_key, cfg, row, col):
        color = cfg["color"]

        # Borde de color
        outer = tk.Frame(parent, bg=color)
        outer.grid(row=row, column=col, padx=18, pady=18)

        # Cuerpo blanco
        card = tk.Frame(outer, bg=COLORS['white'], cursor="hand2")
        card.pack(padx=3, pady=3)

        tk.Label(card, text=cfg["icono"], font=("Arial", 44),
                 bg=COLORS['white']).pack(padx=55, pady=(24, 4))

        tk.Label(card, text=cfg["titulo"], font=("Arial", 15, "bold"),
                 bg=COLORS['white'], fg=color).pack()

        tk.Label(card, text=cfg["desc"], font=("Arial", 10),
                 bg=COLORS['white'], fg=COLORS['text_gray']).pack(pady=(2, 16))

        tk.Button(
            card,
            text="Seleccionar",
            bg=color, fg=COLORS['white'],
            font=("Arial", 10, "bold"),
            relief="flat", padx=22, pady=6,
            cursor="hand2",
            command=lambda r=rol_key: self._seleccionar_rol(r)
        ).pack(pady=(0, 20))

        # Click en toda la tarjeta
        for w in (outer, card):
            w.bind("<Button-1>", lambda e, r=rol_key: self._seleccionar_rol(r))
            w.bind("<Enter>",    lambda e, o=outer, c=color: o.config(bg=self._darken(c)))
            w.bind("<Leave>",    lambda e, o=outer, c=color: o.config(bg=c))

    @staticmethod
    def _darken(hex_color, amount=30):
        h = hex_color.lstrip('#')
        r, g, b = (int(h[i:i+2], 16) for i in (0, 2, 4))
        return f"#{max(0,r-amount):02x}{max(0,g-amount):02x}{max(0,b-amount):02x}"

    def _seleccionar_rol(self, rol_key):
        self.rol_actual = rol_key
        self._mostrar_formulario()

    # ════════════════════════════════════════════════════════════════════════
    # PANTALLA 2 — Formulario + cámara
    # ════════════════════════════════════════════════════════════════════════

    def _mostrar_formulario(self):
        self._limpiar_container()
        self.entries       = {}
        self.fotos_tomadas = 0
        self.fotos_temp    = []

        cfg   = ROL_CONFIG[self.rol_actual]
        color = cfg["color"]

        # ── Cabecera ──
        header = tk.Frame(self.container, bg=COLORS['white'])
        header.pack(fill="x", pady=(0, 12))

        tk.Button(
            header,
            text="← Cambiar rol",
            bg=COLORS['white'], fg=color,
            font=("Arial", 10, "bold"),
            relief="flat", cursor="hand2",
            command=self._volver_seleccion
        ).pack(side="left")

        badge = tk.Frame(header, bg=color)
        badge.pack(side="left", padx=12)
        tk.Label(
            badge,
            text=f"  {cfg['icono']}  {cfg['titulo']}  ",
            font=("Arial", 11, "bold"),
            bg=color, fg=COLORS['white'], pady=4
        ).pack()

        tk.Label(
            header,
            text="Completa el formulario y toma las fotos",
            font=("Arial", 11),
            bg=COLORS['white'], fg=COLORS['text_gray']
        ).pack(side="left", padx=10)

        ttk.Separator(self.container, orient="horizontal").pack(fill="x", pady=(0, 12))

        # ── Cuerpo ──
        main_frame = tk.Frame(self.container, bg=COLORS['white'])
        main_frame.pack(fill="both", expand=True)

        # Formulario izquierda
        form_frame = tk.Frame(main_frame, bg=COLORS['white'], width=420)
        form_frame.pack(side="left", fill="both", expand=True, padx=(0, 20))
        form_frame.pack_propagate(False)
        self._build_form(form_frame, color)

        # Cámara derecha
        self.cam_frame = tk.Frame(main_frame, bg=COLORS['content_bg'], relief="solid", borderwidth=1)
        self.cam_frame.pack(side="right", fill="both", expand=True)
        self._build_camera_area(color)

        # Botón guardar
        self.btn_guardar = tk.Button(
            self.container,
            text="💾 Guardar Usuario",
            bg=color, fg=COLORS['white'],
            font=("Arial", 12, "bold"),
            relief="flat", padx=30, pady=10,
            state="disabled",
            command=self.guardar_usuario
        )
        self.btn_guardar.pack(pady=18)

    def _build_form(self, parent, color):
        self._section_label(parent, "Datos personales", color)
        for label_text, key, required in CAMPOS_COMUNES:
            self._add_entry(parent, label_text, key, required)

        campos_rol = CAMPOS_POR_ROL.get(self.rol_actual, [])
        if campos_rol:
            titulos = {
                "alumno":   "Información académica",
                "maestro":  "Información docente",
                "personal": "Información laboral",
            }
            self._section_label(parent, titulos.get(self.rol_actual, "Datos adicionales"), color)
            for label_text, key, required in campos_rol:
                self._add_entry(parent, label_text, key, required)

    def _section_label(self, parent, text, color):
        frame = tk.Frame(parent, bg=COLORS['white'])
        frame.pack(fill="x", pady=(14, 4))
        tk.Label(frame, text=text, bg=COLORS['white'], fg=color,
                 font=("Arial", 11, "bold")).pack(anchor="w")
        ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=(3, 0))

    def _add_entry(self, parent, label_text, key, required):
        frame = tk.Frame(parent, bg=COLORS['white'])
        frame.pack(fill="x", pady=4)
        tk.Label(
            frame,
            text=label_text + (" *" if required else ""),
            bg=COLORS['white'], fg=COLORS['text_dark'],
            font=("Arial", 11), width=18, anchor="w"
        ).pack(side="left")
        entry = tk.Entry(frame, font=("Arial", 11), relief="solid", borderwidth=1)
        entry.pack(side="left", fill="x", expand=True, padx=(5, 0))
        self.entries[key] = entry

    def _build_camera_area(self, color):
        self.video_label = tk.Label(self.cam_frame, bg=COLORS['content_bg'])
        self.video_label.pack(expand=True, padx=10, pady=10)

        controls = tk.Frame(self.cam_frame, bg=COLORS['content_bg'])
        controls.pack(fill="x", padx=10, pady=5)

        self.btn_iniciar_cam = tk.Button(
            controls, text="📷 Iniciar Cámara",
            bg=color, fg=COLORS['white'],
            font=("Arial", 10, "bold"), relief="flat", padx=15, pady=6,
            command=self.iniciar_camara
        )
        self.btn_iniciar_cam.pack(side="left", padx=5)

        self.btn_capturar = tk.Button(
            controls, text="📸 Capturar Foto",
            bg=COLORS['header'], fg=COLORS['white'],
            font=("Arial", 10, "bold"), relief="flat", padx=15, pady=6,
            state="disabled", command=self.capturar_foto
        )
        self.btn_capturar.pack(side="left", padx=5)

        self.btn_detener = tk.Button(
            controls, text="⏹️ Detener",
            bg=COLORS['danger'], fg=COLORS['white'],
            font=("Arial", 10, "bold"), relief="flat", padx=15, pady=6,
            state="disabled", command=self.detener_camara
        )
        self.btn_detener.pack(side="left", padx=5)

        prog_frame = tk.Frame(self.cam_frame, bg=COLORS['content_bg'])
        prog_frame.pack(fill="x", padx=10, pady=5)

        self.progreso_label = tk.Label(
            prog_frame, text="Fotos: 0/20",
            bg=COLORS['content_bg'], fg=COLORS['text_dark'], font=("Arial", 10)
        )
        self.progreso_label.pack(side="left", padx=5)

        self.progreso_bar = ttk.Progressbar(prog_frame, length=200, maximum=20)
        self.progreso_bar.pack(side="left", padx=5)

        self.instrucciones_label = tk.Label(
            self.cam_frame,
            text="1. Completa el formulario\n2. Inicia la cámara\n3. Toma 20 fotos desde diferentes ángulos",
            bg=COLORS['content_bg'], fg=COLORS['text_gray'],
            font=("Arial", 10), justify="left"
        )
        self.instrucciones_label.pack(pady=10)

    # ── Navegación ────────────────────────────────────────────────────────────

    def _volver_seleccion(self):
        self.detener_camara()
        self._mostrar_seleccion_rol()

    def _limpiar_container(self):
        for w in self.container.winfo_children():
            w.destroy()

    # ── Cámara ────────────────────────────────────────────────────────────────

    def iniciar_camara(self):
        try:
            self.camara = cv2.VideoCapture(0)
            if not self.camara.isOpened():
                messagebox.showerror("Error", "No se pudo abrir la cámara")
                return
            self.capturando = True
            self.btn_iniciar_cam.config(state="disabled")
            self.btn_capturar.config(state="normal")
            self.btn_detener.config(state="normal")
            self.instrucciones_label.config(
                text="📸 Toma 20 fotos desde diferentes ángulos\nPresiona 'Capturar Foto' para cada una"
            )
            self.actualizar_video()
        except Exception as e:
            messagebox.showerror("Error", f"Error al iniciar cámara: {e}")

    def actualizar_video(self):
        if self.capturando and self.camara is not None:
            ret, frame = self.camara.read()
            if ret:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w = frame_rgb.shape[:2]
                nw = 400
                nh = int((nw / w) * h)
                frame_rgb = cv2.resize(frame_rgb, (nw, nh))
                rh, rw = frame_rgb.shape[:2]
                cv2.rectangle(frame_rgb, (rw//4, rh//4), (3*rw//4, 3*rh//4), (0, 255, 0), 2)
                img   = Image.fromarray(frame_rgb)
                imgtk = ImageTk.PhotoImage(image=img)
                self.video_label.imgtk = imgtk
                self.video_label.config(image=imgtk)
            self.video_label.after(10, self.actualizar_video)

    def capturar_foto(self):
        if self.camara is None or not self.capturando:
            return
        ret, frame = self.camara.read()
        if ret:
            self.fotos_tomadas += 1
            self.progreso_bar['value'] = self.fotos_tomadas
            self.progreso_label.config(text=f"Fotos: {self.fotos_tomadas}/20")

            h, w = frame.shape[:2]
            rostro = cv2.resize(frame[h//4:3*h//4, w//4:3*w//4], (200, 200))
            _, buf = cv2.imencode('.jpg', rostro)
            self.fotos_temp.append(buf.tobytes())

            if self.fotos_tomadas >= 20:
                self.btn_capturar.config(state="disabled")
                self.instrucciones_label.config(text="✅ ¡20 fotos capturadas!\nAhora puedes guardar el usuario")
                self.verificar_datos_completos()

    def detener_camara(self):
        self.capturando = False
        if self.camara is not None:
            self.camara.release()
            self.camara = None
        if hasattr(self, 'video_label'):
            self.video_label.config(image='')
        if hasattr(self, 'btn_iniciar_cam'):
            self.btn_iniciar_cam.config(state="normal")
            self.btn_capturar.config(state="disabled")
            self.btn_detener.config(state="disabled")

    # ── Validación y guardado ─────────────────────────────────────────────────

    def verificar_datos_completos(self):
        n = self.entries.get('nombreUsuario')
        p = self.entries.get('apellidoPaternoUsuario')
        if n and p and n.get().strip() and p.get().strip() and len(self.fotos_temp) >= 20:
            self.btn_guardar.config(state="normal")

    def guardar_usuario(self):
        try:
            rol = self.rol_actual

            def val(key, upper=True):
                v = self.entries.get(key)
                t = v.get().strip() if v else ""
                return t.upper() if upper else t

            nombre    = val('nombreUsuario')
            paterno   = val('apellidoPaternoUsuario')
            materno   = val('apellidoMaternoUsuario')
            matricula = val('matriculaUsuario', upper=False)
            telefono  = val('telefonoUsuario',  upper=False)
            correo    = val('correoUsuario',    upper=False)

            if not nombre or not paterno:
                messagebox.showwarning("Campos incompletos", "Nombre y Apellido Paterno son obligatorios")
                return
            if not telefono or not correo:
                messagebox.showwarning("Campos incompletos", "Teléfono y Correo son obligatorios")
                return
            for _, key, required in CAMPOS_POR_ROL.get(rol, []):
                if required and not self.entries.get(key, tk.Entry()).get().strip():
                    messagebox.showwarning("Campos incompletos", f"El campo '{key}' es obligatorio")
                    return
            if len(self.fotos_temp) < 20:
                messagebox.showwarning("Fotos insuficientes", "Debes tomar al menos 20 fotos")
                return

            conn   = get_db()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO usuarios (
                    nombreUsuario, apellidoPaternoUsuario, apellidoMaternoUsuario,
                    matriculaUsuario, rolUsuario, estadoUsuario,
                    telefonoUsuario, correoUsuario
                ) VALUES (?, ?, ?, ?, ?, 'activo', ?, ?)
            """, (nombre, paterno, materno, matricula, rol, telefono, correo))
            user_id = cursor.lastrowid

            if rol == "alumno":
                cursor.execute("""
                    INSERT INTO alumnos (fkIdUsuario, gradoAlumno, grupoAlumno, facultadAlumno, carreraAlumno)
                    VALUES (?, ?, ?, ?, ?)
                """, (user_id,
                      self.entries['gradoAlumno'].get().strip(),
                      self.entries['grupoAlumno'].get().strip(),
                      self.entries['facultadAlumno'].get().strip().upper(),
                      self.entries['carreraAlumno'].get().strip().upper()))

            elif rol == "maestro":
                cursor.execute("""
                    INSERT INTO maestros (fkIdUsuario, gradoImpartidoMaestro, materiaImpartidaMaestro)
                    VALUES (?, ?, ?)
                """, (user_id,
                      self.entries['gradoImpartidoMaestro'].get().strip(),
                      self.entries['materiaImpartidaMaestro'].get().strip().upper()))

            elif rol == "personal":
                cursor.execute("""
                    INSERT INTO personal_escolar (fkIdUsuario, puestoPersonalEscolar, areaPersonalEscolar)
                    VALUES (?, ?, ?)
                """, (user_id,
                      self.entries['puestoPersonalEscolar'].get().strip().upper(),
                      self.entries['areaPersonalEscolar'].get().strip().upper()))

            ahora = datetime.now()
            for foto_bytes in self.fotos_temp:
                cursor.execute("""
                    INSERT INTO biometria (
                        fkIdUsuario, encodeBiometria,
                        fechaHoraRegistroBiometria, fechaHoraActualizacionBiometria
                    ) VALUES (?, ?, ?, ?)
                """, (user_id, foto_bytes, ahora, ahora))

            conn.commit()
            conn.close()

            cfg = ROL_CONFIG[rol]
            messagebox.showinfo(
                "Éxito",
                f"✅ {cfg['icono']} {nombre} {paterno} ({cfg['titulo']}) registrado con {len(self.fotos_temp)} fotos"
            )
            self.detener_camara()
            self._mostrar_seleccion_rol()

        except Exception as e:
            messagebox.showerror("Error", f"Error al guardar: {e}")

    def __del__(self):
        if self.camara is not None:
            self.camara.release()