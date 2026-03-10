# views/historial_accesos_view.py
import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk
import sys
import os
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import COLORS, get_db


class HistorialAccesosView:
    """Vista para mostrar el historial de accesos del sistema"""

    def __init__(self, parent):
        self.parent = parent
        self.container = ctk.CTkFrame(parent, fg_color=COLORS['background'])
        self.container.pack(fill="both", expand=True, padx=30, pady=30)

        self.datos = []
        self._placeholder_activo = True

        self.crear_interfaz()

    def crear_interfaz(self):
        self._configurar_estilo_tabla()

        # === CABECERA ===
        header_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 20))

        ctk.CTkLabel(
            header_frame,
            text="📊 Historial de Accesos",
            font=("Segoe UI", 26, "bold"),
            text_color=COLORS['text_dark']
        ).pack(side="left")

        ctk.CTkButton(
            header_frame,
            text="🔄 Actualizar",
            fg_color=COLORS['primary'],
            hover_color=COLORS['primary_dark'],
            text_color=COLORS['white'],
            font=("Segoe UI", 12, "bold"),
            corner_radius=10,
            height=38,
            command=self.cargar_datos
        ).pack(side="right", padx=(5, 0))

        # Botón para limpiar historial
        ctk.CTkButton(
            header_frame,
            text="🗑️ Limpiar Todo",
            fg_color=COLORS['danger'],
            hover_color=COLORS['danger_dark'],
            text_color=COLORS['white'],
            font=("Segoe UI", 12, "bold"),
            corner_radius=10,
            height=38,
            command=self.limpiar_historial
        ).pack(side="right")

        # === FILTROS ===
        filtros_frame = ctk.CTkFrame(
            self.container,
            fg_color=COLORS['card_bg'],
            corner_radius=14,
            border_width=1,
            border_color=COLORS['border']
        )
        filtros_frame.pack(fill="x", pady=(0, 15))
        filtros_frame.grid_columnconfigure((0, 1, 2, 3), weight=0)

        ctk.CTkLabel(
            filtros_frame,
            text="Buscar:",
            text_color=COLORS['text_dark'],
            font=("Segoe UI", 12, "bold")
        ).pack(side="left", padx=(14, 5), pady=12)

        self.busqueda_var = tk.StringVar()
        self.entrada_busqueda = ctk.CTkEntry(
            filtros_frame,
            textvariable=self.busqueda_var,
            font=("Segoe UI", 12),
            width=260,
            height=36,
            corner_radius=10,
            fg_color=COLORS['white'],
            border_color=COLORS['border'],
            text_color=COLORS['text_gray']
        )
        self.entrada_busqueda.pack(side="left", padx=(0, 15), pady=10)
        self.entrada_busqueda.insert(0, "Nombre de usuario...")
        self.entrada_busqueda.bind("<FocusIn>", self.limpiar_placeholder)
        self.entrada_busqueda.bind("<FocusOut>", self.restaurar_placeholder)
        self.entrada_busqueda.bind("<KeyRelease>", lambda e: self.filtrar_tabla())

        ctk.CTkLabel(
            filtros_frame,
            text="Estado:",
            text_color=COLORS['text_dark'],
            font=("Segoe UI", 12, "bold")
        ).pack(side="left", padx=(0, 5), pady=12)

        self.filtro_estado = ttk.Combobox(
            filtros_frame,
            values=["Todos", "aceptado", "denegado"],
            state="readonly",
            width=15,
            font=("Segoe UI", 11)
        )
        self.filtro_estado.set("Todos")
        self.filtro_estado.pack(side="left", pady=10)
        self.filtro_estado.bind('<<ComboboxSelected>>', lambda e: self.filtrar_tabla())

        # === ESTADÍSTICAS ===
        stats_frame = ctk.CTkFrame(
            self.container,
            fg_color=COLORS['card_bg'],
            corner_radius=14,
            border_width=1,
            border_color=COLORS['border']
        )
        stats_frame.pack(fill="x", pady=(0, 15))

        inner_stats = ctk.CTkFrame(stats_frame, fg_color="transparent")
        inner_stats.pack(fill="x", padx=15, pady=10)

        # Total de accesos
        self.lbl_total = ctk.CTkLabel(
            inner_stats,
            text="Total: 0",
            font=("Segoe UI", 12, "bold"),
            text_color=COLORS['text_dark']
        )
        self.lbl_total.pack(side="left", padx=10)

        # Accesos aceptados
        self.lbl_aceptados = ctk.CTkLabel(
            inner_stats,
            text="✅ Aceptados: 0",
            font=("Segoe UI", 12),
            text_color=COLORS['primary']
        )
        self.lbl_aceptados.pack(side="left", padx=10)

        # Accesos denegados
        self.lbl_denegados = ctk.CTkLabel(
            inner_stats,
            text="❌ Denegados: 0",
            font=("Segoe UI", 12),
            text_color=COLORS['danger']
        )
        self.lbl_denegados.pack(side="left", padx=10)

        # === TABLA ===
        tabla_frame = ctk.CTkFrame(
            self.container,
            fg_color=COLORS['card_bg'],
            corner_radius=14,
            border_width=1,
            border_color=COLORS['border']
        )
        tabla_frame.pack(fill="both", expand=True)

        # Scrollbars
        scroll_y = ctk.CTkScrollbar(tabla_frame, orientation="vertical")
        scroll_y.pack(side="right", fill="y")

        scroll_x = ctk.CTkScrollbar(tabla_frame, orientation="horizontal")
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

        scroll_y.configure(command=self.tree.yview)
        scroll_x.configure(command=self.tree.xview)

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

    def _configurar_estilo_tabla(self):
        style = ttk.Style()
        style.theme_use('default')
        style.configure(
            'Treeview',
            background=COLORS['white'],
            fieldbackground=COLORS['white'],
            foreground=COLORS['text_dark'],
            rowheight=30,
            borderwidth=0,
            font=("Segoe UI", 10)
        )
        style.configure(
            'Treeview.Heading',
            background=COLORS['content_bg'],
            foreground=COLORS['text_dark'],
            font=("Segoe UI", 10, "bold"),
            relief='flat'
        )
        style.map('Treeview.Heading', background=[('active', COLORS['content_bg'])])

    def limpiar_placeholder(self, event):
        if self._placeholder_activo:
            self.entrada_busqueda.delete(0, tk.END)
            self.entrada_busqueda.configure(text_color=COLORS['text_dark'])
            self._placeholder_activo = False

    def restaurar_placeholder(self, event):
        if not self.entrada_busqueda.get():
            self.entrada_busqueda.insert(0, "Nombre de usuario...")
            self.entrada_busqueda.configure(text_color=COLORS['text_gray'])
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

            self.lbl_total.configure(text=f"Total: {total}")
            self.lbl_aceptados.configure(text=f"✅ Aceptados: {aceptados}")
            self.lbl_denegados.configure(text=f"❌ Denegados: {denegados}")

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
