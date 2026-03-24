# views/informacion_escolar_view.py
import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk
import sys
import os
from views.font_scale import FontScale
from views import nuevo_registro_view

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
    sp_restaurar_usuario
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

        ctk.CTkLabel(left, text="📚  Información Escolar",
                     font=("Segoe UI", 24, "bold"),
                     text_color=c['text_dark']).pack(anchor="w")
        ctk.CTkLabel(left, text="Gestión de usuarios registrados en el sistema",
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

        self.btn_toggle_detalles = ctk.CTkButton(btn_row, text="Ver detalles",
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

        ctk.CTkLabel(filtros, text="🔍  Buscar:",
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
        self.entrada_busqueda.insert(0, "Nombre, matrícula o carrera...")
        self.entrada_busqueda.bind("<FocusIn>",    self.limpiar_placeholder)
        self.entrada_busqueda.bind("<FocusOut>",   self.restaurar_placeholder)
        self.entrada_busqueda.bind("<KeyRelease>", lambda e: self.filtrar_tabla())

        ctk.CTkLabel(filtros, text="Rol:",
                     text_color=c['text_dark'],
                     font=("Segoe UI", 12, "bold")).pack(side="left", padx=(0, 6), pady=10)

        self.filtro_rol = ttk.Combobox(filtros,
            values=["Todos", "alumno", "maestro", "personal"],
            state="readonly", width=16,
            font=("Segoe UI", 12),
            style='Dark.TCombobox')
        self.filtro_rol.set("Todos")
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

        self.btn_editar = ctk.CTkButton(self.acciones_frame, text="✏️  Editar",
                      fg_color=c['header'], hover_color=COLORS['header_hover'],
                      text_color="#ffffff",
                      font=("Segoe UI", 12, "bold"),
                      corner_radius=10, height=36,
                      command=self.editar_usuario)
        self.btn_editar.pack(side="left", padx=(0, 8))

        self.btn_eliminar = ctk.CTkButton(self.acciones_frame, text="🗑️  Eliminar",
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
        ctk.CTkLabel(th, text="Usuarios registrados",
                     font=FontScale.fb(13),
                     text_color=c['text_dark']).pack(side="left")

        scroll_y = ttk.Scrollbar(self.tabla_frame, orient="vertical",
                                  style='Dark.Vertical.TScrollbar')
        scroll_y.pack(side="right", fill="y", padx=(0, 4))

        scroll_x = ttk.Scrollbar(self.tabla_frame, orient="horizontal",
                                  style='Dark.Horizontal.TScrollbar')
        scroll_x.pack(side="bottom", fill="x", pady=(0, 4))

        self.tabla = ttk.Treeview(self.tabla_frame,
            columns=("id", "nombre", "matricula", "rol", "fotos"),
            show="headings",
            yscrollcommand=scroll_y.set,
            xscrollcommand=scroll_x.set,
            height=14,
            style='Dark.Treeview')
        scroll_y.configure(command=self.tabla.yview)
        scroll_x.configure(command=self.tabla.xview)

        for col, label, w, anchor in [
            ("id",        "ID",              55,  "center"),
            ("nombre",    "Nombre Completo", 260, "w"),
            ("matricula", "Matrícula",       130, "center"),
            ("rol",       "Rol",             110, "center"),
            ("fotos",     "📸 Fotos",          80,  "center"),
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
        col1 = [("Nombre", u.get('nombre','—')),
                ("Apellido Paterno", u.get('apellido_paterno','—')),
                ("Apellido Materno", u.get('apellido_materno','—'))]
        col2 = [("Matrícula", u.get('matricula','—')),
                ("Teléfono", u.get('telefono','—')),
                ("Rol", rol.capitalize())]
        col3 = []
        if rol == 'alumno':
            col3 = [("Facultad", u.get('facultad','—')), ("Carrera", u.get('carrera','—')),
                    ("Grado", u.get('grado','—')), ("Grupo", u.get('grupo','—'))]
        elif rol == 'maestro':
            col3 = [("Materia", u.get('materia','—')), ("Grado que imparte", u.get('grado','—'))]
        elif rol == 'personal':
            col3 = [("Puesto", u.get('puesto','—')), ("Área", u.get('area','—'))]
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
        self.filtro_rol.set("Todos")
        self.busqueda_var.set("")
        self.entrada_busqueda.delete(0, tk.END)
        self.entrada_busqueda.insert(0, "Nombre, matrícula o carrera...")
        self.entrada_busqueda.configure(text_color=self.colors['text_gray'])
        self._placeholder_activo = True
        self.cargar_datos()

    def cargar_datos(self):
        try:
            conn = get_db()
            if not conn:
                messagebox.showerror("Error", "No se pudo conectar a la base de datos")
                return
            resultados = sp_get_usuarios(conn)
            conn.close()

            self.datos = []
            for row in resultados:
                rol = row[5]
                if rol == 'alumno':
                    carrera, grado, grupo = row[7] or '—', row[8] or '—', row[9] or '—'
                elif rol == 'maestro':
                    carrera, grado, grupo = row[11] or '—', row[12] or '—', '—'
                else:
                    carrera, grado, grupo = row[13] or '—', '—', '—'

                self.datos.append({
                    'id':              row[0],
                    'nombre':          row[1] or '',
                    'apellido_paterno':row[2] or '—',
                    'apellido_materno':row[3] or '—',
                    'matricula':       row[4] or '—',
                    'rol':             rol,
                    'telefono':        row[6] or '—',
                    'carrera':         carrera,
                    'grado':           grado,
                    'grupo':           grupo,
                    'materia':         row[11] or '—',
                    'puesto':          row[13] or '—',
                    'area':            row[14] or '—',
                    'facultad':        row[10] if rol == 'alumno' else '—',
                    'fotos':           row[15] or 0,
                    'accesos':         row[16] or 0,
                })
            self.actualizar_tabla()
        except Exception as e:
            messagebox.showerror("Error", f"Error al cargar datos: {e}")
            self.datos = []

    def actualizar_tabla(self, datos_filtrados=None):
        for item in self.tabla.get_children():
            self.tabla.delete(item)

        lista = datos_filtrados if datos_filtrados is not None else self.datos
        for u in lista:
            nombre_completo = f"{u.get('nombre','')} {u.get('apellido_paterno','')} {u.get('apellido_materno','')}".strip()
            self.tabla.insert("", "end", values=(
                u['id'], nombre_completo, u['matricula'], u['rol'], u['fotos']
            ), tags=(u.get('rol',''),))

        total = len(lista)
        self.lbl_conteo.configure(text=f"{total} usuario{'s' if total != 1 else ''}")

    def filtrar_tabla(self):
        rol_filtro = self.filtro_rol.get()
        texto = "" if self._placeholder_activo else self.busqueda_var.get().lower().strip()

        resultado = [
            u for u in self.datos
            if (rol_filtro == "Todos" or str(u.get('rol','')).lower() == rol_filtro)
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
            self.entrada_busqueda.insert(0, "Nombre, matrícula o carrera...")
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
        self.btn_toggle_detalles.configure(state="normal", text="Ocultar detalles")
        self.container.update_idletasks()

    def ocultar_detalles_panel(self):
        if self.acciones_frame.winfo_ismapped():
            self.acciones_frame.pack_forget()
        if self.detalles_frame.winfo_ismapped():
            self.detalles_frame.pack_forget()
        self.btn_toggle_detalles.configure(text="Ver detalles")

    def toggle_detalles(self):
        if self.detalles_frame.winfo_ismapped():
            self.ocultar_detalles_panel()
        elif self.usuario_seleccionado:
            self.mostrar_detalles_panel()
            self.crear_panel_detalles()
        else:
            messagebox.showinfo("Detalles", "Selecciona un usuario para mostrar detalles")

    # ── Editar ────────────────────────────────────────────────────────────────
    def editar_usuario(self):
        if not self.usuario_seleccionado:
            messagebox.showwarning("Atención", "Selecciona un usuario primero")
            return

        c      = self.colors
        u      = self.usuario_seleccionado
        partes = u['nombre'].split()
        color  = ROL_COLOR.get(u.get('rol', ''), COLORS['primary'])

        win = ctk.CTkToplevel(self.parent)
        win.title("Editar Usuario")
        win.geometry("500x600")
        win.configure(fg_color=c['background'])
        win.grab_set()

        wh = ctk.CTkFrame(win, fg_color=color, corner_radius=0, height=54)
        wh.pack(fill="x")
        wh.pack_propagate(False)
        ctk.CTkLabel(wh, text=f"  ✏️  Editar  —  {u['nombre']} ({u['rol']})",
                     font=FontScale.fb(13), text_color="white").pack(side="left", padx=16, pady=14)

        form = ctk.CTkFrame(win, fg_color="transparent")
        form.pack(padx=28, fill="x", pady=16)

        vars_ = {
            'nombre':    tk.StringVar(value=partes[0] if partes else ''),
            'paterno':   tk.StringVar(value=partes[1] if len(partes) > 1 else ''),
            'materno':   tk.StringVar(value=partes[2] if len(partes) > 2 else ''),
            'matricula': tk.StringVar(value=u['matricula'] if u['matricula'] != '—' else ''),
            'telefono':  tk.StringVar(value=u['telefono']  if u['telefono']  != '—' else ''),
            'rol':       tk.StringVar(value=u['rol']),
            'carrera':   tk.StringVar(value=u['carrera']   if u['carrera']   != '—' else ''),
            'grado':     tk.StringVar(value=u['grado']     if u['grado']     != '—' else ''),
            'grupo':     tk.StringVar(value=u['grupo']     if u['grupo']     != '—' else ''),
        }
        originales = {k: v.get() for k, v in vars_.items()}

        def campo(lbl, var, row, state="normal"):
            ctk.CTkLabel(form, text=lbl, text_color=c['text_gray'],
                         font=("Segoe UI", 10), anchor="w"
                         ).grid(row=row, column=0, sticky="w", pady=4)
            e = ctk.CTkEntry(form, textvariable=var, font=("Segoe UI", 11),
                             width=270, height=34, corner_radius=8,
                             border_color=COLORS['border'],
                             fg_color=c['content_bg'],
                             text_color=c['text_dark'])
            if state == "disabled":
                e.configure(state="disabled")
            e.grid(row=row, column=1, sticky="w", padx=(10, 0), pady=4)
            return e

        campo("Nombre:",      vars_['nombre'],    0)
        campo("Apellido P.:", vars_['paterno'],   1)
        campo("Apellido M.:", vars_['materno'],   2)
        campo("Matrícula:",   vars_['matricula'], 3)
        campo("Teléfono:",    vars_['telefono'],  4)

        ctk.CTkLabel(form, text="Rol:", text_color=c['text_gray'],
                     font=("Segoe UI", 10), anchor="w"
                     ).grid(row=5, column=0, sticky="w", pady=4)
        combo_rol = ttk.Combobox(form, textvariable=vars_['rol'],
                                 values=["alumno", "maestro", "personal"],
                                 state="readonly", width=28, font=("Segoe UI", 11),
                                 style='Dark.TCombobox')
        combo_rol.grid(row=5, column=1, sticky="w", padx=(10, 0), pady=4)

        e_carrera = campo("Carrera/Materia:", vars_['carrera'], 6)
        e_grado   = campo("Grado:",           vars_['grado'],   7)
        e_grupo   = campo("Grupo/Área:",      vars_['grupo'],   8)

        def actualizar_campos(*_):
            rol = vars_['rol'].get()
            e_carrera.configure(state="normal" if rol in ("alumno","maestro") else "disabled")
            e_grado.configure(  state="normal" if rol in ("alumno","maestro") else "disabled")
            e_grupo.configure(  state="normal" if rol == "alumno" else "disabled")

        combo_rol.bind("<<ComboboxSelected>>", actualizar_campos)
        actualizar_campos()

        btn_row = ctk.CTkFrame(win, fg_color="transparent")
        btn_row.pack(pady=12)

        btn_guardar = ctk.CTkButton(btn_row, text="💾  Guardar",
                      fg_color=c['primary'], hover_color=COLORS['primary_dark'],
                      text_color="#ffffff", font=("Segoe UI", 12, "bold"),
                      corner_radius=10, height=38, state="disabled",
                      command=lambda: self._guardar_edicion(u['id'], vars_, win))
        btn_guardar.pack(side="left", padx=6)

        ctk.CTkButton(btn_row, text="🔁  Retomar fotos",
                      fg_color=c['accent'], hover_color="#D97706",
                      text_color="#ffffff", font=("Segoe UI", 12, "bold"),
                      corner_radius=10, height=38,
                      command=lambda: self._retomar_fotos(u, win)).pack(side="left", padx=6)

        ctk.CTkButton(btn_row, text="Cancelar",
                      fg_color=c['content_bg'], hover_color=COLORS['border'],
                      text_color=c['text_dark'], font=("Segoe UI", 12, "bold"),
                      corner_radius=10, height=38,
                      command=win.destroy).pack(side="left", padx=6)

        def detectar_cambios(*_):
            changed = any(v.get() != originales[k] for k, v in vars_.items())
            btn_guardar.configure(state="normal" if changed else "disabled")

        for v in vars_.values():
            v.trace_add("write", detectar_cambios)

    def _guardar_edicion(self, user_id, vars_, ventana):
        import sqlite3 as _sqlite3

        nombre    = vars_['nombre'].get().strip()
        paterno   = vars_['paterno'].get().strip()
        materno   = vars_['materno'].get().strip()
        matricula = vars_['matricula'].get().strip()
        telefono  = vars_['telefono'].get().strip()
        rol       = vars_['rol'].get().strip()
        carrera   = vars_['carrera'].get().strip()
        grado     = vars_['grado'].get().strip()
        grupo     = vars_['grupo'].get().strip()

        if not nombre or not paterno:
            messagebox.showwarning("Campos obligatorios", "Nombre y apellido paterno son obligatorios")
            return

        try:
            conn   = get_db()
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE usuarios SET
                    nombreUsuario = ?,
                    apellidoPaternoUsuario = ?,
                    apellidoMaternoUsuario = ?,
                    matriculaUsuario = ?,
                    telefonoUsuario = ?,
                    rolUsuario = ?
                WHERE idUsuario = ?
            """, (nombre, paterno, materno, matricula, telefono, rol, user_id))

            cursor.execute("DELETE FROM alumnos          WHERE fkIdUsuario = ?", (user_id,))
            cursor.execute("DELETE FROM maestros         WHERE fkIdUsuario = ?", (user_id,))
            cursor.execute("DELETE FROM personal_escolar WHERE fkIdUsuario = ?", (user_id,))

            if rol == "alumno":
                cursor.execute("""
                    INSERT INTO alumnos (fkIdUsuario, gradoAlumno, grupoAlumno, carreraAlumno)
                    VALUES (?, ?, ?, ?)
                """, (user_id, grado, grupo, carrera))
            elif rol == "maestro":
                cursor.execute("""
                    INSERT INTO maestros (fkIdUsuario, gradoImpartidoMaestro, materiaImpartidaMaestro)
                    VALUES (?, ?, ?)
                """, (user_id, grado, carrera))
            elif rol == "personal":
                cursor.execute("""
                    INSERT INTO personal_escolar (fkIdUsuario, areaPersonalEscolar)
                    VALUES (?, ?)
                """, (user_id, grupo))

            conn.commit()
            conn.close()
            messagebox.showinfo("✅ Actualizado", "Usuario actualizado correctamente.")
            ventana.destroy()
            self.cargar_datos()

        except Exception as e:
            messagebox.showerror("Error", f"No se pudo actualizar:\n{e}")

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
            messagebox.showerror("Error", f"No se pudo iniciar la captura: {e}")

    # ── Eliminar ──────────────────────────────────────────────────────────────
    def eliminar_usuario(self):
        if not self.usuario_seleccionado:
            return
        u = self.usuario_seleccionado
        if not messagebox.askyesno("Confirmar eliminación",
                f"¿Eliminar a {u['nombre']} {u.get('apellido_paterno','')} ({u['rol']})?"):
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
            messagebox.showerror("Error", f"No se pudo eliminar: {e}")

    # ── Papelera ──────────────────────────────────────────────────────────────
    def _papelera(self):
        c   = self.colors
        win = ctk.CTkToplevel(self.parent)
        win.title("Papelera de Usuarios")
        win.geometry("860x480")
        win.configure(fg_color=c['background'])
        win.grab_set()

        wh = ctk.CTkFrame(win, fg_color=c['danger'], corner_radius=0, height=50)
        wh.pack(fill="x")
        wh.pack_propagate(False)
        ctk.CTkLabel(wh, text="  🗑  Papelera — Usuarios Inactivos",
                     font=("Segoe UI", 14, "bold"), text_color="white").pack(side="left", padx=16, pady=12)

        tabla_frame = ctk.CTkFrame(win, fg_color=c['card_bg'],
                                    corner_radius=12, border_width=1,
                                    border_color=COLORS['border'])
        tabla_frame.pack(fill="both", expand=True, padx=16, pady=12)

        scroll = ttk.Scrollbar(tabla_frame, orient="vertical",
                                style='Dark.Vertical.TScrollbar')
        scroll.pack(side="right", fill="y")

        tabla = ttk.Treeview(tabla_frame,
            columns=("id", "nombre", "rol", "matricula"),
            show="headings", height=12,
            yscrollcommand=scroll.set,
            style='Dark.Treeview')
        scroll.configure(command=tabla.yview)

        for col, lbl, w, anc in [
            ("id",        "ID",        60,  "center"),
            ("nombre",    "Nombre",    300, "w"),
            ("rol",       "Rol",       120, "center"),
            ("matricula", "Matrícula", 160, "center"),
        ]:
            tabla.heading(col, text=lbl)
            tabla.column(col, width=w, anchor=anc)

        tabla.pack(fill="both", expand=True, padx=4, pady=4)

        try:
            conn = get_db()
            rows = sp_get_usuarios_inactivos(conn)
            conn.close()
            for r in rows:
                nombre = f"{r[1]} {r[2] or ''} {r[3] or ''}".strip()
                tabla.insert("", "end", values=(r[0], nombre, r[5], r[4] or "—"))
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar la papelera:\n{e}")
            return

        def restaurar():
            sel = tabla.selection()
            if not sel:
                messagebox.showwarning("Atención", "Selecciona un usuario"); return
            user_id = tabla.item(sel[0])['values'][0]
            if not messagebox.askyesno("Confirmar", "¿Restaurar este usuario?"):
                return
            try:
                conn = get_db()
                sp_restaurar_usuario(conn, user_id)
                conn.commit()
                conn.close()
                messagebox.showinfo("✅ Restaurado", "Usuario restaurado correctamente.")
                win.destroy()
                self.cargar_datos()
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo restaurar:\n{e}")

        ctk.CTkButton(win, text="♻️  Restaurar Usuario",
                      fg_color=c['primary'], hover_color=COLORS['primary_dark'],
                      text_color="#ffffff", font=("Segoe UI", 12, "bold"),
                      corner_radius=10, height=38,
                      command=restaurar).pack(pady=(0, 12))