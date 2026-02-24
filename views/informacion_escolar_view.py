# views/informacion_escolar_view.py
import tkinter as tk
from tkinter import ttk, messagebox
import sys
import os

# Añadir la carpeta raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import COLORS, get_db

class InformacionEscolarView:
    """Vista para consultar y gestionar información escolar"""
    
    def __init__(self, parent):
        self.parent = parent
        self.container = tk.Frame(parent, bg=COLORS['white'])
        self.container.pack(fill="both", expand=True, padx=30, pady=30)
        
        self.usuario_seleccionado = None
        self.datos = []  # ← Inicializar datos vacío
        
        self.crear_interfaz()
        self.cargar_datos()  # ← Cargar datos después de crear interfaz
    
    def crear_interfaz(self):
        """Crea todos los elementos de la interfaz"""
        
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
        
        # Botón de actualizar
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
        
        # === FILTROS DE BÚSQUEDA ===
        filtros_frame = tk.Frame(self.container, bg=COLORS['white'])
        filtros_frame.pack(fill="x", pady=(0, 15))
        
        # Buscador
        tk.Label(
            filtros_frame,
            text="Buscar:",
            bg=COLORS['white'],
            fg=COLORS['text_dark'],
            font=("Arial", 11)
        ).pack(side="left", padx=(0, 5))
        
        self.busqueda_var = tk.StringVar()
        
        entrada_busqueda = tk.Entry(
            filtros_frame,
            textvariable=self.busqueda_var,
            font=("Arial", 11),
            width=30,
            relief="solid",
            borderwidth=1
        )
        entrada_busqueda.pack(side="left", padx=(0, 15))
        entrada_busqueda.insert(0, "Nombre, matrícula o carrera...")
        entrada_busqueda.bind("<FocusIn>", self.limpiar_placeholder)
        entrada_busqueda.bind("<FocusOut>", self.restaurar_placeholder)
        
        # Vincular tecla de búsqueda
        self.busqueda_var.trace('w', lambda *args: self.filtrar_tabla() if hasattr(self, 'datos') else None)
        
        # Filtro por rol
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
        
        # === TABLA DE INFORMACIÓN ===
        # Frame para la tabla con scroll
        tabla_frame = tk.Frame(self.container, bg=COLORS['white'])
        tabla_frame.pack(fill="both", expand=True, pady=(0, 15))
        
        # Scrollbars
        scroll_y = tk.Scrollbar(tabla_frame)
        scroll_y.pack(side="right", fill="y")
        
        scroll_x = tk.Scrollbar(tabla_frame, orient="horizontal")
        scroll_x.pack(side="bottom", fill="x")
        
        # Treeview (tabla)
        self.tabla = ttk.Treeview(
            tabla_frame,
            columns=("id", "nombre", "matricula", "rol", "carrera", "grado", "grupo", "fotos"),
            show="headings",
            yscrollcommand=scroll_y.set,
            xscrollcommand=scroll_x.set,
            height=15
        )
        
        # Configurar scrollbars
        scroll_y.config(command=self.tabla.yview)
        scroll_x.config(command=self.tabla.xview)
        
        # Definir headings
        self.tabla.heading("id", text="ID")
        self.tabla.heading("nombre", text="Nombre Completo")
        self.tabla.heading("matricula", text="Matrícula")
        self.tabla.heading("rol", text="Rol")
        self.tabla.heading("carrera", text="Carrera/Materia")
        self.tabla.heading("grado", text="Grado")
        self.tabla.heading("grupo", text="Grupo")
        self.tabla.heading("fotos", text="Fotos")
        
        # Definir anchos de columna
        self.tabla.column("id", width=50, anchor="center")
        self.tabla.column("nombre", width=250)
        self.tabla.column("matricula", width=120, anchor="center")
        self.tabla.column("rol", width=100, anchor="center")
        self.tabla.column("carrera", width=200)
        self.tabla.column("grado", width=80, anchor="center")
        self.tabla.column("grupo", width=80, anchor="center")
        self.tabla.column("fotos", width=80, anchor="center")
        
        self.tabla.pack(fill="both", expand=True)
        
        # Bind selección
        self.tabla.bind('<<TreeviewSelect>>', self.on_select)
        
        # === PANEL DE DETALLES ===
        self.detalles_frame = tk.Frame(self.container, bg=COLORS['content_bg'], relief="solid", borderwidth=1)
        self.detalles_frame.pack(fill="x", pady=(0, 15))
        
        self.crear_panel_detalles()
        
        # === BOTONES DE ACCIÓN ===
        acciones_frame = tk.Frame(self.container, bg=COLORS['white'])
        acciones_frame.pack(fill="x")
        
        self.btn_editar = tk.Button(
            acciones_frame,
            text="✏️ Editar Información",
            bg=COLORS['header'],
            fg=COLORS['white'],
            font=("Arial", 11),
            relief="flat",
            padx=20,
            pady=8,
            state="disabled",
            command=self.editar_usuario
        )
        self.btn_editar.pack(side="left", padx=5)
        
        self.btn_ver_fotos = tk.Button(
            acciones_frame,
            text="📸 Ver Fotos",
            bg=COLORS['primary'],
            fg=COLORS['white'],
            font=("Arial", 11),
            relief="flat",
            padx=20,
            pady=8,
            state="disabled",
            command=self.ver_fotos
        )
        self.btn_ver_fotos.pack(side="left", padx=5)
        
        self.btn_historial = tk.Button(
            acciones_frame,
            text="📊 Historial de Accesos",
            bg=COLORS['info'],
            fg=COLORS['white'],
            font=("Arial", 11),
            relief="flat",
            padx=20,
            pady=8,
            state="disabled",
            command=self.ver_historial
        )
        self.btn_historial.pack(side="left", padx=5)
    
    def crear_panel_detalles(self):
        """Crea el panel de detalles del usuario seleccionado"""
        # Limpiar panel
        for widget in self.detalles_frame.winfo_children():
            widget.destroy()
        
        # Título
        tk.Label(
            self.detalles_frame,
            text="📋 Detalles del Usuario",
            font=("Arial", 12, "bold"),
            bg=COLORS['content_bg'],
            fg=COLORS['text_dark']
        ).pack(anchor="w", padx=15, pady=(10, 5))
        
        # Frame para la info en grid
        info_frame = tk.Frame(self.detalles_frame, bg=COLORS['content_bg'])
        info_frame.pack(fill="x", padx=15, pady=5)
        
        if self.usuario_seleccionado:
            # Mostrar información del usuario seleccionado
            self.mostrar_detalles_usuario(info_frame)
        else:
            # Mensaje por defecto
            tk.Label(
                info_frame,
                text="Selecciona un usuario para ver sus detalles",
                bg=COLORS['content_bg'],
                fg=COLORS['text_gray'],
                font=("Arial", 11, "italic")
            ).pack(pady=15)
    
    def mostrar_detalles_usuario(self, parent):
        """Muestra los detalles del usuario seleccionado"""
        if not self.usuario_seleccionado:
            return
        
        # Datos personales
        self.crear_fila_detalle(parent, "Nombre:", self.usuario_seleccionado.get('nombre', ''), 0)
        self.crear_fila_detalle(parent, "Matrícula:", self.usuario_seleccionado.get('matricula', ''), 1)
        self.crear_fila_detalle(parent, "Rol:", self.usuario_seleccionado.get('rol', ''), 2)
        self.crear_fila_detalle(parent, "Teléfono:", self.usuario_seleccionado.get('telefono', 'No registrado'), 3)
        
        # Datos académicos (si aplica)
        if self.usuario_seleccionado.get('rol') == 'alumno':
            self.crear_fila_detalle(parent, "Carrera:", self.usuario_seleccionado.get('carrera', 'No especificada'), 4)
            self.crear_fila_detalle(parent, "Grado/Grupo:", f"{self.usuario_seleccionado.get('grado', '')}° {self.usuario_seleccionado.get('grupo', '')}", 5)
            self.crear_fila_detalle(parent, "Facultad:", self.usuario_seleccionado.get('facultad', 'No especificada'), 6)
        
        # Estadísticas
        stats_frame = tk.Frame(parent, bg=COLORS['content_bg'])
        stats_frame.grid(row=7, column=0, columnspan=2, pady=(10, 0), sticky="w")
        
        tk.Label(
            stats_frame,
            text=f"📸 Fotos registradas: {self.usuario_seleccionado.get('fotos', 0)}",
            bg=COLORS['content_bg'],
            fg=COLORS['primary'],
            font=("Arial", 10, "bold")
        ).pack(side="left", padx=(0, 20))
        
        tk.Label(
            stats_frame,
            text=f"🔐 Accesos totales: {self.usuario_seleccionado.get('accesos', 0)}",
            bg=COLORS['content_bg'],
            fg=COLORS['header'],
            font=("Arial", 10, "bold")
        ).pack(side="left")
    
    def crear_fila_detalle(self, parent, label, valor, fila):
        """Crea una fila de detalle en el grid"""
        tk.Label(
            parent,
            text=label,
            bg=COLORS['content_bg'],
            fg=COLORS['text_gray'],
            font=("Arial", 10),
            width=15,
            anchor="w"
        ).grid(row=fila, column=0, sticky="w", pady=2)
        
        tk.Label(
            parent,
            text=valor,
            bg=COLORS['content_bg'],
            fg=COLORS['text_dark'],
            font=("Arial", 10, "bold"),
            anchor="w"
        ).grid(row=fila, column=1, sticky="w", pady=2, padx=(10, 0))
    
    def cargar_datos(self):
        """Carga los datos desde la base de datos"""
        try:
            conn = get_db()
            if not conn:
                messagebox.showerror("Error", "No se pudo conectar a la base de datos")
                return
                
            cursor = conn.cursor()
            
            # Consulta para obtener información escolar completa
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
                    COUNT(DISTINCT b.idBiometria) as total_fotos,
                    COUNT(DISTINCT ac.idAcceso) as total_accesos
                FROM usuarios u
                LEFT JOIN alumnos a ON u.idUsuario = a.fkIdUsuario
                LEFT JOIN maestros m ON u.idUsuario = m.fkIdUsuario
                LEFT JOIN personal_escolar p ON u.idUsuario = p.fkIdUsuario
                LEFT JOIN biometria b ON u.idUsuario = b.fkIdUsuario
                LEFT JOIN accesos ac ON u.idUsuario = ac.fkIdUsuario
                GROUP BY u.idUsuario
                ORDER BY u.idUsuario
            """)
            
            resultados = cursor.fetchall()
            conn.close()
            
            self.datos = []  # Reiniciar datos
            
            for row in resultados:
                # Determinar carrera/materia según rol
                if row[5] == 'alumno':  # rol = alumno
                    carrera = row[7] or 'No especificada'
                    grado = row[8] or '-'
                    grupo = row[9] or '-'
                    especialidad = row[10] or '-'
                elif row[5] == 'maestro':
                    carrera = row[11] or 'No especificada'
                    grado = row[12] or '-'
                    grupo = '-'
                else:
                    carrera = row[13] or '-'
                    grado = '-'
                    grupo = '-'
                
                nombre_completo = f"{row[1]} {row[2] or ''} {row[3] or ''}".strip()
                
                usuario_info = {
                    'id': row[0],
                    'nombre': nombre_completo,
                    'matricula': row[4] or 'N/A',
                    'rol': row[5],
                    'telefono': row[6] or 'N/A',
                    'carrera': carrera,
                    'grado': grado,
                    'grupo': grupo,
                    'facultad': row[10] if row[5] == 'alumno' else 'N/A',
                    'fotos': row[15] or 0,
                    'accesos': row[16] or 0
                }
                self.datos.append(usuario_info)
            
            self.actualizar_tabla()
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al cargar datos: {e}")
            self.datos = []
    
    def actualizar_tabla(self, datos_filtrados=None):
        """Actualiza la tabla con los datos (filtrados o no)"""
        # Limpiar tabla
        for item in self.tabla.get_children():
            self.tabla.delete(item)
        
        datos_mostrar = datos_filtrados if datos_filtrados is not None else self.datos
        
        for usuario in datos_mostrar:
            self.tabla.insert("", "end", values=(
                usuario['id'],
                usuario['nombre'],
                usuario['matricula'],
                usuario['rol'],
                usuario['carrera'],
                usuario['grado'],
                usuario['grupo'],
                usuario['fotos']
            ))
    
    def filtrar_tabla(self):
        """Filtra la tabla según búsqueda y rol"""
        if not hasattr(self, 'datos') or not self.datos:
            return  # No hay datos para filtrar
            
        texto_busqueda = self.busqueda_var.get().lower()
        rol_filtro = self.filtro_rol.get()
        
        if texto_busqueda == "nombre, matrícula o carrera...":
            texto_busqueda = ""
        
        datos_filtrados = []
        for usuario in self.datos:
            # Filtro por rol
            if rol_filtro != "Todos" and usuario['rol'] != rol_filtro:
                continue
            
            # Filtro por búsqueda
            if texto_busqueda:
                if (texto_busqueda in usuario['nombre'].lower() or
                    texto_busqueda in usuario['matricula'].lower() or
                    texto_busqueda in usuario['carrera'].lower()):
                    datos_filtrados.append(usuario)
            else:
                datos_filtrados.append(usuario)
        
        self.actualizar_tabla(datos_filtrados)
    
    def on_select(self, event):
        """Evento al seleccionar un usuario en la tabla"""
        seleccion = self.tabla.selection()
        if seleccion:
            item = self.tabla.item(seleccion[0])
            user_id = item['values'][0]
            
            # Buscar usuario en datos
            for usuario in self.datos:
                if usuario['id'] == user_id:
                    self.usuario_seleccionado = usuario
                    break
            
            # Habilitar botones
            self.btn_editar.config(state="normal")
            self.btn_ver_fotos.config(state="normal")
            self.btn_historial.config(state="normal")
            
            # Actualizar panel de detalles
            self.crear_panel_detalles()
    
    def limpiar_placeholder(self, event):
        """Limpia el placeholder del campo de búsqueda"""
        if self.busqueda_var.get() == "Nombre, matrícula o carrera...":
            self.busqueda_var.set("")
    
    def restaurar_placeholder(self, event):
        """Restaura el placeholder si el campo está vacío"""
        if not self.busqueda_var.get():
            self.busqueda_var.set("Nombre, matrícula o carrera...")
    
    def editar_usuario(self):
        """Editar información del usuario seleccionado"""
        if self.usuario_seleccionado:
            messagebox.showinfo(
                "Editar Usuario",
                f"Editar información de: {self.usuario_seleccionado['nombre']}\n(En desarrollo)"
            )
    
    def ver_fotos(self):
        """Ver fotos del usuario seleccionado"""
        if self.usuario_seleccionado:
            messagebox.showinfo(
                "Fotos del Usuario",
                f"📸 {self.usuario_seleccionado['nombre']} tiene {self.usuario_seleccionado['fotos']} fotos registradas\n(En desarrollo)"
            )
    
    def ver_historial(self):
        """Ver historial de accesos del usuario"""
        if self.usuario_seleccionado:
            messagebox.showinfo(
                "Historial de Accesos",
                f"🔐 {self.usuario_seleccionado['nombre']} tiene {self.usuario_seleccionado['accesos']} accesos registrados\n(En desarrollo)"
            )