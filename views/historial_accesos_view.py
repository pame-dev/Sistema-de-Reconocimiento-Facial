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
        self.container.pack(fill="both", expand=True, padx=24, pady=20)

        self.datos = []
        self._placeholder_activo = True

        self.crear_interfaz()

    def crear_interfaz(self):
        self._configurar_estilo_tabla()

        # ── Cabecera ──────────────────────────────────────────────────────────
        header = ctk.CTkFrame(self.container, fg_color="transparent")
        header.pack(fill="x", pady=(0, 16))

        left = ctk.CTkFrame(header, fg_color="transparent")
        left.pack(side="left")

        ctk.CTkLabel(
            left,
            text="📊  Historial de Accesos",
            font=("Segoe UI", 24, "bold"),
            text_color=COLORS['text_dark']
        ).pack(anchor="w")

        ctk.CTkLabel(
            left,
            text="Registro de todos los intentos de acceso al sistema",
            font=("Segoe UI", 11),
            text_color=COLORS['text_gray']
        ).pack(anchor="w", pady=(2, 0))

        btn_row = ctk.CTkFrame(header, fg_color="transparent")
        btn_row.pack(side="right")

        ctk.CTkButton(
            btn_row,
            text="🗑️  Limpiar Todo",
            fg_color=COLORS['danger'],
            hover_color=COLORS['danger_dark'],
            text_color=COLORS['white'],
            font=("Segoe UI", 12, "bold"),
            corner_radius=10,
            height=38,
            command=self.limpiar_historial
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            btn_row,
            text="🔄  Actualizar",
            fg_color=COLORS['primary'],
            hover_color=COLORS['primary_dark'],
            text_color=COLORS['white'],
            font=("Segoe UI", 12, "bold"),
            corner_radius=10,
            height=38,
            command=self.cargar_datos
        ).pack(side="left")

        # ── Tarjetas de estadísticas ──────────────────────────────────────────
        stats_row = ctk.CTkFrame(self.container, fg_color="transparent")
        stats_row.pack(fill="x", pady=(0, 14))
        stats_row.grid_columnconfigure((0, 1, 2), weight=1, uniform="stat")

        self.lbl_total     = self._stat_card(stats_row, "Total de accesos",    "0", COLORS['primary'], "🔢", 0)
        self.lbl_aceptados = self._stat_card(stats_row, "Accesos aceptados",   "0", "#27AE60",          "✅", 1)
        self.lbl_denegados = self._stat_card(stats_row, "Accesos denegados",   "0", COLORS['danger'],   "❌", 2)

        # ── Barra de filtros ──────────────────────────────────────────────────
        filtros = ctk.CTkFrame(
            self.container,
            fg_color=COLORS['card_bg'],
            corner_radius=12,
            border_width=1,
            border_color=COLORS['border']
        )
        filtros.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            filtros,
            text="🔍  Buscar:",
            text_color=COLORS['text_dark'],
            font=("Segoe UI", 12, "bold")
        ).pack(side="left", padx=(14, 6), pady=10)

        self.busqueda_var     = tk.StringVar()
        self.entrada_busqueda = ctk.CTkEntry(
            filtros,
            textvariable=self.busqueda_var,
            font=("Segoe UI", 12),
            width=270, height=36,
            corner_radius=10,
            fg_color=COLORS['white'],
            border_color=COLORS['border'],
            text_color=COLORS['text_gray']
        )
        self.entrada_busqueda.pack(side="left", padx=(0, 16), pady=10)
        self.entrada_busqueda.insert(0, "Nombre de usuario...")
        self.entrada_busqueda.bind("<FocusIn>",   self.limpiar_placeholder)
        self.entrada_busqueda.bind("<FocusOut>",  self.restaurar_placeholder)
        self.entrada_busqueda.bind("<KeyRelease>", lambda e: self.filtrar_tabla())

        ctk.CTkLabel(
            filtros,
            text="Estado:",
            text_color=COLORS['text_dark'],
            font=("Segoe UI", 12, "bold")
        ).pack(side="left", padx=(0, 6), pady=10)

        # Combobox con fuente grande en dropdown
        win = self.container.winfo_toplevel()
        win.option_add("*TCombobox*Listbox.font", ("Segoe UI", 12))

        self.filtro_estado = ttk.Combobox(
            filtros,
            values=["Todos", "aceptado", "denegado"],
            state="readonly",
            width=14,
            font=("Segoe UI", 12)
        )
        self.filtro_estado.set("Todos")
        self.filtro_estado.pack(side="left", pady=10)
        self.filtro_estado.bind('<<ComboboxSelected>>', lambda e: self.filtrar_tabla())

        # ── Tabla ─────────────────────────────────────────────────────────────
        tabla_card = ctk.CTkFrame(
            self.container,
            fg_color=COLORS['card_bg'],
            corner_radius=12,
            border_width=1,
            border_color=COLORS['border']
        )
        tabla_card.pack(fill="both", expand=True)

        # Header de la tabla
        tabla_header = ctk.CTkFrame(tabla_card, fg_color="transparent")
        tabla_header.pack(fill="x", padx=16, pady=(12, 6))

        ctk.CTkLabel(
            tabla_header,
            text="Registros",
            font=("Segoe UI", 13, "bold"),
            text_color=COLORS['text_dark']
        ).pack(side="left")

        self.lbl_conteo = ctk.CTkLabel(
            tabla_header,
            text="0 registros",
            font=("Segoe UI", 11),
            text_color=COLORS['text_gray']
        )
        self.lbl_conteo.pack(side="right")

        # Scrollbars
        scroll_y = ctk.CTkScrollbar(tabla_card, orientation="vertical")
        scroll_y.pack(side="right", fill="y", padx=(0, 4))

        scroll_x = ctk.CTkScrollbar(tabla_card, orientation="horizontal")
        scroll_x.pack(side="bottom", fill="x", pady=(0, 4))

        self.tree = ttk.Treeview(
            tabla_card,
            columns=("id", "usuario", "fecha", "estado", "confianza", "umbral"),
            show="headings",
            yscrollcommand=scroll_y.set,
            xscrollcommand=scroll_x.set,
            height=15
        )
        scroll_y.configure(command=self.tree.yview)
        scroll_x.configure(command=self.tree.xview)

        cols = [
            ("id",        "ID",          55,  "center"),
            ("usuario",   "Usuario",     220, "w"),
            ("fecha",     "Fecha y Hora",165, "center"),
            ("estado",    "Estado",      120, "center"),
            ("confianza", "Confianza",   110, "center"),
            ("umbral",    "Umbral",      90,  "center"),
        ]
        for col, label, w, anchor in cols:
            self.tree.heading(col, text=label)
            self.tree.column(col, width=w, anchor=anchor)

        self.tree.pack(fill="both", expand=True, padx=4)

        # Tags de color por estado
        self.tree.tag_configure('aceptado', background='#EAF7EE', foreground='#1A7A40')
        self.tree.tag_configure('denegado', background='#FEF0F0', foreground='#C0392B')

    # ── Stat card ─────────────────────────────────────────────────────────────

    def _stat_card(self, parent, titulo, valor, color, icono, col):
        card = ctk.CTkFrame(
            parent,
            fg_color=COLORS['card_bg'],
            corner_radius=12,
            border_width=1,
            border_color=COLORS['border']
        )
        card.grid(row=0, column=col, padx=6, sticky="ew")

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(padx=16, pady=12, fill="x")

        top = ctk.CTkFrame(inner, fg_color="transparent")
        top.pack(fill="x")

        ctk.CTkLabel(
            top, text=titulo,
            font=("Segoe UI", 11, "bold"),
            text_color=color, anchor="w"
        ).pack(side="left")

        ctk.CTkLabel(
            top, text=icono,
            font=("Segoe UI Emoji", 16)
        ).pack(side="right")

        lbl = ctk.CTkLabel(
            inner, text=valor,
            font=("Segoe UI", 30, "bold"),
            text_color=COLORS['text_dark'],
            anchor="w"
        )
        lbl.pack(anchor="w", pady=(4, 0))
        return lbl

    # ── Estilo tabla ──────────────────────────────────────────────────────────

    def _configurar_estilo_tabla(self):
        style = ttk.Style()
        style.theme_use('default')
        style.configure(
            'Treeview',
            background=COLORS['white'],
            fieldbackground=COLORS['white'],
            foreground=COLORS['text_dark'],
            rowheight=32,
            borderwidth=0,
            font=("Segoe UI", 11)
        )
        style.configure(
            'Treeview.Heading',
            background=COLORS['content_bg'],
            foreground=COLORS['text_dark'],
            font=("Segoe UI", 11, "bold"),
            relief='flat',
            padding=6
        )
        style.map('Treeview', background=[('selected', COLORS['primary'])])
        style.map('Treeview.Heading', background=[('active', COLORS['content_bg'])])

    # ── Placeholder ───────────────────────────────────────────────────────────

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

    # ── Datos ─────────────────────────────────────────────────────────────────

    def cargar_datos(self):
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

            total     = len(self.datos)
            aceptados = sum(1 for d in self.datos if d[3] == 'aceptado')
            denegados = sum(1 for d in self.datos if d[3] == 'denegado')

            self.lbl_total.configure(text=str(total))
            self.lbl_aceptados.configure(text=str(aceptados))
            self.lbl_denegados.configure(text=str(denegados))

            self.filtrar_tabla()

        except Exception as e:
            messagebox.showerror("Error", f"Error al cargar datos: {str(e)}")

    def filtrar_tabla(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        busqueda     = "" if self._placeholder_activo else self.busqueda_var.get().lower().strip()
        estado_filtro = self.filtro_estado.get()

        conteo = 0
        for dato in self.datos:
            id_acceso, nombre, fecha, estado, confianza, umbral = dato

            if estado_filtro != "Todos" and estado != estado_filtro:
                continue
            if busqueda and busqueda not in nombre.lower():
                continue

            try:
                fecha_fmt = datetime.strptime(fecha, "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y  %H:%M:%S")
            except Exception:
                fecha_fmt = fecha or "—"

            estado_fmt = "✅  Aceptado" if estado == "aceptado" else "❌  Denegado"

            self.tree.insert("", "end", values=(
                id_acceso,
                nombre,
                fecha_fmt,
                estado_fmt,
                f"{confianza:.2f}" if confianza else "—",
                f"{umbral:.0f}"    if umbral    else "N/A"
            ), tags=(estado,))
            conteo += 1

        self.lbl_conteo.configure(text=f"{conteo} registro{'s' if conteo != 1 else ''}")

    def limpiar_historial(self):
        respuesta = messagebox.askyesno(
            "Confirmar eliminación",
            "¿Estás segura de que quieres eliminar TODO el historial?\n\nEsta acción no se puede deshacer.",
            icon='warning'
        )
        if not respuesta:
            return

        try:
            conn = get_db()
            if not conn:
                messagebox.showerror("Error", "No se pudo conectar a la base de datos")
                return
            conn.cursor().execute("DELETE FROM accesos")
            conn.commit()
            conn.close()
            messagebox.showinfo("✅ Listo", "Historial eliminado correctamente.")
            self.cargar_datos()
        except Exception as e:
            messagebox.showerror("Error", f"Error al limpiar historial: {str(e)}")
