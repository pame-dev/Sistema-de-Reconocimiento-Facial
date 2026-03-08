# views/historial_accesos_view.py
import tkinter as tk
from tkinter import ttk, messagebox
import sys
import os
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import COLORS, get_db


class HistorialAccesosView:
    """Vista para mostrar el historial de accesos del sistema"""

    def __init__(self, parent):
        self.parent = parent
        self.container = tk.Frame(parent, bg=COLORS['white'])
        self.container.pack(fill="both", expand=True, padx=30, pady=30)

        self.datos = []
        self._placeholder_activo = True

        self.crear_interfaz()

    def crear_interfaz(self):
        # === CABECERA ===
        header_frame = tk.Frame(self.container, bg=COLORS['white'])
        header_frame.pack(fill="x", pady=(0, 20))

        tk.Label(
            header_frame,
            text="📊 Historial de Accesos",
            font=("Arial", 20, "bold"),
            bg=COLORS['white'],
            fg=COLORS['text_dark']
        ).pack(side="left")

        tk.Button(
            header_frame,
            text="🔄 Actualizar",
            bg=COLORS['primary'],
            fg=COLORS['white'],
            font=("Arial", 10),
            relief="flat",
            padx=15,
            pady=5,
            command=self.cargar_datos
        ).pack(side="right", padx=(5, 0))

        # Botón para limpiar historial
        tk.Button(
            header_frame,
            text="🗑️ Limpiar Todo",
            bg=COLORS['danger'],
            fg=COLORS['white'],
            font=("Arial", 10),
            relief="flat",
            padx=15,
            pady=5,
            command=self.limpiar_historial
        ).pack(side="right")

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
        self.entrada_busqueda.insert(0, "Nombre de usuario...")
        self.entrada_busqueda.bind("<FocusIn>", self.limpiar_placeholder)
        self.entrada_busqueda.bind("<FocusOut>", self.restaurar_placeholder)
        self.entrada_busqueda.bind("<KeyRelease>", lambda e: self.filtrar_tabla())

        tk.Label(
            filtros_frame,
            text="Estado:",
            bg=COLORS['white'],
            fg=COLORS['text_dark'],
            font=("Arial", 11)
        ).pack(side="left", padx=(0, 5))

        self.filtro_estado = ttk.Combobox(
            filtros_frame,
            values=["Todos", "aceptado", "denegado"],
            state="readonly",
            width=15,
            font=("Arial", 11)
        )
        self.filtro_estado.set("Todos")
        self.filtro_estado.pack(side="left")
        self.filtro_estado.bind('<<ComboboxSelected>>', lambda e: self.filtrar_tabla())

        # === ESTADÍSTICAS ===
        stats_frame = tk.Frame(self.container, bg=COLORS['content_bg'], relief="solid", borderwidth=1)
        stats_frame.pack(fill="x", pady=(0, 15))

        inner_stats = tk.Frame(stats_frame, bg=COLORS['content_bg'])
        inner_stats.pack(fill="x", padx=15, pady=10)

        # Total de accesos
        self.lbl_total = tk.Label(
            inner_stats,
            text="Total: 0",
            font=("Arial", 11, "bold"),
            bg=COLORS['content_bg'],
            fg=COLORS['text_dark']
        )
        self.lbl_total.pack(side="left", padx=10)

        # Accesos aceptados
        self.lbl_aceptados = tk.Label(
            inner_stats,
            text="✅ Aceptados: 0",
            font=("Arial", 11),
            bg=COLORS['content_bg'],
            fg=COLORS['primary']
        )
        self.lbl_aceptados.pack(side="left", padx=10)

        # Accesos denegados
        self.lbl_denegados = tk.Label(
            inner_stats,
            text="❌ Denegados: 0",
            font=("Arial", 11),
            bg=COLORS['content_bg'],
            fg=COLORS['danger']
        )
        self.lbl_denegados.pack(side="left", padx=10)

        # === TABLA ===
        tabla_frame = tk.Frame(self.container, bg=COLORS['white'])
        tabla_frame.pack(fill="both", expand=True)

        # Scrollbars
        scroll_y = tk.Scrollbar(tabla_frame, orient="vertical")
        scroll_y.pack(side="right", fill="y")

        scroll_x = tk.Scrollbar(tabla_frame, orient="horizontal")
        scroll_x.pack(side="bottom", fill="x")

        # Treeview
        self.tree = ttk.Treeview(
            tabla_frame,
            columns=("id", "usuario", "fecha", "estado", "confianza", "umbral"),
            show="headings",
            yscrollcommand=scroll_y.set,
            xscrollcommand=scroll_x.set,
            height=15
        )

        scroll_y.config(command=self.tree.yview)
        scroll_x.config(command=self.tree.xview)

        # Configurar columnas
        self.tree.heading("id", text="ID")
        self.tree.heading("usuario", text="Usuario")
        self.tree.heading("fecha", text="Fecha y Hora")
        self.tree.heading("estado", text="Estado")
        self.tree.heading("confianza", text="Confianza")
        self.tree.heading("umbral", text="Umbral")

        self.tree.column("id", width=50, anchor="center")
        self.tree.column("usuario", width=200, anchor="w")
        self.tree.column("fecha", width=150, anchor="center")
        self.tree.column("estado", width=100, anchor="center")
        self.tree.column("confianza", width=100, anchor="center")
        self.tree.column("umbral", width=100, anchor="center")

        self.tree.pack(fill="both", expand=True)

        # Estilos para filas
        self.tree.tag_configure('aceptado', background='#d4edda')
        self.tree.tag_configure('denegado', background='#f8d7da')

    def limpiar_placeholder(self, event):
        if self._placeholder_activo:
            self.entrada_busqueda.delete(0, tk.END)
            self.entrada_busqueda.config(fg=COLORS['text_dark'])
            self._placeholder_activo = False

    def restaurar_placeholder(self, event):
        if not self.entrada_busqueda.get():
            self.entrada_busqueda.insert(0, "Nombre de usuario...")
            self.entrada_busqueda.config(fg=COLORS['text_gray'])
            self._placeholder_activo = True

    def cargar_datos(self):
        """Carga los datos de accesos desde la base de datos"""
        try:
            conn = get_db()
            if not conn:
                messagebox.showerror("Error", "No se pudo conectar a la base de datos")
                return

            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    a.idAcceso,
                    COALESCE(u.nombreUsuario || ' ' || u.apellidoPaternoUsuario, 'Desconocido') as nombreCompleto,
                    a.fechaHoraIntentoAcceso,
                    a.estado_acceso,
                    a.confianzaAcceso,
                    a.umbralConfianzaUsado
                FROM accesos a
                LEFT JOIN usuarios u ON a.fkIdUsuario = u.idUsuario
                ORDER BY a.fechaHoraIntentoAcceso DESC
            """)

            self.datos = cursor.fetchall()
            conn.close()

            # Actualizar estadísticas
            total = len(self.datos)
            aceptados = sum(1 for d in self.datos if d[3] == 'aceptado')
            denegados = sum(1 for d in self.datos if d[3] == 'denegado')

            self.lbl_total.config(text=f"Total: {total}")
            self.lbl_aceptados.config(text=f"✅ Aceptados: {aceptados}")
            self.lbl_denegados.config(text=f"❌ Denegados: {denegados}")

            self.filtrar_tabla()

        except Exception as e:
            messagebox.showerror("Error", f"Error al cargar datos: {str(e)}")

    def filtrar_tabla(self):
        """Filtra y muestra los datos en la tabla"""
        # Limpiar tabla
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Obtener filtros
        busqueda = self.busqueda_var.get().lower()
        if self._placeholder_activo:
            busqueda = ""

        estado_filtro = self.filtro_estado.get()

        # Filtrar datos
        for dato in self.datos:
            id_acceso, nombre, fecha, estado, confianza, umbral = dato

            # Aplicar filtros
            if estado_filtro != "Todos" and estado != estado_filtro:
                continue

            if busqueda and busqueda not in nombre.lower():
                continue

            # Formatear fecha
            try:
                fecha_obj = datetime.strptime(fecha, "%Y-%m-%d %H:%M:%S")
                fecha_formatted = fecha_obj.strftime("%d/%m/%Y %H:%M:%S")
            except:
                fecha_formatted = fecha

            # Formatear estado
            estado_formatted = "✅ Aceptado" if estado == "aceptado" else "❌ Denegado"

            # Insertar en tabla
            tag = estado
            self.tree.insert(
                "",
                "end",
                values=(
                    id_acceso,
                    nombre,
                    fecha_formatted,
                    estado_formatted,
                    f"{confianza:.2f}",
                    f"{umbral:.0f}" if umbral else "N/A"
                ),
                tags=(tag,)
            )

    def limpiar_historial(self):
        """Limpia todo el historial de accesos"""
        respuesta = messagebox.askyesno(
            "Confirmar",
            "¿Estás segura de que quieres eliminar TODO el historial de accesos?\n\nEsta acción no se puede deshacer.",
            icon='warning'
        )

        if not respuesta:
            return

        try:
            conn = get_db()
            if not conn:
                messagebox.showerror("Error", "No se pudo conectar a la base de datos")
                return

            cursor = conn.cursor()
            cursor.execute("DELETE FROM accesos")
            conn.commit()
            conn.close()

            messagebox.showinfo("Éxito", "Historial limpiado correctamente")
            self.cargar_datos()

        except Exception as e:
            messagebox.showerror("Error", f"Error al limpiar historial: {str(e)}")
