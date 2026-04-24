# views/informacion_escolar_view.py
import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk
import sys
import os
from datetime import datetime
from tkcalendar import DateEntry
from views.font_scale import FontScale
from views import nuevo_registro_view
from idiomas import t   

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import COLORS, get_colors, toggle_theme, get_db
from database.queries import (
    sp_get_usuarios,
    sp_actualizar_usuario,
    sp_actualizar_alumno,
    sp_actualizar_maestro,
    sp_actualizar_personal,
    sp_eliminar_usuario,
    sp_get_usuarios_inactivos,
    sp_restaurar_usuario,
    sp_eliminar_usuario_definitivo,   # 👈 AGREGAR
    sp_vaciar_papelera  
)

ROL_COLOR = {"alumno": "#4A90D9", "maestro": "#27AE60", "personal": "#E67E22"}
ROL_ICONO = {"alumno": "🎓",      "maestro": "📚",      "personal": "🏢"}


class InformacionEscolarView:

    def __init__(self, parent):
        self.colors = get_colors()
        self.parent    = parent
        self.container = ctk.CTkFrame(parent, fg_color=self.colors['background'])
        self.container.pack(fill="both", expand=True, padx=24, pady=20)

        self.usuario_seleccionado = None
        self.datos                = []
        self._placeholder_activo  = True

        self.crear_interfaz()
        self.cargar_datos()

    # ── Aplica estilos ttk con colores del tema actual ────────────────────────
    def _aplicar_estilo_tabla(self):
        c = self.colors
        style = ttk.Style()
        style.theme_use('default')

        style.configure('Dark.Treeview',
            background=c['tree_bg'],
            fieldbackground=c['tree_bg'],
            foreground=c['tree_fg'],
            rowheight=32, borderwidth=0,
            font=("Segoe UI", 12),
        )
        style.configure('Dark.Treeview.Heading',
            background=c['tree_head_bg'],
            foreground=c['tree_head_fg'],
            font=("Segoe UI", 12, "bold"),
            relief='flat', padding=6,
        )
        style.map('Dark.Treeview',
            background=[('selected', c['tree_sel_bg'])],
            foreground=[('selected', c['tree_sel_fg'])],
        )
        style.map('Dark.Treeview.Heading',
            background=[('active', c['tree_head_bg'])],
        )

        style.configure('Dark.Vertical.TScrollbar',
            background=c['card_bg'], troughcolor=c['background'],
            arrowcolor=c['text_gray'], borderwidth=0)
        style.configure('Dark.Horizontal.TScrollbar',
            background=c['card_bg'], troughcolor=c['background'],
            arrowcolor=c['text_gray'], borderwidth=0)

        style.configure('Dark.TCombobox',
            fieldbackground=c['card_bg'], background=c['card_bg'],
            foreground=c['text_dark'], arrowcolor=c['text_gray'],
            bordercolor=c['border'], selectbackground=c['tree_sel_bg'],
            selectforeground=c['tree_sel_fg'],
        )
        style.map('Dark.TCombobox',
            fieldbackground=[('readonly', c['card_bg'])],
            foreground=[('readonly', c['text_dark'])],
            background=[('readonly', c['card_bg'])],
        )

        win = self.parent.winfo_toplevel()
        win.option_add("*TCombobox*Listbox.background",       c['card_bg'])
        win.option_add("*TCombobox*Listbox.foreground",       c['text_dark'])
        win.option_add("*TCombobox*Listbox.selectBackground", c['tree_sel_bg'])
        win.option_add("*TCombobox*Listbox.selectForeground", c['tree_sel_fg'])
        win.option_add("*TCombobox*Listbox.font",             ("Segoe UI", 13))

    # ── Interfaz ──────────────────────────────────────────────────────────────
    def crear_interfaz(self):
        self._aplicar_estilo_tabla()
        c = self.colors

        # Cabecera
        header = ctk.CTkFrame(self.container, fg_color="transparent")
        header.pack(fill="x", pady=(0, 14))

        left = ctk.CTkFrame(header, fg_color="transparent")
        left.pack(side="left")

        ctk.CTkLabel(left, text="📚  " + t("info_escolar"),
                     font=("Segoe UI", 24, "bold"),
                     text_color=c['text_dark']).pack(anchor="w")
        ctk.CTkLabel(left, text=t("gestion_usuarios"),
                     font=("Segoe UI", 11),
                     text_color=c['text_gray']).pack(anchor="w", pady=(2, 0))

        btn_row = ctk.CTkFrame(header, fg_color="transparent")
        btn_row.pack(side="right")

        ctk.CTkButton(btn_row, text="🗑",
                      fg_color=c['content_bg'], hover_color=COLORS['border'],
                      text_color=c['text_dark'],
                      font=("Segoe UI", 12, "bold"),
                      corner_radius=10, height=38, width=30,
                      command=self._papelera).pack(side="left", padx=(0, 8))

        self.btn_toggle_detalles = ctk.CTkButton(btn_row, text=t("ver_detalles"),
                      fg_color=c['header'], hover_color=COLORS['header_hover'],
                      text_color="#ffffff",
                      font=("Segoe UI", 12, "bold"),
                      corner_radius=10, height=38, width=70,
                      state="disabled",
                      command=self.toggle_detalles)
        self.btn_toggle_detalles.pack(side="left", padx=(0, 8))

        ctk.CTkButton(btn_row, text="🔄",
                      fg_color=c['primary'], hover_color=COLORS['primary_dark'],
                      text_color="#ffffff",
                      font=("Segoe UI", 12, "bold"),
                      corner_radius=10, height=38, width=50,
                      command=self._actualizar_todo).pack(side="left")

        # Filtros
        filtros = ctk.CTkFrame(self.container, fg_color=c['card_bg'],
                               corner_radius=12, border_width=1,
                               border_color=COLORS['border'])
        filtros.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(filtros, text="🔍  " + t("buscar"),
                     text_color=c['text_dark'],
                     font=("Segoe UI", 12, "bold")).pack(side="left", padx=(14, 6), pady=10)

        self.busqueda_var = tk.StringVar()
        self.entrada_busqueda = ctk.CTkEntry(filtros,
            textvariable=self.busqueda_var,
            font=("Segoe UI", 12), width=200, height=36,
            corner_radius=10,
            fg_color=c['content_bg'],
            border_color=COLORS['border'],
            text_color=c['text_gray'])
        self.entrada_busqueda.pack(side="left", padx=(0, 16), pady=10)
        self.entrada_busqueda.insert(0, t("placeholder_busqueda"))
        self.entrada_busqueda.bind("<FocusIn>",    self.limpiar_placeholder)
        self.entrada_busqueda.bind("<FocusOut>",   self.restaurar_placeholder)
        self.entrada_busqueda.bind("<KeyRelease>", lambda e: self.filtrar_tabla())

        ctk.CTkLabel(filtros, text=t("rol"),
                     text_color=c['text_dark'],
                     font=("Segoe UI", 12, "bold")).pack(side="left", padx=(0, 6), pady=10)

        self.filtro_rol = ttk.Combobox(filtros,
            values=[t("todos"), t("estudiante"), t("docente"), t("personal")],
            state="readonly", width=16,
            font=("Segoe UI", 12),
            style='Dark.TCombobox')
        self.filtro_rol.set(t("todos")),
        self.filtro_rol.pack(side="left", pady=10)
        self.filtro_rol.bind('<<ComboboxSelected>>', lambda e: self.filtrar_tabla())

        self.lbl_conteo = ctk.CTkLabel(filtros, text="",
                                        font=("Segoe UI", 11),
                                        text_color=c['text_gray'])
        self.lbl_conteo.pack(side="right", padx=14)

        # Panel de detalles (oculto)
        self.detalles_frame = ctk.CTkFrame(self.container, fg_color=c['card_bg'],
                                            corner_radius=12, border_width=1,
                                            border_color=COLORS['border'])
        self.crear_panel_detalles()
        self.detalles_frame.pack_forget()

        # Botones de acción (ocultos)
        self.acciones_frame = ctk.CTkFrame(self.container, fg_color="transparent")

        self.btn_editar = ctk.CTkButton(self.acciones_frame, text="✏️  " + t("editar"),
                      fg_color=c['header'], hover_color=COLORS['header_hover'],
                      text_color="#ffffff",
                      font=("Segoe UI", 12, "bold"),
                      corner_radius=10, height=36,
                      command=self.editar_usuario)
        self.btn_editar.pack(side="left", padx=(0, 8))

        self.btn_eliminar = ctk.CTkButton(self.acciones_frame, text="🗑️  " + t("eliminar"),
                      fg_color=c['danger'], hover_color=COLORS['danger_dark'],
                      text_color="#ffffff",
                      font=("Segoe UI", 12, "bold"),
                      corner_radius=10, height=36,
                      command=self.eliminar_usuario)
        self.btn_eliminar.pack(side="left")

        # Tabla
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

        self.tabla = ttk.Treeview(self.tabla_frame,
            columns=("id", "nombre", "matricula", "tipo_sangre", "rol", "fotos"),
            show="headings",
            yscrollcommand=scroll_y.set,
            xscrollcommand=scroll_x.set,
            height=14,
            style='Dark.Treeview')
        scroll_y.configure(command=self.tabla.yview)
        scroll_x.configure(command=self.tabla.xview)

        for col, label, w, anchor in [
            ("id", t("id"), 55, "center"),
            ("nombre",    t("nombre_completo"), 260, "w"),
            ("matricula", t("matricula"), 130, "center"),
            ("tipo_sangre", t("tipo_sangre"), 95, "center"),
            ("rol",       t("rol"), 110, "center"),
            ("fotos", f"📸 {t('fotos')}", 80, "center"),
        ]:
            self.tabla.heading(col, text=label)
            self.tabla.column(col, width=w, anchor=anchor)

        self.tabla.pack(fill="both", expand=True, padx=4)
        self.tabla.bind('<<TreeviewSelect>>', self.on_select)

        # Tags de color por rol
        self.tabla.tag_configure('alumno',
            background=c['tree_aceptado_bg'], foreground=c['tree_fg'])
        self.tabla.tag_configure('maestro',
            background=c['card_bg'], foreground=c['tree_fg'])
        self.tabla.tag_configure('personal',
            background=c['tree_denegado_bg'], foreground=c['tree_fg'])

    # ── Panel detalles ────────────────────────────────────────────────────────
    def crear_panel_detalles(self):
        for w in self.detalles_frame.winfo_children():
            w.destroy()
        if not self.usuario_seleccionado:
            return

        c     = self.colors
        u     = self.usuario_seleccionado
        rol   = u.get('rol', '')
        color = ROL_COLOR.get(rol, COLORS['primary'])
        icono = ROL_ICONO.get(rol, '👤')

        ph = ctk.CTkFrame(self.detalles_frame, fg_color=color, corner_radius=0, height=36)
        ph.pack(fill="x")
        ph.pack_propagate(False)

        nombre_completo = f"{u.get('nombre','')} {u.get('apellido_paterno','')} {u.get('apellido_materno','')}".strip()
        ctk.CTkLabel(ph,
            text=f"  {icono}  {nombre_completo}  —  {rol.capitalize()}",
            font=("Segoe UI", 12, "bold"), text_color="#ffffff"
        ).pack(side="left", padx=14, pady=8)

        stats_row = ctk.CTkFrame(ph, fg_color="transparent")
        stats_row.pack(side="right", padx=14)
        for txt, val in [("📸", u.get('fotos', 0)), ("🔐", u.get('accesos', 0))]:
            chip = ctk.CTkFrame(stats_row, fg_color="white", corner_radius=6)
            chip.pack(side="left", padx=3)
            ctk.CTkLabel(chip, text=f"  {txt} {val}  ",
                         font=("Segoe UI", 10, "bold"),
                         text_color=color).pack(padx=2, pady=3)

        body = ctk.CTkFrame(self.detalles_frame, fg_color="transparent")
        body.pack(fill="x", padx=16, pady=10)

        for ci, col_items in enumerate(self._get_cols_data(u, rol)):
            col_frame = ctk.CTkFrame(body, fg_color="transparent")
            col_frame.pack(side="left", fill="x", expand=True, padx=(0, 16))
            for label, valor in col_items:
                self._detail_item(col_frame, label, valor, color)

    def _get_cols_data(self, u, rol):
        col1 = [(t("nombre"), u.get('nombre','—')),
                (t("apellido_paterno"), u.get('apellido_paterno','—')),
                (t("apellido_materno"), u.get('apellido_materno','—')),]
        col2 = [(t("matricula"), u.get('matricula','—')),
                (t("telefono"), u.get('telefono','—')),
            (t("fecha_nacimiento"), u.get('fecha_nacimiento','—')),
            (t("tipo_sangre"), u.get('tipo_sangre','—')),
                (t("rol"), rol.capitalize()),]
        col3 = []
        if rol == 'alumno':
            col3 = [(t("facultad"), u.get('facultad','—')), (t("carrera"), u.get('carrera','—')),
                    (t("grado"), u.get('grado','—')), (t("grupo"), u.get('grupo','—'))]
        elif rol == 'maestro':
            col3 = [(t("materia"), u.get('materia','—')), (t("grado_imparte"), u.get('grado','—'))]
        elif rol == 'personal':
            col3 = [(t("puesto"), u.get('puesto','—')), (t("area"), u.get('area','—'))]
        return [c for c in [col1, col2, col3] if c]

    def _detail_item(self, parent, label, valor, color):
        c   = self.colors
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=2)
        ctk.CTkLabel(row, text=label+":",
                     font=("Segoe UI", 10),
                     text_color=c['text_gray'],
                     width=130, anchor="w").pack(side="left")
        ctk.CTkLabel(row, text=str(valor),
                     font=("Segoe UI", 10, "bold"),
                     text_color=c['text_dark'],
                     anchor="w").pack(side="left")

    # ── Datos ─────────────────────────────────────────────────────────────────
    def _actualizar_todo(self):
        self.filtro_rol.set(t("todos"))
        self.busqueda_var.set("")
        self.entrada_busqueda.delete(0, tk.END)
        self.entrada_busqueda.insert(0, t("placeholder_busqueda"))
        self.entrada_busqueda.configure(text_color=self.colors['text_gray'])
        self._placeholder_activo = True
        self.cargar_datos()

    def cargar_datos(self):
        try:
            conn = get_db()
            if not conn:
                messagebox.showerror(t("error"), t("error_db"))
                return
            resultados = sp_get_usuarios(conn)
            conn.close()

            self.datos = []
            for row in resultados:
                rol = row[5]
                if rol == 'alumno':
                    carrera, grado, grupo = row[9] or '—', row[10] or '—', row[11] or '—'
                elif rol == 'maestro':
                    carrera, grado, grupo = row[12] or '—', row[13] or '—', '—'
                else:
                    carrera, grado, grupo = row[14] or '—', '—', '—'

                self.datos.append({
                    'id':              row[0],
                    'nombre':          row[1] or '',
                    'apellido_paterno':row[2] or '—',
                    'apellido_materno':row[3] or '—',
                    'matricula':       row[4] or '—',
                    'rol':             rol,
                    'telefono':        row[6] or '—',
                    'fecha_nacimiento': row[7] or '—',
                    'tipo_sangre':     row[8] or '—',
                    'carrera':         carrera,
                    'grado':           grado,
                    'grupo':           grupo,
                    'materia':         row[12] or '—',
                    'puesto':          row[14] or '—',
                    'area':            row[15] or '—',
                    'facultad':        row[11] if rol == 'alumno' else '—',
                    'fotos':           row[16] or 0,
                    'accesos':         row[17] or 0,
                })
            self.actualizar_tabla()
        except Exception as e:
            messagebox.showerror(t("error"), t("error_cargar_datos").format(e))
            self.datos = []

    def actualizar_tabla(self, datos_filtrados=None):
        for item in self.tabla.get_children():
            self.tabla.delete(item)

        lista = datos_filtrados if datos_filtrados is not None else self.datos
        for u in lista:
            nombre_completo = f"{u.get('nombre','')} {u.get('apellido_paterno','')} {u.get('apellido_materno','')}".strip()
            self.tabla.insert("", "end", values=(
                u['id'], nombre_completo, u['matricula'], u.get('tipo_sangre', '—'), u['rol'], u['fotos']
            ), tags=(u.get('rol',''),))

        total = len(lista)
        self.lbl_conteo.configure(
            text=t("usuarios_total").format(total, "s" if total != 1 else "")
        )

    def filtrar_tabla(self):
        rol_filtro = self.filtro_rol.get()
        texto = "" if self._placeholder_activo else self.busqueda_var.get().lower().strip()

        resultado = [
            u for u in self.datos
            if (rol_filtro == t("todos") or str(u.get('rol','')).lower() == rol_filtro)
            and (not texto
                or texto in str(u.get('nombre','')).lower()
                or texto in str(u.get('matricula','')).lower()
                or texto in str(u.get('carrera','')).lower())
        ]
        self.actualizar_tabla(resultado)

    # ── Placeholder ───────────────────────────────────────────────────────────
    def limpiar_placeholder(self, event):
        if self._placeholder_activo:
            self.entrada_busqueda.delete(0, tk.END)
            self.entrada_busqueda.configure(text_color=self.colors['text_dark'])
            self._placeholder_activo = False

    def restaurar_placeholder(self, event):
        if not self.busqueda_var.get().strip():
            self.entrada_busqueda.insert(0, t("placeholder_busqueda"))
            self.entrada_busqueda.configure(text_color=self.colors['text_gray'])
            self._placeholder_activo = True

    # ── Selección ─────────────────────────────────────────────────────────────
    def on_select(self, event):
        sel = self.tabla.selection()
        if not sel:
            return
        user_id = self.tabla.item(sel[0])['values'][0]
        for u in self.datos:
            if u['id'] == user_id:
                self.usuario_seleccionado = u
                break
        self.mostrar_detalles_panel()
        self.crear_panel_detalles()

    def mostrar_detalles_panel(self):
        if not self.detalles_frame.winfo_ismapped():
            self.detalles_frame.pack(fill="x", pady=(0, 8), before=self.tabla_frame)
        if not self.acciones_frame.winfo_ismapped():
            self.acciones_frame.pack(fill="x", pady=(0, 6), before=self.detalles_frame)
        self.btn_toggle_detalles.configure(state="normal", text=t("ocultar_detalles"))
        self.container.update_idletasks()

    def ocultar_detalles_panel(self):
        if self.acciones_frame.winfo_ismapped():
            self.acciones_frame.pack_forget()
        if self.detalles_frame.winfo_ismapped():
            self.detalles_frame.pack_forget()
        self.btn_toggle_detalles.configure(text=t("ver_detalles"))

    def toggle_detalles(self):
        if self.detalles_frame.winfo_ismapped():
            self.ocultar_detalles_panel()
        elif self.usuario_seleccionado:
            self.mostrar_detalles_panel()
            self.crear_panel_detalles()
        else:
            messagebox.showinfo(t("detalles"), t("selecciona_usuario"))

    # ── Editar ────────────────────────────────────────────────────────────────
    def editar_usuario(self):
        if not self.usuario_seleccionado:
            messagebox.showwarning(t("atencion"), t("selecciona_usuario"))
            return

        c     = self.colors
        u     = self.usuario_seleccionado
        color = ROL_COLOR.get(u.get('rol', ''), COLORS['primary'])

        def _val(key):
            v = u.get(key, '')
            return '' if v in ('—', None) else str(v)

        # ── Variables compartidas ─────────────────────────────────────────────
        vars_ = {
            'nombre':    tk.StringVar(value=_val('nombre')),
            'paterno':   tk.StringVar(value=_val('apellido_paterno')),
            'materno':   tk.StringVar(value=_val('apellido_materno')),
            'matricula': tk.StringVar(value=_val('matricula')),
            'telefono':  tk.StringVar(value=_val('telefono')),
            'fecha_nacimiento': tk.StringVar(value=_val('fecha_nacimiento')),
            'tipo_sangre': tk.StringVar(value=_val('tipo_sangre')),
            'rol':       tk.StringVar(value=u['rol']),
            # específicos — se rellenan/vacían al cambiar rol
            'facultad':  tk.StringVar(value=_val('facultad')),
            'carrera':   tk.StringVar(value=_val('carrera')),
            'grado':     tk.StringVar(value=_val('grado')),
            'grupo':     tk.StringVar(value=_val('grupo')),
            'materia':   tk.StringVar(value=_val('materia')),
            'puesto':    tk.StringVar(value=_val('puesto')),
            'area':      tk.StringVar(value=_val('area')),
        }
        originales = {k: v.get() for k, v in vars_.items()}

        # ── Ventana ───────────────────────────────────────────────────────────
        win = ctk.CTkToplevel(self.parent)
        win.title(t("editar_usuario"))
        win.geometry("520x660")
        win.configure(fg_color=c['background'])
        win.grab_set()
        win.resizable(False, False)

        # Header con color de rol
        wh = ctk.CTkFrame(win, fg_color=color, corner_radius=0, height=54)
        wh.pack(fill="x")
        wh.pack_propagate(False)

        icono_rol = ROL_ICONO.get(u['rol'], '👤')
        nombre_completo = f"{_val('nombre')} {_val('apellido_paterno')}".strip()
        ctk.CTkLabel(wh,
        text=f"  {icono_rol}  {t('editar')} — {nombre_completo}",
        font=FontScale.fb(13), text_color="white"
    ).pack(side="left", padx=16, pady=14)

        # ── Scroll principal ──────────────────────────────────────────────────
        scroll_outer = ctk.CTkScrollableFrame(win, fg_color="transparent")
        scroll_outer.pack(fill="both", expand=True, padx=0, pady=0)

        # ── Sección: Datos personales ─────────────────────────────────────────
        def section_header(parent, texto, sec_color):
            f = ctk.CTkFrame(parent, fg_color="transparent")
            f.pack(fill="x", padx=20, pady=(14, 4))
            ctk.CTkLabel(f, text=texto,
                         font=("Segoe UI", 11, "bold"),
                         text_color=sec_color).pack(side="left")
            ctk.CTkFrame(f, fg_color=COLORS['border'],
                         height=1, corner_radius=0).pack(side="left", fill="x", expand=True, padx=(8, 0))

        def make_entry(parent, label_text, var, key=None):
            """Crea una fila label + entry y devuelve el CTkEntry."""
            row = ctk.CTkFrame(parent, fg_color="transparent")
            row.pack(fill="x", padx=20, pady=4)
            ctk.CTkLabel(row, text=label_text,
                         font=("Segoe UI", 10),
                         text_color=c['text_gray'],
                         width=130, anchor="w").pack(side="left")
            if key == "fecha_nacimiento":
                e = DateEntry(
                    row,
                    date_pattern='dd-mm-yyyy',
                    maxdate=datetime.now(),
                    font=("Segoe UI", 11),
                    textvariable=var,
                )
                if var.get().strip() not in ('', '—'):
                    valor = var.get().strip()
                    for fmt in ('%d-%m-%Y', '%Y-%m-%d'):
                        try:
                            e.set_date(datetime.strptime(valor, fmt))
                            break
                        except Exception:
                            pass
                e.bind("<<DateEntrySelected>>", lambda _event, v=var, widget=e: v.set(widget.get()))

            elif key == "tipo_sangre":
                e = ttk.Combobox(
                    row,
                    values=[
                        "A+", "A-",
                        "B+", "B-",
                        "AB+", "AB-",
                        "O+", "O-"
                    ],
                    state="readonly",
                    font=("Segoe UI", 11),
                    textvariable=var,
                )
                if var.get().strip() in e['values']:
                    e.set(var.get().strip())

            else:
                e = ctk.CTkEntry(row, textvariable=var,
                                 font=("Segoe UI", 11), height=34,
                                 corner_radius=8,
                                 border_color=COLORS['border'],
                                 fg_color=c['content_bg'],
                                 text_color=c['text_dark'])
            e.pack(side="left", fill="x", expand=True)
            return e

        section_header(scroll_outer, t("datos_personales"), color)
        make_entry(scroll_outer, t("nombre_req"), vars_['nombre'])
        make_entry(scroll_outer, t("apellido_paterno_req"), vars_['paterno'])
        make_entry(scroll_outer, t("apellido_materno"), vars_['materno'])
        make_entry(scroll_outer, t("matricula"), vars_['matricula'])
        make_entry(scroll_outer, t("telefono"), vars_['telefono'])
        make_entry(scroll_outer, t("fecha_nacimiento"), vars_['fecha_nacimiento'], key="fecha_nacimiento")
        make_entry(scroll_outer, t("tipo_sangre"), vars_['tipo_sangre'], key="tipo_sangre")

        # Rol — combobox
        rol_row = ctk.CTkFrame(scroll_outer, fg_color="transparent")
        rol_row.pack(fill="x", padx=20, pady=4)
        ctk.CTkLabel(rol_row, text=t("rol"),
                     font=("Segoe UI", 10),
                     text_color=c['text_gray'],
                     width=130, anchor="w").pack(side="left")
        combo_rol = ttk.Combobox(rol_row, textvariable=vars_['rol'],
                                  values=["alumno", "maestro", "personal"],
                                  state="readonly", width=24,
                                  font=("Segoe UI", 11),
                                  style='Dark.TCombobox')
        combo_rol.pack(side="left")

        # ── Sección dinámica (se destruye y recrea al cambiar rol) ────────────
        self._sec_rol_frame = ctk.CTkFrame(scroll_outer, fg_color="transparent")
        self._sec_rol_frame.pack(fill="x")

        def construir_seccion_rol(*_):
            # Limpiar sección anterior
            for w in self._sec_rol_frame.winfo_children():
                w.destroy()

            rol = vars_['rol'].get()

            TITULOS = {
                'alumno':   (t("info_academica"), "#4A90D9"),
                'maestro':  (t("info_docente"), "#27AE60"),
                'personal': (t("info_laboral"), "#E67E22"),
            }
            titulo, col_sec = TITULOS.get(rol, ("Datos adicionales", color))
            section_header(self._sec_rol_frame, titulo, col_sec)

            if rol == 'alumno':
                make_entry(self._sec_rol_frame, t("facultad"),  vars_['facultad'])
                make_entry(self._sec_rol_frame, t("carrera"),   vars_['carrera'])
                make_entry(self._sec_rol_frame, t("grado"),     vars_['grado'])
                make_entry(self._sec_rol_frame, t("grupo"),     vars_['grupo'])

            elif rol == 'maestro':
                make_entry(self._sec_rol_frame, t("grado_imparte"), vars_['grado'])
                make_entry(self._sec_rol_frame, t("materia"),        vars_['materia'])

            elif rol == 'personal':
                make_entry(self._sec_rol_frame, t("puesto"), vars_['puesto'])
                make_entry(self._sec_rol_frame, t("area"),   vars_['area'])

        combo_rol.bind("<<ComboboxSelected>>", construir_seccion_rol)
        construir_seccion_rol()   # construir con el rol actual

        # ── Botones ───────────────────────────────────────────────────────────
        sep = ctk.CTkFrame(win, fg_color=COLORS['border'], height=1, corner_radius=0)
        sep.pack(fill="x", pady=(8, 0))

        btn_row = ctk.CTkFrame(win, fg_color=c['card_bg'])
        btn_row.pack(fill="x", padx=20, pady=12)

        btn_guardar = ctk.CTkButton(btn_row, text="💾  " + t("guardar"),
                      fg_color=c['primary'], hover_color=COLORS['primary_dark'],
                      text_color="#ffffff", font=("Segoe UI", 12, "bold"),
                      corner_radius=10, height=38, state="disabled",
                      command=lambda: self._guardar_edicion(u['id'], vars_, win))
        btn_guardar.pack(side="left", padx=(0, 8))

        ctk.CTkButton(btn_row, text="🔁  " + t("retomar_fotos"),
                      fg_color=c['accent'], hover_color="#D97706",
                      text_color="#ffffff", font=("Segoe UI", 12, "bold"),
                      corner_radius=10, height=38,
                      command=lambda: self._retomar_fotos(u, win)).pack(side="left", padx=(0, 8))

        ctk.CTkButton(btn_row, text=t("cancelar"),
                      fg_color=c['content_bg'], hover_color=COLORS['border'],
                      text_color=c['text_dark'], font=("Segoe UI", 12, "bold"),
                      corner_radius=10, height=38,
                      command=win.destroy).pack(side="left")

        def detectar_cambios(*_):
            changed = any(v.get() != originales[k] for k, v in vars_.items())
            btn_guardar.configure(state="normal" if changed else "disabled")

        for v in vars_.values():
            v.trace_add("write", detectar_cambios)

    def _guardar_edicion(self, user_id, vars_, ventana):
        g = lambda k: vars_[k].get().strip()

        nombre    = g('nombre')
        paterno   = g('paterno')
        materno   = g('materno')
        matricula = g('matricula')
        telefono  = g('telefono')
        rol       = g('rol')

        if not nombre or not paterno:
            messagebox.showwarning(t("campos_obligatorios"), t("error_nombre"))
            return

        try:
            conn   = get_db()
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE usuarios SET
                    nombreUsuario          = ?,
                    apellidoPaternoUsuario = ?,
                    apellidoMaternoUsuario = ?,
                    matriculaUsuario       = ?,
                    telefonoUsuario        = ?,
                    fechaNacimientoUsuario = ?,
                    tipoSangreUsuario      = ?,
                    rolUsuario             = ?
                WHERE idUsuario = ?
            """, (
                nombre,
                paterno,
                materno,
                matricula,
                telefono,
                g('fecha_nacimiento'),
                g('tipo_sangre'),
                rol,
                user_id,
            ))

            cursor.execute("DELETE FROM alumnos          WHERE fkIdUsuario = ?", (user_id,))
            cursor.execute("DELETE FROM maestros         WHERE fkIdUsuario = ?", (user_id,))
            cursor.execute("DELETE FROM personal_escolar WHERE fkIdUsuario = ?", (user_id,))

            if rol == "alumno":
                cursor.execute("""
                    INSERT INTO alumnos
                        (fkIdUsuario, facultadAlumno, carreraAlumno, gradoAlumno, grupoAlumno)
                    VALUES (?, ?, ?, ?, ?)
                """, (user_id, g('facultad'), g('carrera'), g('grado'), g('grupo')))

            elif rol == "maestro":
                cursor.execute("""
                    INSERT INTO maestros
                        (fkIdUsuario, gradoImpartidoMaestro, materiaImpartidaMaestro)
                    VALUES (?, ?, ?)
                """, (user_id, g('grado'), g('materia')))

            elif rol == "personal":
                cursor.execute("""
                    INSERT INTO personal_escolar
                        (fkIdUsuario, puestoPersonalEscolar, areaPersonalEscolar)
                    VALUES (?, ?, ?)
                """, (user_id, g('puesto'), g('area')))

            conn.commit()
            conn.close()
            messagebox.showinfo(t("actualizado"), t("usuario_actualizado"))
            ventana.destroy()
            self.cargar_datos()

        except Exception as e:
            messagebox.showerror(t("error"), t("no_actualizar").format(e))


    def _retomar_fotos(self, usuario, ventana_actual):
        try:
            from views.nuevo_registro_view import NuevoRegistroView
            ventana_actual.destroy()
            for widget in self.parent.winfo_children():
                widget.destroy()

            nuevo_reg = NuevoRegistroView(self.parent)
            nuevo_reg.modo_retomar_fotos = True
            nuevo_reg.user_id_existente  = usuario.get("id")
            nuevo_reg.rol_actual         = usuario.get('rol', 'alumno')
            nuevo_reg._mostrar_formulario()

            campo_map = {
                'nombreUsuario':          'nombre',
                'apellidoPaternoUsuario': 'paterno',
                'apellidoMaternoUsuario': 'materno',
                'matriculaUsuario':       'matricula',
                'telefonoUsuario':        'telefono',
                'correoUsuario':          'correo',
                'gradoAlumno':            'grado',
                'grupoAlumno':            'grupo',
                'carreraAlumno':          'carrera',
            }
            for entry_key, user_key in campo_map.items():
                valor = usuario.get(user_key, '')
                if entry_key in nuevo_reg.entries and valor:
                    nuevo_reg.entries[entry_key].delete(0, tk.END)
                    nuevo_reg.entries[entry_key].insert(0, valor)

            nuevo_reg.valores_form = {k: e.get().strip() for k, e in nuevo_reg.entries.items()}
            nuevo_reg.parent.after(200, nuevo_reg._mostrar_captura)

        except Exception as e:
            messagebox.showerror(t("error"), t("error_captura").format(e))

    # ── Eliminar ──────────────────────────────────────────────────────────────
    def eliminar_usuario(self):
        if not self.usuario_seleccionado:
            return
        u = self.usuario_seleccionado
        if not messagebox.askyesno(
            t("confirmar_eliminacion"),
            t("eliminar_usuario_msg").format(
                nombre=u['nombre'],
                apellido=u.get('apellido_paterno',''),
                rol=u['rol']
            )
        ):
            return
        try:
            conn = get_db()
            sp_eliminar_usuario(conn, u['id'])
            conn.commit()
            conn.close()
            self.usuario_seleccionado = None
            self.ocultar_detalles_panel()
            self.cargar_datos()
            messagebox.showinfo("✅ Eliminado", f"{u['nombre']} eliminado correctamente.")
        except Exception as e:
            messagebox.showerror(t("error"), t("error_eliminar").format(e))

    # ── Papelera ──────────────────────────────────────────────────────────────
    def _papelera(self):
        c   = self.colors
        win = ctk.CTkToplevel(self.parent)
        win.title(t("papelera"))
        win.geometry("860x480")
        win.configure(fg_color=c['background'])
        win.grab_set()

        # Header
        wh = ctk.CTkFrame(win, fg_color=c['danger'], corner_radius=0, height=50)
        wh.pack(fill="x")
        wh.pack_propagate(False)
        ctk.CTkLabel(
            wh,
            text="  🗑  " + t("papelera_usuarios"),
            font=("Segoe UI", 14, "bold"),
            text_color="white"
        ).pack(side="left", padx=16, pady=12)

        # Tabla
        tabla_frame = ctk.CTkFrame(
            win,
            fg_color=c['card_bg'],
            corner_radius=12,
            border_width=1,
            border_color=COLORS['border']
        )
        tabla_frame.pack(fill="both", expand=True, padx=16, pady=12)

        scroll = ttk.Scrollbar(tabla_frame, orient="vertical",
                            style='Dark.Vertical.TScrollbar')
        scroll.pack(side="right", fill="y")

        tabla = ttk.Treeview(
            tabla_frame,
            columns=("id", "nombre", "rol", "matricula"),
            show="headings",
            height=12,
            yscrollcommand=scroll.set,
            style='Dark.Treeview'
        )
        scroll.configure(command=tabla.yview)

        for col, lbl, w, anc in [
            ("id",        "ID",             60,  "center"),
            ("nombre",    t("nombre"),      300, "w"),
            ("rol",       t("rol"),         120, "center"),
            ("matricula", t("matricula"),   160, "center"),
        ]:
            tabla.heading(col, text=lbl)
            tabla.column(col, width=w, anchor=anc)

        tabla.pack(fill="both", expand=True, padx=4, pady=4)

        # Cargar datos
        def cargar_tabla():
            for i in tabla.get_children():
                tabla.delete(i)
            try:
                conn = get_db()
                rows = sp_get_usuarios_inactivos(conn)
                conn.close()
                for r in rows:
                    nombre = f"{r[1]} {r[2] or ''} {r[3] or ''}".strip()
                    tabla.insert("", "end", values=(r[0], nombre, r[5], r[4] or "—"))
            except Exception as e:
                messagebox.showerror(t("error"), t("no_cargar_papelera").format(e))

        cargar_tabla()

        # Restaurar usuario
        def restaurar():
            sel = tabla.selection()
            if not sel:
                messagebox.showwarning(t("atencion"), t("selecciona_usuario"))
                return

            user_id = tabla.item(sel[0])['values'][0]

            if not messagebox.askyesno(t("confirmar"), t("restaurar_msg")):
                return

            try:
                conn = get_db()
                sp_restaurar_usuario(conn, user_id)
                conn.commit()
                conn.close()
                messagebox.showinfo(t("restaurado"), t("usuario_restaurado"))
                cargar_tabla()
                self.cargar_datos()
            except Exception as e:
                messagebox.showerror(t("error"), t("no_restaurar").format(e))

        # Eliminar definitivamente
        def eliminar_definitivo():
            sel = tabla.selection()
            if not sel:
                messagebox.showwarning(t("atencion"), t("selecciona_usuario"))
                return

            user_id = tabla.item(sel[0])['values'][0]

            if not messagebox.askyesno(t("confirmar"), t("confirmar_eliminar_definitivo")):
                return

            try:
                conn = get_db()
                sp_eliminar_usuario_definitivo(conn, user_id)
                conn.commit()
                conn.close()
                messagebox.showinfo(t("exito"), t("usuario_eliminado_definitivo"))
                cargar_tabla()
                self.cargar_datos()
            except Exception as e:
                messagebox.showerror(t("error"), t("error_eliminar_definitivo").format(e))

        # Vaciar papelera
        def vaciar_papelera():
            if not messagebox.askyesno(t("confirmar"), t("confirmar_vaciar_papelera")):
                return

            try:
                conn = get_db()
                sp_vaciar_papelera(conn)
                conn.commit()
                conn.close()
                messagebox.showinfo(t("exito"), t("papelera_vaciada"))
                cargar_tabla()
                self.cargar_datos()
            except Exception as e:
                messagebox.showerror(t("error"), t("error_vaciar_papelera").format(e))


        # Botones
        btn_frame = ctk.CTkFrame(win, fg_color="transparent")
        btn_frame.pack(fill="x", padx=16, pady=(0, 12))

        ctk.CTkButton(
            btn_frame,
            text="♻️  " + t("restaurar_usuario"),
            fg_color=c['primary'],
            hover_color=COLORS['primary_dark'],
            text_color="#ffffff",
            font=("Segoe UI", 12, "bold"),
            corner_radius=10,
            height=38,
            command=restaurar
        ).pack(side="left")

        ctk.CTkButton(
            btn_frame,
            text="❌ " + t("eliminar"),
            fg_color=c['danger'],
            hover_color="#b71c1c",
            text_color="#ffffff",
            font=("Segoe UI", 12, "bold"),
            corner_radius=10,
            height=38,
            command=eliminar_definitivo
        ).pack(side="right", padx=5)

        ctk.CTkButton(
            btn_frame,
            text="🗑 " + t("vaciar_papelera"),
            fg_color="#6d4c41",
            hover_color="#4e342e",
            text_color="#ffffff",
            font=("Segoe UI", 12, "bold"),
            corner_radius=10,
            height=38,
            command=vaciar_papelera
        ).pack(side="right", padx=5)

