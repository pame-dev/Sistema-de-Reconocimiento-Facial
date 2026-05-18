# views/historial_accesos_view.py
import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk
import sys
import os
from datetime import datetime
from views.font_scale import FontScale
from PIL import Image, ImageTk
import io

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import COLORS, get_colors, toggle_theme, get_db
from idiomas import t
from tools.access_counter import AccessCounter


class HistorialAccesosView:
    """Vista para mostrar el historial de accesos del sistema."""

    def __init__(self, parent):
        self.colors = get_colors()
        self.parent = parent
        self.container = ctk.CTkFrame(parent, fg_color=self.colors['background'])
        self.container.view = self
        self.container.pack(fill="both", expand=True, padx=24, pady=20)

        self.datos = []
        self._placeholder_activo  = True
        self._acceso_seleccionado = None   # id del acceso actualmente en el panel
        self._foto_ref            = None   # referencia a ImageTk para evitar GC

        self.crear_interfaz()

    def destroy(self):
        try:
            self.entrada_busqueda.unbind("<FocusIn>")
            self.entrada_busqueda.unbind("<FocusOut>")
            self.entrada_busqueda.unbind("<KeyRelease>")
        except Exception:
            pass
        try:
            self.filtro_estado.unbind('<<ComboboxSelected>>')
        except Exception:
            pass
        try:
            self.tree.unbind('<<TreeviewSelect>>')
        except Exception:
            pass

    def _is_alive(self):
        return getattr(self, 'container', None) is not None and self.container.winfo_exists()

    # ── Estilos ttk ──────────────────────────────────────────────────────────
    def _aplicar_estilo_tabla(self):
        c = self.colors
        style = ttk.Style()
        style.theme_use('default')

        style.configure(
            'Dark.Treeview',
            background=c['tree_bg'],
            fieldbackground=c['tree_bg'],
            foreground=c['tree_fg'],
            rowheight=32,
            borderwidth=0,
            font=FontScale.f(11),
        )
        style.configure(
            'Dark.Treeview.Heading',
            background=c['tree_head_bg'],
            foreground=c['tree_head_fg'],
            font=FontScale.fb(11),
            relief='flat',
            padding=6,
        )
        style.map('Dark.Treeview',
                  background=[('selected', c['tree_sel_bg'])],
                  foreground=[('selected', c['tree_sel_fg'])])
        style.map('Dark.Treeview.Heading',
                  background=[('active', c['tree_head_bg'])])

        style.configure('Dark.Vertical.TScrollbar',
                        background=c['card_bg'], troughcolor=c['background'],
                        arrowcolor=c['text_gray'], borderwidth=0)
        style.configure('Dark.Horizontal.TScrollbar',
                        background=c['card_bg'], troughcolor=c['background'],
                        arrowcolor=c['text_gray'], borderwidth=0)

        style.configure('Dark.TCombobox',
                        fieldbackground=c['card_bg'], background=c['card_bg'],
                        foreground=c['text_dark'], arrowcolor=c['text_gray'],
                        bordercolor=c['border'], lightcolor=c['border'],
                        darkcolor=c['border'],
                        selectbackground=c['tree_sel_bg'],
                        selectforeground=c['tree_sel_fg'])
        style.map('Dark.TCombobox',
                  fieldbackground=[('readonly', c['card_bg'])],
                  foreground=[('readonly', c['text_dark'])],
                  background=[('readonly', c['card_bg'])])

        win = self.parent.winfo_toplevel()
        win.option_add("*TCombobox*Listbox.background",        c['card_bg'])
        win.option_add("*TCombobox*Listbox.foreground",        c['text_dark'])
        win.option_add("*TCombobox*Listbox.selectBackground",  c['tree_sel_bg'])
        win.option_add("*TCombobox*Listbox.selectForeground",  c['tree_sel_fg'])
        win.option_add("*TCombobox*Listbox.font", ("Segoe UI", 12))

    # ── Construcción de la interfaz ───────────────────────────────────────────
    def crear_interfaz(self):
        self._aplicar_estilo_tabla()
        c = self.colors

        # Cabecera
        header = ctk.CTkFrame(self.container, fg_color="transparent")
        header.pack(fill="x", pady=(0, 16))

        left = ctk.CTkFrame(header, fg_color="transparent")
        left.pack(side="left")

        ctk.CTkLabel(left, text="📊 " + t("historial"),
                     font=("Segoe UI", 20, "bold"),
                     text_color=c['text_dark']).pack(anchor="w")
        ctk.CTkLabel(left, text="📝 " + t("registro_intentos"),
                     font=("Segoe UI", 12),
                     text_color=c['text_gray']).pack(anchor="w", pady=(2, 0))

        btn_row = ctk.CTkFrame(header, fg_color="transparent")
        btn_row.pack(side="right")

        ctk.CTkButton(btn_row, text="🗑️",
                      fg_color=c['danger'], hover_color=COLORS['danger_dark'],
                      text_color="#ffffff", font=("Segoe UI", 12, "bold"),
                      width=36, height=38, corner_radius=8,
                      command=self.limpiar_historial).pack(side="left", padx=(4, 4))

        ctk.CTkButton(btn_row, text="🔄",
                      fg_color=c['primary'], hover_color=COLORS['primary_dark'],
                      text_color="#ffffff", font=("Segoe UI", 12, "bold"),
                      corner_radius=10, width=50, height=38,
                      command=self.cargar_datos).pack(side="left")

        # Tarjetas stats
        stats_row = ctk.CTkFrame(self.container, fg_color="transparent")
        stats_row.pack(fill="x", pady=(0, 14))
        stats_row.grid_columnconfigure((0, 1, 2), weight=1, uniform="stat")

        self.lbl_total     = self._stat_card(stats_row, t("accesos"),   "0", COLORS['primary'], "🔢", 0)
        self.lbl_aceptados = self._stat_card(stats_row, t("aceptados"), "0", "#27AE60",         "✅", 1)
        self.lbl_denegados = self._stat_card(stats_row, t("denegados"), "0", COLORS['danger'],  "❌", 2)

        # Filtros
        filtros = ctk.CTkFrame(self.container, fg_color=c['card_bg'],
                               corner_radius=12, border_width=1,
                               border_color=COLORS['border'])
        filtros.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(filtros, text="🔍 " + t("buscar"),
                     text_color=c['text_dark'],
                     font=("Segoe UI", 10, "bold")).pack(side="left", padx=(14, 6), pady=10)

        self.busqueda_var = tk.StringVar()
        self.entrada_busqueda = ctk.CTkEntry(
            filtros, textvariable=self.busqueda_var,
            font=("Segoe UI", 10), width=60, height=36, corner_radius=10,
            fg_color=c['content_bg'], border_color=COLORS['border'],
            text_color=c['text_gray'])
        self.entrada_busqueda.pack(side="left", padx=(0, 16), pady=10)
        self.entrada_busqueda.insert(0, t("placeholder_usuario"))
        self.entrada_busqueda.bind("<FocusIn>",    self.limpiar_placeholder)
        self.entrada_busqueda.bind("<FocusOut>",   self.restaurar_placeholder)
        self.entrada_busqueda.bind("<KeyRelease>", lambda e: self.filtrar_tabla())

        ctk.CTkLabel(filtros, text="📊 " + t("estado"),
                     text_color=c['text_dark'],
                     font=("Segoe UI", 10, "bold")).pack(side="left", padx=(0, 6), pady=10)

        self.filtro_estado = ttk.Combobox(
            filtros,
            values=[t("todos"), t("aceptado"), t("denegado")],
            state="readonly", width=10,
            font=("Segoe UI", 12), style='Dark.TCombobox')
        self.filtro_estado.set(t("todos"))
        self.filtro_estado.pack(side="left", pady=10)
        self.filtro_estado.bind('<<ComboboxSelected>>', lambda e: self.filtrar_tabla())

        # Cuerpo principal: tabla + panel detalles lado a lado
        self.body = ctk.CTkFrame(self.container, fg_color="transparent")
        self.body.pack(fill="both", expand=True)
        self.body.grid_columnconfigure(0, weight=1)
        self.body.grid_columnconfigure(1, weight=0)
        self.body.grid_rowconfigure(0, weight=1)

        # ── Tabla ──────────────────────────────────────────────────────────────
        tabla_card = ctk.CTkFrame(self.body, fg_color=c['card_bg'],
                                  corner_radius=12, border_width=1,
                                  border_color=COLORS['border'])
        tabla_card.grid(row=0, column=0, sticky="nsew", padx=(0, 0))

        tabla_header = ctk.CTkFrame(tabla_card, fg_color="transparent")
        tabla_header.pack(fill="x", padx=16, pady=(12, 6))

        ctk.CTkLabel(tabla_header, text="📋 " + t("registros"),
                     font=FontScale.fb(13),
                     text_color=c['text_dark']).pack(side="left")

        self.lbl_conteo = ctk.CTkLabel(tabla_header, text="0 " + t("registros"),
                                        font=("Segoe UI", 11),
                                        text_color=c['text_gray'])
        self.lbl_conteo.pack(side="right")

        scroll_y = ttk.Scrollbar(tabla_card, orient="vertical",
                                  style='Dark.Vertical.TScrollbar')
        scroll_y.pack(side="right", fill="y", padx=(0, 4))

        scroll_x = ttk.Scrollbar(tabla_card, orient="horizontal",
                                  style='Dark.Horizontal.TScrollbar')
        scroll_x.pack(side="bottom", fill="x", pady=(0, 4))

        self.tree = ttk.Treeview(
            tabla_card,
            columns=("usuario", "fecha", "estado"),
            show="headings",
            yscrollcommand=scroll_y.set,
            xscrollcommand=scroll_x.set,
            height=15, style='Dark.Treeview')

        scroll_y.configure(command=self.tree.yview)
        scroll_x.configure(command=self.tree.xview)

        for col, label, w, anchor in [
            ("usuario",   "👤 " + t("usuario"),    280, "w"),
            ("fecha",     "🕐 " + t("fecha_hora"), 200, "center"),
            ("estado",    "📊 " + t("estado"),     150, "center"),
        ]:
            self.tree.heading(col, text=label)
            self.tree.column(col, width=w, anchor=anchor)

        self.tree.pack(fill="both", expand=True, padx=4)
        self.tree.tag_configure('aceptado',
                                background=c['tree_aceptado_bg'],
                                foreground=c['tree_aceptado_fg'])
        self.tree.tag_configure('denegado',
                                background=c['tree_denegado_bg'],
                                foreground=c['tree_denegado_fg'])

        self.tree.bind('<<TreeviewSelect>>', self._on_select)

        # ── Panel de detalles (oculto al inicio) ───────────────────────────────
        self.detalles_card = ctk.CTkFrame(self.body, fg_color=c['card_bg'],
                                          corner_radius=12, border_width=1,
                                          border_color=COLORS['border'],
                                          width=280)
        # No se hace grid aquí; se muestra/oculta dinámicamente

    def _stat_card(self, parent, titulo, valor, color, icono, col):
        c = self.colors
        card = ctk.CTkFrame(parent, fg_color=c['card_bg'],
                            corner_radius=12, border_width=1,
                            border_color=COLORS['border'])
        card.grid(row=0, column=col, padx=6, sticky="ew")

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(padx=8, pady=12, fill="x")

        top = ctk.CTkFrame(inner, fg_color="transparent")
        top.pack(fill="x")
        ctk.CTkLabel(top, text=titulo, font=("Segoe UI", 11, "bold"),
                     text_color=color, anchor="w").pack(side="left")
        ctk.CTkLabel(top, text=icono,
                     font=("Segoe UI Emoji", 16)).pack(side="right")

        lbl = ctk.CTkLabel(inner, text=valor,
                           font=("Segoe UI", 30, "bold"),
                           text_color=c['text_dark'], anchor="w")
        lbl.pack(anchor="w", pady=(4, 0))
        return lbl

    # ── Placeholder ───────────────────────────────────────────────────────────
    def limpiar_placeholder(self, event):
        if not self._is_alive():
            return
        if self._placeholder_activo:
            self.entrada_busqueda.delete(0, tk.END)
            self.entrada_busqueda.configure(text_color=self.colors['text_dark'])
            self._placeholder_activo = False

    def restaurar_placeholder(self, event):
        if not self._is_alive():
            return
        if not self.entrada_busqueda.get():
            self.entrada_busqueda.insert(0, t("placeholder_usuario"))
            self.entrada_busqueda.configure(text_color=self.colors['text_gray'])
            self._placeholder_activo = True

    # ── Carga y filtrado de datos ─────────────────────────────────────────────
    def cargar_datos(self):
        if not self._is_alive():
            return
        try:
            conn = get_db()
            if not conn:
                messagebox.showerror(t("error"), t("error_db"))
                return

            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    a.idAcceso,
                    COALESCE(u.nombreUsuario || ' ' || u.apellidoPaternoUsuario, ?),
                    a.fechaHoraIntentoAcceso,
                    a.estado_acceso,
                    a.confianzaAcceso,
                    a.umbralConfianzaUsado
                FROM accesos a
                LEFT JOIN usuarios u ON a.fkIdUsuario = u.idUsuario
                ORDER BY a.fechaHoraIntentoAcceso DESC
            """, (t("desconocido"),))

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
            messagebox.showerror(t("error"), f"{str(e)}")

    def filtrar_tabla(self):
        if not self._is_alive():
            return
        for item in self.tree.get_children():
            self.tree.delete(item)

        busqueda      = "" if self._placeholder_activo else self.busqueda_var.get().lower().strip()
        estado_filtro = self.filtro_estado.get()
        conteo        = 0

        for dato in self.datos:
            id_acceso, nombre, fecha, estado, confianza, umbral = dato

            if estado_filtro != t("todos") and estado != estado_filtro.lower():
                continue
            if busqueda and busqueda not in nombre.lower():
                continue

            try:
                fecha_fmt = datetime.strptime(fecha, "%Y-%m-%d %H:%M:%S") \
                                    .strftime("%d/%m/%Y %H:%M:%S")
            except Exception:
                fecha_fmt = fecha or "—"

            estado_fmt = ("✅ " + t("aceptado")) if estado == "aceptado" \
                         else ("❌ " + t("denegado"))

            self.tree.insert("", "end", iid=str(id_acceso),
                             values=(
                                 nombre, fecha_fmt, estado_fmt,
                             ),
                             tags=(estado,))
            conteo += 1

        self.lbl_conteo.configure(text=f"{conteo} {t('registros')}")

    # ── Selección en tabla → panel de detalles ────────────────────────────────
    def _on_select(self, event):
        if not self._is_alive():
            return
        sel = self.tree.selection()
        if not sel:
            return
        id_acceso = int(sel[0])
        
        # Obtener el estado del acceso
        estado = None
        for dato in self.datos:
            if dato[0] == id_acceso:
                estado = dato[3]
                break
        
        # Solo mostrar detalles si fue denegado
        if estado != "denegado":
            self._ocultar_panel_detalles()
            return
        
        if id_acceso == self._acceso_seleccionado:
            return
        self._acceso_seleccionado = id_acceso
        self._mostrar_panel_detalles(id_acceso)

    def _mostrar_panel_detalles(self, id_acceso: int):
        """Consulta el acceso en BD y muestra el panel lateral con sus detalles."""
        if not self._is_alive():
            return
        c = self.colors

        try:
            conn = get_db()
            if not conn:
                return
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    ac.idAcceso,
                    COALESCE(u.nombreUsuario || ' ' || u.apellidoPaternoUsuario,
                             ?) AS nombre,
                    ac.fechaHoraIntentoAcceso,
                    ac.estado_acceso,
                    ac.confianzaAcceso,
                    ac.umbralConfianzaUsado,
                    ac.fotoAcceso
                FROM accesos ac
                LEFT JOIN usuarios u ON ac.fkIdUsuario = u.idUsuario
                WHERE ac.idAcceso = ?
            """, (t("desconocido"), id_acceso))
            fila = cursor.fetchone()
            conn.close()
        except Exception as e:
            messagebox.showerror(t("error"), str(e))
            return

        if not fila:
            return

        _, nombre, fecha, estado, confianza, umbral, foto_bytes = fila

        # Limpiar panel anterior
        for w in self.detalles_card.winfo_children():
            w.destroy()

        # Mostrar panel si estaba oculto
        self.detalles_card.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        # ── Encabezado del panel (fijo, sin scroll) ──────────────────────────
        header_panel = ctk.CTkFrame(self.detalles_card, fg_color="transparent")
        header_panel.pack(fill="x", padx=14, pady=(14, 0))

        ctk.CTkLabel(header_panel,
                     text="🔍 " + t("detalles_acceso") if hasattr(t, '__call__') else "🔍 Detalles",
                     font=("Segoe UI", 14, "bold"),
                     text_color=c['text_dark']).pack(side="left")

        ctk.CTkButton(header_panel, text="✕",
                      fg_color="transparent",
                      hover_color=c['card_bg'],
                      text_color=c['text_gray'],
                      font=("Segoe UI", 13, "bold"),
                      width=28, height=28, corner_radius=6,
                      command=self._ocultar_panel_detalles).pack(side="right")

        # Separador visual
        ctk.CTkFrame(self.detalles_card, fg_color=COLORS['border'],
                     height=1).pack(fill="x", padx=14, pady=(8, 12))

        # ── Contenido desplazable (scroll vertical) ──────────────────────────
        scroll_content = ctk.CTkScrollableFrame(self.detalles_card,
                                                fg_color="transparent")
        scroll_content.pack(fill="both", expand=True, padx=0, pady=0)

        # ── Foto capturada (dentro del scrollable) ────────────────────────────
        foto_frame = ctk.CTkFrame(scroll_content,
                                  fg_color=c['content_bg'],
                                  corner_radius=10)
        foto_frame.pack(fill="x", padx=14, pady=(0, 12))

        if foto_bytes:
            try:
                img = Image.open(io.BytesIO(foto_bytes))
                # Escalar manteniendo proporción dentro de 252 x 180
                img.thumbnail((252, 180), Image.LANCZOS)
                self._foto_ref = ImageTk.PhotoImage(img)
                lbl_foto = tk.Label(foto_frame, image=self._foto_ref,
                                    bg=c['content_bg'], bd=0)
                lbl_foto.pack(pady=8)
            except Exception:
                ctk.CTkLabel(foto_frame,
                             text="📷 " + "No se pudo cargar la foto",
                             font=("Segoe UI", 11),
                             text_color=c['text_gray']).pack(pady=20)
        else:
            # Acceso aceptado o denegado sin foto disponible
            icono  = "✅" if estado == "aceptado" else "📷"
            texto  = "Acceso aceptado" if estado == "aceptado" \
                     else "Sin foto disponible"
            ctk.CTkLabel(foto_frame, text=f"{icono}\n{texto}",
                         font=("Segoe UI", 11),
                         text_color=c['text_gray'],
                         justify="center").pack(pady=20)

        # ── Datos del acceso (dentro del scrollable) ──────────────────────────
        datos_frame = ctk.CTkFrame(scroll_content, fg_color="transparent")
        datos_frame.pack(fill="x", padx=14, pady=(0, 14))

        color_estado = "#27AE60" if estado == "aceptado" else COLORS['danger']
        icono_estado = "✅" if estado == "aceptado" else "❌"

        try:
            fecha_fmt = datetime.strptime(fecha, "%Y-%m-%d %H:%M:%S") \
                                .strftime("%d/%m/%Y  %H:%M:%S")
        except Exception:
            fecha_fmt = fecha or "—"

        filas_datos = [
            ("👤", t("usuario")   if callable(t) else "Usuario",   nombre),
            ("🕐", t("fecha_hora") if callable(t) else "Fecha",    fecha_fmt),
            ("📊", t("estado")    if callable(t) else "Estado",
             f"{icono_estado} {t('aceptado') if estado == 'aceptado' else t('denegado')}"),
        ]

        for icono, etiqueta, valor in filas_datos:
            fila_w = ctk.CTkFrame(datos_frame, fg_color="transparent")
            fila_w.pack(fill="x", pady=3)

            ctk.CTkLabel(fila_w, text=f"{icono} {etiqueta}",
                         font=("Segoe UI", 10, "bold"),
                         text_color=c['text_gray'],
                         anchor="w", width=110).pack(side="left")

            color_val = color_estado if etiqueta in (
                t("estado") if callable(t) else "Estado", "Estado"
            ) else c['text_dark']

            ctk.CTkLabel(fila_w, text=valor,
                         font=("Segoe UI", 10),
                         text_color=color_val,
                         anchor="w",
                         wraplength=130).pack(side="left", padx=(4, 0))

    def _ocultar_panel_detalles(self):
        """Oculta el panel de detalles y deselecciona la fila."""
        self._acceso_seleccionado = None
        self._foto_ref            = None
        self.detalles_card.grid_forget()
        if self.tree.selection():
            self.tree.selection_remove(self.tree.selection())

    # ── Limpiar historial ─────────────────────────────────────────────────────
    def limpiar_historial(self):
        if not self._is_alive():
            return
        respuesta = messagebox.askyesno(t("confirmar"), t("pregunta_limpiar_historial"))
        if not respuesta:
            return
        try:
            conn = get_db()
            if not conn:
                messagebox.showerror(t("error"), t("error_db"))
                return
            conn.cursor().execute("DELETE FROM accesos")
            conn.commit()
            conn.close()
            AccessCounter.set(0)
            self._ocultar_panel_detalles()
            messagebox.showinfo(t("confirmar"), t("historial_eliminado"))
            self.cargar_datos()
        except Exception as e:
            messagebox.showerror(t("error"), str(e))