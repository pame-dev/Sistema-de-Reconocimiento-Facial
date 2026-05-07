# views/informacion_escolar_view.py
"""
Orquestador de la vista de información escolar.
Toda la lógica específica vive en los mixins del sub-paquete:

    estilos.py          — ROL_COLOR, ROL_ICONO, _aplicar_estilo_tabla()
    datos_usuarios.py   — cargar_datos(), cargar_inactivos(), filtrar_tabla()
    panel_detalles.py   — crear_panel_detalles(), mostrar/ocultar detalles
    dialogo_edicion.py  — editar_usuario(), _guardar_edicion(), _retomar_fotos()
    acciones_usuario.py — eliminar_usuario(), restaurar_usuario()
"""
import tkinter as tk
from tkinter import ttk
import customtkinter as ctk

from config import COLORS, get_colors
from idiomas import t
from views.font_scale import FontScale
from views.informacion_escolar.estilos import EstilosMixin
from views.informacion_escolar.datos_usuarios import DatosUsuariosMixin
from views.informacion_escolar.panel_detalles import PanelDetallesMixin
from views.informacion_escolar.dialogo_edicion import DialogoEdicionMixin
from views.informacion_escolar.acciones_usuario import AccionesUsuarioMixin


class InformacionEscolarView(
    EstilosMixin,
    DatosUsuariosMixin,
    PanelDetallesMixin,
    DialogoEdicionMixin,
    AccionesUsuarioMixin,
):
    def __init__(self, parent):
        self.colors = get_colors()
        self.parent    = parent
        self.container = ctk.CTkFrame(parent, fg_color=self.colors['background'])
        self.container.view = self
        self.container.pack(fill="both", expand=True, padx=24, pady=20)

        self.usuario_seleccionado = None
        self.datos                = []
        self._placeholder_activo  = True
        self._small_layout        = False

        self.crear_interfaz()
        self.container.bind("<Configure>", self._on_root_resize)
        self.container.update_idletasks()
        self._apply_responsive_layout(self.container.winfo_width())

        # Botón restaurar (creado aquí para que acciones_frame ya exista)
        self.btn_restaurar = ctk.CTkButton(
            self.acciones_frame,
            text="🔄 Restaurar",
            fg_color=self.colors['primary'],
            hover_color=COLORS['primary_dark'],
            text_color="#ffffff",
            font=("Segoe UI", 12, "bold"),
            corner_radius=10, height=36,
            command=self.restaurar_usuario,
        )
        self.cargar_datos()

    # ── Ciclo de vida ─────────────────────────────────────────────────────────
    def destroy(self):
        try:
            self.container.unbind("<Configure>")
        except Exception:
            pass
        for widget_name in ('entrada_busqueda', 'filtro_rol', 'filtro_estado', 'tabla'):
            try:
                w = getattr(self, widget_name)
                for seq in ("<FocusIn>", "<FocusOut>", "<KeyRelease>",
                            "<<ComboboxSelected>>", "<<TreeviewSelect>>"):
                    try:
                        w.unbind(seq)
                    except Exception:
                        pass
            except Exception:
                pass

    def _is_alive(self):
        return (getattr(self, 'container', None) is not None
                and self.container.winfo_exists())

    # ── Layout responsivo ─────────────────────────────────────────────────────
    def _on_root_resize(self, event):
        if event.widget == self.container:
            self._apply_responsive_layout(event.width)

    def _is_small_screen(self):
        return self.parent.winfo_toplevel().winfo_width() < 900

    def _apply_responsive_layout(self, width):
        small = width < 900
        if small == self._small_layout:
            return
        self._small_layout = small
        if small:
            self.header_left.pack_forget()
            self.header_left.pack(side="top", fill="x", padx=0, pady=(0, 10))
            self.filtros_top.pack_configure(fill="x", pady=(10, 4))
            self.filtros_bottom.pack_configure(fill="x", pady=(0, 10))
            self.filtro_rol.configure(width=12)
            self.filtro_estado.configure(width=12)
        else:
            self.header_left.pack_forget()
            self.header_left.pack(side="left", fill="x", expand=True)
            self.filtros_top.pack_configure(fill="x", pady=(10, 4))
            self.filtros_bottom.pack_configure(fill="x", pady=(0, 10))
            self.filtro_rol.configure(width=8)
            self.filtro_estado.configure(width=10)

        if self.detalles_frame.winfo_ismapped() and self.usuario_seleccionado:
            self.crear_panel_detalles()

    # ── Construcción de la interfaz ───────────────────────────────────────────
    def crear_interfaz(self):
        self._aplicar_estilo_tabla()
        c = self.colors

        # Cabecera
        self.header = ctk.CTkFrame(self.container, fg_color="transparent")
        self.header.pack(fill="x", pady=(0, 14))

        self.header_left = ctk.CTkFrame(self.header, fg_color="transparent")
        self.header_left.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(self.header_left, text="📚  " + t("info_escolar"),
                     font=("Segoe UI", 24, "bold"),
                     text_color=c['text_dark']).pack(anchor="w")
        ctk.CTkLabel(self.header_left, text=t("gestion_usuarios"),
                     font=("Segoe UI", 11),
                     text_color=c['text_gray']).pack(anchor="w", pady=(2, 0))

        # Filtros
        filtros = ctk.CTkFrame(self.container, fg_color=c['card_bg'],
                               corner_radius=12, border_width=1,
                               border_color=COLORS['border'])
        filtros.pack(fill="x", pady=(0, 12))

        self.filtros_top = ctk.CTkFrame(filtros, fg_color="transparent")
        self.filtros_top.pack(fill="x", pady=(10, 4))
        self.filtros_bottom = ctk.CTkFrame(filtros, fg_color="transparent")
        self.filtros_bottom.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(self.filtros_top, text="🔍  " + t("buscar"),
                     text_color=c['text_dark'],
                     font=("Segoe UI", 10, "bold")).pack(side="left", padx=(2, 6), pady=10)

        self.busqueda_var = tk.StringVar()
        self.entrada_busqueda = ctk.CTkEntry(
            self.filtros_top,
            textvariable=self.busqueda_var,
            font=("Segoe UI", 10), width=200, height=36,
            corner_radius=10,
            fg_color=c['content_bg'],
            border_color=COLORS['border'],
            text_color=c['text_gray'],
        )
        self.entrada_busqueda.pack(side="left", padx=(0, 3), pady=10, fill="x", expand=True)
        self.entrada_busqueda.insert(0, t("placeholder_busqueda"))
        self.entrada_busqueda.bind("<FocusIn>",    self.limpiar_placeholder)
        self.entrada_busqueda.bind("<FocusOut>",   self.restaurar_placeholder)
        self.entrada_busqueda.bind("<KeyRelease>", lambda e: self.filtrar_tabla())

        ctk.CTkLabel(self.filtros_bottom, text=t("rol"),
                     text_color=c['text_dark'],
                     font=("Segoe UI", 10, "bold")).pack(side="left", padx=(3, 3), pady=10)

        self.filtro_rol = ttk.Combobox(
            self.filtros_bottom,
            values=[t("todos"), t("estudiante"), t("docente"), t("personal")],
            state="readonly", width=8,
            font=("Segoe UI", 12), style='Dark.TCombobox',
        )
        self.filtro_rol.set(t("todos"))
        self.filtro_rol.pack(side="left", pady=10)
        self.filtro_rol.bind('<<ComboboxSelected>>', lambda e: self.filtrar_tabla())

        ctk.CTkLabel(self.filtros_bottom, text=t("estado"),
                     text_color=c['text_dark'],
                     font=("Segoe UI", 10, "bold")).pack(side="left", padx=(3, 3), pady=10)

        self.filtro_estado = ttk.Combobox(
            self.filtros_bottom,
            values=[t("activos"), t("inactivos")],
            state="readonly", width=8,
            font=("Segoe UI", 12), style='Dark.TCombobox',
        )
        self.filtro_estado.set(t("activos"))
        self.filtro_estado.pack(side="left", pady=10)
        self.filtro_estado.bind('<<ComboboxSelected>>', lambda e: self.cambiar_estado())

        self.lbl_conteo = ctk.CTkLabel(self.filtros_bottom, text="",
                                        font=("Segoe UI", 11),
                                        text_color=c['text_gray'])
        self.lbl_conteo.pack(side="right", padx=4)

        # Panel detalles (oculto inicialmente)
        self.detalles_frame = ctk.CTkFrame(self.container, fg_color=c['card_bg'],
                                            corner_radius=12, border_width=1,
                                            border_color=COLORS['border'])
        self.crear_panel_detalles()
        self.detalles_frame.pack_forget()

        # Botones de acción (ocultos inicialmente)
        self.acciones_frame = ctk.CTkFrame(self.container, fg_color="transparent")

        self.btn_editar = ctk.CTkButton(
            self.acciones_frame, text="✏️  " + t("editar"),
            fg_color=c['header'], hover_color=COLORS['header_hover'],
            text_color="#ffffff",
            font=("Segoe UI", 12, "bold"), corner_radius=10, height=36,
            command=self.editar_usuario,
        )
        self.btn_editar.pack(side="left", padx=(0, 8))

        self.btn_eliminar = ctk.CTkButton(
            self.acciones_frame, text="🗑️  " + t("eliminar"),
            fg_color=c['danger'], hover_color=COLORS['danger_dark'],
            text_color="#ffffff",
            font=("Segoe UI", 12, "bold"), corner_radius=10, height=36,
            command=self.eliminar_usuario,
        )
        self.btn_eliminar.pack(side="left")

        # Tabla principal
        self.tabla_frame = ctk.CTkFrame(self.container, fg_color=c['card_bg'],
                                         corner_radius=12, border_width=1,
                                         border_color=COLORS['border'])
        self.tabla_frame.pack(fill="both", expand=True, pady=(0, 8))

        th = ctk.CTkFrame(self.tabla_frame, fg_color="transparent")
        th.pack(fill="x", padx=16, pady=(10, 4))
        ctk.CTkLabel(th, text=t("usuarios_registrados"),
                     font=FontScale.fb(13),
                     text_color=c['text_dark']).pack(side="left")

        scroll_y = ttk.Scrollbar(self.tabla_frame, orient="vertical",
                                  style='Dark.Vertical.TScrollbar')
        scroll_y.pack(side="right", fill="y", padx=(0, 4))

        scroll_x = ttk.Scrollbar(self.tabla_frame, orient="horizontal",
                                  style='Dark.Horizontal.TScrollbar')
        scroll_x.pack(side="bottom", fill="x", pady=(0, 4))

        self.tabla = ttk.Treeview(
            self.tabla_frame,
            columns=("nombre", "matricula", "fecha_nacimiento", "tipo_sangre", "rol", "fotos"),
            show="headings",
            yscrollcommand=scroll_y.set,
            xscrollcommand=scroll_x.set,
            height=14, style='Dark.Treeview',
        )
        scroll_y.configure(command=self.tabla.yview)
        scroll_x.configure(command=self.tabla.xview)

        for col, label, w, anchor in [
            ("nombre",           t("nombre_completo"),  260, "w"),
            ("matricula",        t("matricula"),         130, "center"),
            ("fecha_nacimiento", t("fecha_nacimiento"),  115, "center"),
            ("tipo_sangre",      t("tipo_sangre"),        95, "center"),
            ("rol",              t("rol"),               110, "center"),
            ("fotos",            f"📸 {t('fotos')}",     80, "center"),
        ]:
            self.tabla.heading(col, text=label)
            self.tabla.column(col, width=w, anchor=anchor)

        self.tabla.pack(fill="both", expand=True, padx=4)
        self.tabla.bind('<<TreeviewSelect>>', self.on_select)

        self.tabla.tag_configure('alumno',
            background=c['tree_aceptado_bg'], foreground=c['tree_fg'])
        self.tabla.tag_configure('maestro',
            background=c['card_bg'], foreground=c['tree_fg'])
        self.tabla.tag_configure('personal',
            background=c['tree_denegado_bg'], foreground=c['tree_fg'])

    # ── Selección en tabla ────────────────────────────────────────────────────
    def on_select(self, event):
        if not self._is_alive():
            return
        sel = self.tabla.selection()
        if not sel:
            return
        user_id = int(sel[0])
        self.usuario_seleccionado = next(
            (u for u in self.datos if u['id'] == user_id), None
        )
        if self.usuario_seleccionado:
            self.mostrar_detalles_panel()
            self.crear_panel_detalles()

    # ── Placeholder búsqueda ──────────────────────────────────────────────────
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
        if not self.busqueda_var.get().strip():
            self.entrada_busqueda.insert(0, t("placeholder_busqueda"))
            self.entrada_busqueda.configure(text_color=self.colors['text_gray'])
            self._placeholder_activo = True