# views/informacion_escolar_view.py
import tkinter as tk
from tkinter import ttk, messagebox
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import COLORS, get_db

class InformacionEscolarView:
    """Vista para consultar y gestionar información escolar"""

    def __init__(self, parent):
        self.parent = parent
        self.container = tk.Frame(parent, bg=COLORS['white'])
        self.container.pack(fill="both", expand=True, padx=30, pady=30)

        self.usuario_seleccionado = None
        self.datos = []
        self._placeholder_activo = True  # ← controla si el placeholder está visible

        self.crear_interfaz()
        
    def crear_interfaz(self):
        # === CABECERA ===
        header_frame = tk.Frame(self.container, bg=COLORS['white'])
        header_frame.pack(fill="x", pady=(0, 20))

        tk.Label(
            header_frame,
            text="📚 Información Escolar",
            font=("Arial", 20, "bold"),
            bg=COLORS['white'],
            fg=COLORS['text_dark']
        ).pack(side="left")

        self.btn_actualizar = tk.Button(
            header_frame,
            text="🔄 Actualizar",
            bg=COLORS['primary'],
            fg=COLORS['white'],
            font=("Arial", 10),
            relief="flat",
            padx=15,
            pady=5,
            command=self.cargar_datos
        )
        self.btn_actualizar.pack(side="right")

        # === FILTROS ===
        filtros_frame = tk.Frame(self.container, bg=COLORS['white'])
        filtros_frame.pack(fill="x", pady=(0, 15))

        tk.Label(
            filtros_frame,
            text="Buscar:",
            bg=COLORS['white'],
            fg=COLORS['text_dark'],
            font=("Arial", 11)
        ).pack(side="left", padx=(0, 5))

        self.busqueda_var = tk.StringVar()
        # IMPORTANTE: NO usar trace aquí, usamos KeyRelease en el widget
        self.entrada_busqueda = tk.Entry(
            filtros_frame,
            textvariable=self.busqueda_var,
            font=("Arial", 11),
            width=30,
            relief="solid",
            borderwidth=1,
            fg=COLORS['text_gray']
        )
        self.entrada_busqueda.pack(side="left", padx=(0, 15))
        self.entrada_busqueda.insert(0, "Nombre, matrícula o carrera...")
        self.entrada_busqueda.bind("<FocusIn>",   self.limpiar_placeholder)
        self.entrada_busqueda.bind("<FocusOut>",  self.restaurar_placeholder)
        self.entrada_busqueda.bind("<KeyRelease>", lambda e: self.filtrar_tabla())

        tk.Label(
            filtros_frame,
            text="Rol:",
            bg=COLORS['white'],
            fg=COLORS['text_dark'],
            font=("Arial", 11)
        ).pack(side="left", padx=(0, 5))

        self.filtro_rol = ttk.Combobox(
            filtros_frame,
            values=["Todos", "alumno", "maestro", "personal"],
            state="readonly",
            width=15,
            font=("Arial", 11)
        )
        self.filtro_rol.set("Todos")
        self.filtro_rol.pack(side="left")
        self.filtro_rol.bind('<<ComboboxSelected>>', lambda e: self.filtrar_tabla())

        # === TABLA ===
        tabla_frame = tk.Frame(self.container, bg=COLORS['white'])
        tabla_frame.pack(fill="both", expand=True, pady=(0, 15))

        scroll_y = tk.Scrollbar(tabla_frame)
        scroll_y.pack(side="right", fill="y")

        scroll_x = tk.Scrollbar(tabla_frame, orient="horizontal")
        scroll_x.pack(side="bottom", fill="x")

        self.tabla = ttk.Treeview(
            tabla_frame,
            columns=("id", "nombre", "matricula", "rol", "carrera", "grado", "grupo", "fotos"),
            show="headings",
            yscrollcommand=scroll_y.set,
            xscrollcommand=scroll_x.set,
            height=15
        )

        scroll_y.config(command=self.tabla.yview)
        scroll_x.config(command=self.tabla.xview)

        self.tabla.heading("id",        text="ID")
        self.tabla.heading("nombre",    text="Nombre Completo")
        self.tabla.heading("matricula", text="Matrícula")
        self.tabla.heading("rol",       text="Rol")
        self.tabla.heading("carrera",   text="Carrera/Materia")
        self.tabla.heading("grado",     text="Grado")
        self.tabla.heading("grupo",     text="Grupo")
        self.tabla.heading("fotos",     text="Fotos")

        self.tabla.column("id",        width=50,  anchor="center")
        self.tabla.column("nombre",    width=250)
        self.tabla.column("matricula", width=120, anchor="center")
        self.tabla.column("rol",       width=100, anchor="center")
        self.tabla.column("carrera",   width=200)
        self.tabla.column("grado",     width=80,  anchor="center")
        self.tabla.column("grupo",     width=80,  anchor="center")
        self.tabla.column("fotos",     width=80,  anchor="center")

        self.tabla.pack(fill="both", expand=True)
        self.tabla.bind('<<TreeviewSelect>>', self.on_select)

        # === PANEL DETALLES ===
        self.detalles_frame = tk.Frame(self.container, bg=COLORS['content_bg'], relief="solid", borderwidth=1)
        self.detalles_frame.pack(fill="x", pady=(0, 15))
        self.crear_panel_detalles()

        # === BOTONES ACCIÓN ===
        acciones_frame = tk.Frame(self.container, bg=COLORS['white'])
        acciones_frame.pack(fill="x")

        self.btn_editar = tk.Button(
            acciones_frame, text="✏️ Editar Información",
            bg=COLORS['header'], fg=COLORS['white'],
            font=("Arial", 11), relief="flat", padx=20, pady=8,
            state="disabled", command=self.editar_usuario
        )
        self.btn_editar.pack(side="left", padx=5)

        self.btn_ver_fotos = tk.Button(
            acciones_frame, text="📸 Ver Fotos",
            bg=COLORS['primary'], fg=COLORS['white'],
            font=("Arial", 11), relief="flat", padx=20, pady=8,
            state="disabled", command=self.ver_fotos
        )
        self.btn_ver_fotos.pack(side="left", padx=5)

        self.btn_historial = tk.Button(
            acciones_frame, text="📊 Historial de Accesos",
            bg=COLORS['info'], fg=COLORS['white'],
            font=("Arial", 11), relief="flat", padx=20, pady=8,
            state="disabled", command=self.ver_historial
        )
        self.btn_historial.pack(side="left", padx=5)

    # ── Panel de detalles ────────────────────────────────────────────────────

    def crear_panel_detalles(self):
        for widget in self.detalles_frame.winfo_children():
            widget.destroy()

        tk.Label(
            self.detalles_frame,
            text="📋 Detalles del Usuario",
            font=("Arial", 12, "bold"),
            bg=COLORS['content_bg'],
            fg=COLORS['text_dark']
        ).pack(anchor="w", padx=15, pady=(10, 5))

        info_frame = tk.Frame(self.detalles_frame, bg=COLORS['content_bg'])
        info_frame.pack(fill="x", padx=15, pady=5)

        if self.usuario_seleccionado:
            self.mostrar_detalles_usuario(info_frame)
        else:
            tk.Label(
                info_frame,
                text="Selecciona un usuario para ver sus detalles",
                bg=COLORS['content_bg'],
                fg=COLORS['text_gray'],
                font=("Arial", 11, "italic")
            ).pack(pady=15)

    def mostrar_detalles_usuario(self, parent):
        if not self.usuario_seleccionado:
            return
        u = self.usuario_seleccionado
        self.crear_fila_detalle(parent, "Nombre:",    u.get('nombre', ''),              0)
        self.crear_fila_detalle(parent, "Matrícula:", u.get('matricula', ''),           1)
        self.crear_fila_detalle(parent, "Rol:",       u.get('rol', ''),                 2)
        self.crear_fila_detalle(parent, "Teléfono:",  u.get('telefono', 'N/A'),         3)

        if u.get('rol') == 'alumno':
            self.crear_fila_detalle(parent, "Carrera:",    u.get('carrera', 'N/A'),     4)
            self.crear_fila_detalle(parent, "Grado/Grupo:", f"{u.get('grado','')}° {u.get('grupo','')}", 5)
            self.crear_fila_detalle(parent, "Facultad:",   u.get('facultad', 'N/A'),    6)

        stats = tk.Frame(parent, bg=COLORS['content_bg'])
        stats.grid(row=7, column=0, columnspan=2, pady=(10, 0), sticky="w")
        tk.Label(stats, text=f"📸 Fotos: {u.get('fotos', 0)}",
                 bg=COLORS['content_bg'], fg=COLORS['primary'],
                 font=("Arial", 10, "bold")).pack(side="left", padx=(0, 20))
        tk.Label(stats, text=f"🔐 Accesos: {u.get('accesos', 0)}",
                 bg=COLORS['content_bg'], fg=COLORS['header'],
                 font=("Arial", 10, "bold")).pack(side="left")

    def crear_fila_detalle(self, parent, label, valor, fila):
        tk.Label(parent, text=label, bg=COLORS['content_bg'], fg=COLORS['text_gray'],
                 font=("Arial", 10), width=15, anchor="w"
                 ).grid(row=fila, column=0, sticky="w", pady=2)
        tk.Label(parent, text=valor, bg=COLORS['content_bg'], fg=COLORS['text_dark'],
                 font=("Arial", 10, "bold"), anchor="w"
                 ).grid(row=fila, column=1, sticky="w", pady=2, padx=(10, 0))

    # ── Carga y filtrado ─────────────────────────────────────────────────────

    def cargar_datos(self):
        try:
            conn = get_db()
            if not conn:
                messagebox.showerror("Error", "No se pudo conectar a la base de datos")
                return

            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    u.idUsuario,
                    u.nombreUsuario,
                    u.apellidoPaternoUsuario,
                    u.apellidoMaternoUsuario,
                    u.matriculaUsuario,
                    u.rolUsuario,
                    u.telefonoUsuario,
                    a.carreraAlumno,
                    a.gradoAlumno,
                    a.grupoAlumno,
                    a.facultadAlumno,
                    m.materiaImpartidaMaestro,
                    m.gradoImpartidoMaestro,
                    p.puestoPersonalEscolar,
                    p.areaPersonalEscolar,
                    COUNT(DISTINCT b.idBiometria)  as total_fotos,
                    COUNT(DISTINCT ac.idAcceso)    as total_accesos
                FROM usuarios u
                LEFT JOIN alumnos         a  ON u.idUsuario = a.fkIdUsuario
                LEFT JOIN maestros        m  ON u.idUsuario = m.fkIdUsuario
                LEFT JOIN personal_escolar p ON u.idUsuario = p.fkIdUsuario
                LEFT JOIN biometria       b  ON u.idUsuario = b.fkIdUsuario
                LEFT JOIN accesos         ac ON u.idUsuario = ac.fkIdUsuario
                GROUP BY u.idUsuario
                ORDER BY u.idUsuario
            """)
            resultados = cursor.fetchall()
            conn.close()

            self.datos = []
            for row in resultados:
                rol = row[5]
                if rol == 'alumno':
                    carrera = row[7] or 'No especificada'
                    grado   = row[8] or '-'
                    grupo   = row[9] or '-'
                elif rol == 'maestro':
                    carrera = row[11] or 'No especificada'
                    grado   = row[12] or '-'
                    grupo   = '-'
                else:
                    carrera = row[13] or '-'
                    grado   = '-'
                    grupo   = '-'

                self.datos.append({
                    'id':       row[0],
                    'nombre':   f"{row[1]} {row[2] or ''} {row[3] or ''}".strip(),
                    'matricula':row[4] or 'N/A',
                    'rol':      rol,
                    'telefono': row[6] or 'N/A',
                    'carrera':  carrera,
                    'grado':    grado,
                    'grupo':    grupo,
                    'facultad': row[10] if rol == 'alumno' else 'N/A',
                    'fotos':    row[15] or 0,
                    'accesos':  row[16] or 0,
                })

            self.actualizar_tabla()

        except Exception as e:
            messagebox.showerror("Error", f"Error al cargar datos: {e}")
            self.datos = []

    def actualizar_tabla(self, datos_filtrados=None):
        for item in self.tabla.get_children():
            self.tabla.delete(item)

        for u in (datos_filtrados if datos_filtrados is not None else self.datos):
            self.tabla.insert("", "end", values=(
                u['id'], u['nombre'], u['matricula'], u['rol'],
                u['carrera'], u['grado'], u['grupo'], u['fotos']
            ))

    def filtrar_tabla(self):
        # Si el placeholder está activo, no hay texto real → mostrar todo
        if self._placeholder_activo:
            self.actualizar_tabla()
            return

        texto = self.busqueda_var.get().lower().strip()
        rol_filtro = self.filtro_rol.get()

        resultado = [
            u for u in self.datos
            if (rol_filtro == "Todos" or u['rol'] == rol_filtro)
            and (not texto or
                 texto in u['nombre'].lower() or
                 texto in u['matricula'].lower() or
                 texto in u['carrera'].lower())
        ]
        self.actualizar_tabla(resultado)

    # ── Placeholder ──────────────────────────────────────────────────────────

    def limpiar_placeholder(self, event):
        if self._placeholder_activo:
            self.entrada_busqueda.delete(0, tk.END)
            self.entrada_busqueda.config(fg=COLORS['text_dark'])
            self._placeholder_activo = False

    def restaurar_placeholder(self, event):
        if not self.busqueda_var.get().strip():
            self.entrada_busqueda.insert(0, "Nombre, matrícula o carrera...")
            self.entrada_busqueda.config(fg=COLORS['text_gray'])
            self._placeholder_activo = True

    # ── Eventos de tabla ─────────────────────────────────────────────────────

    def on_select(self, event):
        seleccion = self.tabla.selection()
        if not seleccion:
            return
        user_id = self.tabla.item(seleccion[0])['values'][0]
        for u in self.datos:
            if u['id'] == user_id:
                self.usuario_seleccionado = u
                break
        self.btn_editar.config(state="normal")
        self.btn_ver_fotos.config(state="normal")
        self.btn_historial.config(state="normal")
        self.crear_panel_detalles()

    # ── Acciones ─────────────────────────────────────────────────────────────

    def editar_usuario(self):
        if self.usuario_seleccionado:
            messagebox.showinfo("Editar Usuario",
                f"Editar: {self.usuario_seleccionado['nombre']}\n(En desarrollo)")

    def ver_fotos(self):
        if self.usuario_seleccionado:
            messagebox.showinfo("Fotos del Usuario",
                f"📸 {self.usuario_seleccionado['nombre']} — {self.usuario_seleccionado['fotos']} fotos\n(En desarrollo)")

    def ver_historial(self):
        if self.usuario_seleccionado:
            messagebox.showinfo("Historial de Accesos",
                f"🔐 {self.usuario_seleccionado['nombre']} — {self.usuario_seleccionado['accesos']} accesos\n(En desarrollo)")