# views/informacion_escolar_view.py
import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk
import sys
import os

from views import nuevo_registro_view

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import COLORS, get_db
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

class InformacionEscolarView:

    def __init__(self, parent):
        self.parent = parent
        self.container = ctk.CTkFrame(parent, fg_color=COLORS['background'])
        self.container.pack(fill="both", expand=True, padx=30, pady=30)

        self.usuario_seleccionado = None
        self.datos = []
        self._placeholder_activo = True

        self.crear_interfaz()
        self.cargar_datos()

    def crear_interfaz(self):
        self._configurar_estilo_tabla()

        # === CABECERA ===
        header_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 20))

        ctk.CTkLabel(
            header_frame,
            text="📚 Información Escolar",
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
        ).pack(side="right")

        self.btn_toggle_detalles = ctk.CTkButton(
            header_frame,
            text="Ocultar detalles",
            fg_color=COLORS['header'],
            hover_color=COLORS['header_hover'],
            text_color=COLORS['white'],
            font=("Segoe UI", 12, "bold"),
            corner_radius=10,
            height=38,
            state="disabled",
            command=self.toggle_detalles
        )
        self.btn_toggle_detalles.pack(side="right", padx=(0, 10))
        
        # Botón papelera 
        ctk.CTkButton(
            header_frame,
            text="🗑 Papelera",
            fg_color=COLORS['content_bg'],
            hover_color=COLORS['border'],
            text_color=COLORS['text_dark'],
            font=("Segoe UI", 12, "bold"),
            corner_radius=10,
            height=38,
            command=self._papelera
        ).pack(side="right", padx=(0,10))

        # === FILTROS ===
        filtros_frame = ctk.CTkFrame(
            self.container,
            fg_color=COLORS['card_bg'],
            corner_radius=14,
            border_width=1,
            border_color=COLORS['border']
        )
        filtros_frame.pack(fill="x", pady=(0, 15))

        ctk.CTkLabel(
            filtros_frame,
            text="Buscar:",
            text_color=COLORS['text_dark'],
            font=("Segoe UI", 12, "bold")
        ).pack(side="left", padx=(14, 5), pady=12)

        self.busqueda_var = tk.StringVar()
        self.entrada_busqueda = ctk.CTkEntry(
            filtros_frame, textvariable=self.busqueda_var,
            font=("Segoe UI", 12), width=260,
            height=36, corner_radius=10,
            fg_color=COLORS['white'], border_color=COLORS['border'],
            text_color=COLORS['text_gray']
        )
        self.entrada_busqueda.pack(side="left", padx=(0, 15), pady=10)
        self.entrada_busqueda.insert(0, "Nombre, matrícula o carrera...")
        self.entrada_busqueda.bind("<FocusIn>",   self.limpiar_placeholder)
        self.entrada_busqueda.bind("<FocusOut>",  self.restaurar_placeholder)
        self.entrada_busqueda.bind("<KeyRelease>", lambda e: self.filtrar_tabla())

        ctk.CTkLabel(
            filtros_frame,
            text="Rol:",
            text_color=COLORS['text_dark'],
            font=("Segoe UI", 12, "bold")
        ).pack(side="left", padx=(0, 5), pady=12)

        self.filtro_rol = ttk.Combobox(
            filtros_frame, values=["Todos", "alumno", "maestro", "personal"],
            state="readonly", width=15, font=("Segoe UI", 11)
        )
        self.filtro_rol.set("Todos")
        self.filtro_rol.pack(side="left", pady=10)
        self.filtro_rol.bind('<<ComboboxSelected>>', lambda e: self.filtrar_tabla())

        # === PANEL DETALLES (bottom) ===
        self.detalles_frame = ctk.CTkFrame(
            self.container,
            fg_color=COLORS['card_bg'],
            corner_radius=14,
            border_width=1,
            border_color=COLORS['border']
        )
        self.detalles_frame.pack(fill="x", pady=(0, 10))
        self.crear_panel_detalles()
        self.detalles_frame.pack_forget()

        # === BOTONES ACCIÓN (bottom, ocultos al inicio) ===
        self.acciones_frame = ctk.CTkFrame(self.container, fg_color="transparent")

        izq = ctk.CTkFrame(self.acciones_frame, fg_color="transparent")
        izq.pack(side="left")

        self.btn_editar = ctk.CTkButton(
            izq, text="✏️ Editar Información",
            fg_color=COLORS['header'], hover_color=COLORS['header_hover'],
            text_color=COLORS['white'],
            font=("Segoe UI", 12, "bold"),
            corner_radius=10,
            height=38,
            command=self.editar_usuario
        )
        self.btn_editar.pack(side="left", padx=(0, 8))

        self.btn_eliminar = ctk.CTkButton(
            izq, text="🗑️ Eliminar Usuario",
            fg_color=COLORS['danger'], hover_color=COLORS['danger_dark'],
            text_color=COLORS['white'],
            font=("Segoe UI", 12, "bold"),
            corner_radius=10,
            height=38,
            command=self.eliminar_usuario
        )
        self.btn_eliminar.pack(side="left")

        # === TABLA (centro, toma espacio restante) ===
        self.tabla_frame = ctk.CTkFrame(
            self.container,
            fg_color=COLORS['card_bg'],
            corner_radius=14,
            border_width=1,
            border_color=COLORS['border']
        )
        self.tabla_frame.pack(fill="both", expand=True, pady=(0, 10))

        scroll_y = ctk.CTkScrollbar(self.tabla_frame)
        scroll_y.pack(side="right", fill="y")
        scroll_x = ctk.CTkScrollbar(self.tabla_frame, orientation="horizontal")
        scroll_x.pack(side="bottom", fill="x")

        self.tabla = ttk.Treeview(
            self.tabla_frame,
            columns=("id", "nombre", "matricula", "rol", "fotos"),
            show="headings", yscrollcommand=scroll_y.set,
            xscrollcommand=scroll_x.set, height=12
        )
        scroll_y.configure(command=self.tabla.yview)
        scroll_x.configure(command=self.tabla.xview)

        headers = [("id",50,"center"),("nombre",250,"w"),("matricula",120,"center"),
                   ("rol",100,"center"),("fotos",80,"center")]
        labels  = {"id":"ID","nombre":"Nombre Completo","matricula":"Matrícula",
                   "rol":"Rol","fotos":"Fotos"}
        for col, w, anchor in headers:
            self.tabla.heading(col, text=labels[col])
            self.tabla.column(col, width=w, anchor=anchor)

        self.tabla.pack(fill="both", expand=True)
        self.tabla.bind('<<TreeviewSelect>>', self.on_select)

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

    # ── Panel detalles ───────────────────────────────────────────────────────

    def crear_panel_detalles(self):
        for w in self.detalles_frame.winfo_children():
            w.destroy()

        ctk.CTkLabel(
            self.detalles_frame,
            text="📋 Detalles del Usuario",
            font=("Segoe UI", 14, "bold"),
            text_color=COLORS['text_dark']
        ).pack(anchor="w", padx=15, pady=(10, 5))

        info_frame = ctk.CTkFrame(self.detalles_frame, fg_color="transparent")
        info_frame.pack(fill="x", padx=15, pady=5)

        if self.usuario_seleccionado:
            self.mostrar_detalles_usuario(info_frame)
        else:
            ctk.CTkLabel(
                info_frame,
                text="Selecciona un usuario para ver sus detalles",
                text_color=COLORS['text_gray'],
                font=("Segoe UI", 12, "italic")
            ).pack(pady=15)
            

    def mostrar_detalles_usuario(self, parent):
        u = self.usuario_seleccionado
        fila = 0
        self._fila(parent, "Nombre:",    u.get('nombre', ''), fila); fila += 1
        self._fila(parent, "Apellido Paterno:", u.get('apellido_paterno', 'N/A'), fila); fila += 1
        self._fila(parent, "Apellido Materno:", u.get('apellido_materno', 'N/A'), fila); fila += 1
        self._fila(parent, "Matrícula:", u.get('matricula', ''), fila); fila += 1
        self._fila(parent, "Rol:",       u.get('rol', ''), fila); fila += 1
        self._fila(parent, "Teléfono:",  u.get('telefono', 'N/A'), fila); fila += 1

        rol = u.get('rol')
        if rol == 'alumno':
            self._fila(parent, "Facultad:", u.get('facultad', 'N/A'), fila); fila += 1
            self._fila(parent, "Carrera:", u.get('carrera', 'N/A'), fila); fila += 1
            self._fila(parent, "Grado:", u.get('grado', '-'), fila); fila += 1
            self._fila(parent, "Grupo:", u.get('grupo', '-'), fila); fila += 1
        elif rol == 'maestro':
            self._fila(parent, "Materia:", u.get('materia', 'N/A'), fila); fila += 1
            self._fila(parent, "Grado que imparte:", u.get('grado', '-'), fila); fila += 1
        elif rol == 'personal':
            self._fila(parent, "Puesto:", u.get('puesto', 'N/A'), fila); fila += 1
            self._fila(parent, "Área:", u.get('area', 'N/A'), fila); fila += 1

        stats = ctk.CTkFrame(parent, fg_color="transparent")
        stats.grid(row=fila, column=0, columnspan=2, pady=(10, 0), sticky="w")
        ctk.CTkLabel(
            stats,
            text=f"📸 Fotos: {u.get('fotos', 0)}",
            text_color=COLORS['primary'],
            font=("Segoe UI", 11, "bold")
        ).pack(side="left", padx=(0, 20))
        ctk.CTkLabel(
            stats,
            text=f"🔐 Accesos: {u.get('accesos', 0)}",
            text_color=COLORS['header'],
            font=("Segoe UI", 11, "bold")
        ).pack(side="left")

    def _fila(self, parent, label, valor, fila):
        ctk.CTkLabel(
            parent,
            text=label,
            text_color=COLORS['text_gray'],
            font=("Segoe UI", 10),
            width=120,
            anchor="w"
        ).grid(row=fila, column=0, sticky="w", pady=2)
        ctk.CTkLabel(
            parent,
            text=valor,
            text_color=COLORS['text_dark'],
            font=("Segoe UI", 10, "bold"),
            anchor="w"
        ).grid(row=fila, column=1, sticky="w", pady=2, padx=(10, 0))

    # ── Carga de datos — usa sp_get_usuarios ─────────────────────────────────

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
                    carrera, grado, grupo = row[7] or 'No especificada', row[8] or '-', row[9] or '-'
                elif rol == 'maestro':
                    carrera, grado, grupo = row[11] or 'No especificada', row[12] or '-', '-'
                else:
                    carrera, grado, grupo = row[13] or '-', '-', '-'

                self.datos.append({
                    'id':       row[0],
                    'nombre':   row[1] or '',
                    'apellido_paterno': row[2] or 'N/A',
                    'apellido_materno': row[3] or 'N/A',
                    'matricula':row[4] or 'N/A',
                    'rol':      rol,
                    'telefono': row[6] or 'N/A',
                    'carrera':  carrera,
                    'grado':    grado,
                    'grupo':    grupo,
                    'materia':  row[11] or 'N/A',
                    'puesto':   row[13] or 'N/A',
                    'area':     row[14] or 'N/A',
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
            nombre_completo = f"{u.get('nombre', '')} {u.get('apellido_paterno', '')} {u.get('apellido_materno', '')}".strip()
            self.tabla.insert("", "end", values=(
                u['id'], nombre_completo, u['matricula'], u['rol'], u['fotos']
            ))

    def filtrar_tabla(self):
        rol_filtro = self.filtro_rol.get()
        texto = "" if self._placeholder_activo else self.busqueda_var.get().lower().strip()

        resultado = [
            u for u in self.datos
            if (rol_filtro == "Todos" or str(u.get('rol', '')).lower() == rol_filtro)
            and (
                not texto
                or texto in str(u.get('nombre', '')).lower()
                or texto in str(u.get('matricula', '')).lower()
                or texto in str(u.get('carrera', '')).lower()
            )
        ]
        self.actualizar_tabla(resultado)

    # ── Placeholder ──────────────────────────────────────────────────────────

    def limpiar_placeholder(self, event):
        if self._placeholder_activo:
            self.entrada_busqueda.delete(0, tk.END)
            self.entrada_busqueda.configure(text_color=COLORS['text_dark'])
            self._placeholder_activo = False

    def restaurar_placeholder(self, event):
        if not self.busqueda_var.get().strip():
            self.entrada_busqueda.insert(0, "Nombre, matrícula o carrera...")
            self.entrada_busqueda.configure(text_color=COLORS['text_gray'])
            self._placeholder_activo = True

    # ── Selección ────────────────────────────────────────────────────────────

    def on_select(self, event):
        seleccion = self.tabla.selection()
        if not seleccion:
            return
        user_id = self.tabla.item(seleccion[0])['values'][0]
        for u in self.datos:
            if u['id'] == user_id:
                self.usuario_seleccionado = u
                break
        self.mostrar_detalles_panel()
        self.crear_panel_detalles()

    def mostrar_detalles_panel(self):
        if not self.detalles_frame.winfo_ismapped():
            self.detalles_frame.pack(fill="x", pady=(0, 10), before=self.tabla_frame)
        if not self.acciones_frame.winfo_ismapped():
            self.acciones_frame.pack(fill="x", pady=(0, 8), before=self.detalles_frame)
        self.btn_toggle_detalles.configure(state="normal", text="Ocultar detalles")
        self.container.update_idletasks()
        self.detalles_frame.lift()

    def ocultar_detalles_panel(self):
        if self.acciones_frame.winfo_ismapped():
            self.acciones_frame.pack_forget()
        if self.detalles_frame.winfo_ismapped():
            self.detalles_frame.pack_forget()
        self.btn_toggle_detalles.configure(text="Mostrar detalles")

    def toggle_detalles(self):
        if self.detalles_frame.winfo_ismapped():
            self.ocultar_detalles_panel()
            return
        if self.usuario_seleccionado:
            self.mostrar_detalles_panel()
            self.crear_panel_detalles()
            return
        messagebox.showinfo("Detalles", "Selecciona un usuario para mostrar detalles")

    # ── Editar — usa sp_actualizar_* ─────────────────────────────────────────

    def editar_usuario(self):
        if not self.usuario_seleccionado:
            messagebox.showwarning("Atención", "Selecciona un usuario primero")
            return

        u       = self.usuario_seleccionado
        partes  = u['nombre'].split()

        win = ctk.CTkToplevel(self.parent)
        win.title("Editar Usuario")
        win.geometry("480x580")
        win.configure(fg_color=COLORS['background'])
        win.grab_set()

        ctk.CTkLabel(
            win,
            text="✏️ Editar Usuario",
            font=("Segoe UI", 18, "bold"),
            text_color=COLORS['text_dark']
        ).pack(pady=(20, 5))
        ctk.CTkLabel(
            win,
            text=f"ID: {u['id']}  |  Rol actual: {u['rol']}",
            font=("Segoe UI", 11),
            text_color=COLORS['text_gray']
        ).pack(pady=(0, 15))

        form = ctk.CTkFrame(win, fg_color="transparent")
        form.pack(padx=30, fill="x")

        # Variables
        vars_ = {
            'nombre':    tk.StringVar(value=partes[0] if partes else ''),
            'paterno':   tk.StringVar(value=partes[1] if len(partes) > 1 else ''),
            'materno':   tk.StringVar(value=partes[2] if len(partes) > 2 else ''),
            'matricula': tk.StringVar(value=u['matricula'] if u['matricula'] != 'N/A' else ''),
            'telefono':  tk.StringVar(value=u['telefono']  if u['telefono']  != 'N/A' else ''),
            'rol':       tk.StringVar(value=u['rol']),
            'carrera':   tk.StringVar(value=u['carrera']   if u['carrera']   != '-'   else ''),
            'grado':     tk.StringVar(value=u['grado']     if u['grado']     != '-'   else ''),
            'grupo':     tk.StringVar(value=u['grupo']     if u['grupo']     != '-'   else ''),
        }

        originales = {k: v.get() for k, v in vars_.items()}

        def campo(parent, label, var, row, state="normal"):
            ctk.CTkLabel(
                parent,
                text=label,
                text_color=COLORS['text_gray'],
                font=("Segoe UI", 10),
                anchor="w"
            ).grid(row=row, column=0, sticky="w", pady=4)
            e = ctk.CTkEntry(
                parent,
                textvariable=var,
                font=("Segoe UI", 11),
                width=260,
                height=34,
                corner_radius=8,
                border_color=COLORS['border']
            )
            if state == "disabled":
                e.configure(state="disabled")
            e.grid(row=row, column=1, sticky="w", padx=(10, 0), pady=4)
            return e

        campo(form, "Nombre:",       vars_['nombre'],    0)
        campo(form, "Apellido P.:",  vars_['paterno'],   1)
        campo(form, "Apellido M.:",  vars_['materno'],   2)
        campo(form, "Matrícula:",    vars_['matricula'], 3)
        campo(form, "Teléfono:",     vars_['telefono'],  4)

        # Rol
        ctk.CTkLabel(
            form,
            text="Rol:",
            text_color=COLORS['text_gray'],
            font=("Segoe UI", 10),
            anchor="w"
        ).grid(row=5, column=0, sticky="w", pady=4)

        combo_rol = ttk.Combobox(
            form,
            textvariable=vars_['rol'],
            values=["alumno","maestro","personal"],
            state="readonly",
            width=26,
            font=("Segoe UI", 11)
        )
        combo_rol.grid(row=5, column=1, sticky="w", padx=(10, 0), pady=4)

        e_carrera = campo(form, "Carrera/Materia:", vars_['carrera'], 6)
        e_grado   = campo(form, "Grado:",           vars_['grado'],   7)
        e_grupo   = campo(form, "Grupo/Área:",      vars_['grupo'],   8)

        def actualizar_campos(*_):
            rol = vars_['rol'].get()
            e_carrera.configure(state="normal" if rol in ("alumno","maestro") else "disabled")
            e_grado.configure(  state="normal" if rol in ("alumno","maestro") else "disabled")
            e_grupo.configure(  state="normal" if rol == "alumno" else "disabled")

        combo_rol.bind("<<ComboboxSelected>>", actualizar_campos)
        actualizar_campos()


        # Botones
        btn_frame = ctk.CTkFrame(win, fg_color="transparent")
        btn_frame.pack(pady=20)

        btn_guardar = ctk.CTkButton(
            btn_frame,
            text="💾 Guardar Cambios",
            fg_color=COLORS['primary'],
            hover_color=COLORS['primary_dark'],
            text_color=COLORS['white'],
            font=("Segoe UI", 12, "bold"),
            corner_radius=10,
            height=38,
            command=lambda: self._guardar_edicion(u['id'], vars_, win)
        )
        btn_guardar.pack(side="left", padx=8)
        btn_guardar.configure(state="disabled")

        ctk.CTkButton(
            btn_frame,
            text="Cancelar",
            fg_color=COLORS['danger'],
            hover_color=COLORS['danger_dark'],
            text_color=COLORS['white'],
            font=("Segoe UI", 12, "bold"),
            corner_radius=10,
            height=38,
            command=win.destroy
        ).pack(side="left")

        ctk.CTkButton(
            btn_frame,
            text="🔁 Volver a tomar fotos",
            fg_color=COLORS['accent'],
            hover_color="#D97706",
            text_color=COLORS['white'],
            font=("Segoe UI", 12, "bold"),
            corner_radius=10,
            height=38,
            command=lambda: self._retomar_fotos(u, win)
        ).pack(side="left", padx=8)

        # 🔧 DETECTOR DE CAMBIOS (esto habilita el botón)
        def detectar_cambios(*args):

            for k, v in vars_.items():
                if v.get() != originales[k]:
                    btn_guardar.configure(state="normal")
                    return

            btn_guardar.configure(state="disabled")

        for v in vars_.values():
            v.trace_add("write", detectar_cambios)



    def _guardar_edicion(self, user_id, vars_, ventana):

        import sqlite3
        from tkinter import messagebox


        nombre     = vars_['nombre'].get().strip()
        paterno    = vars_['paterno'].get().strip()
        materno    = vars_['materno'].get().strip()
        matricula  = vars_['matricula'].get().strip()
        telefono   = vars_['telefono'].get().strip()
        rol        = vars_['rol'].get().strip()
        carrera    = vars_['carrera'].get().strip()
        grado      = vars_['grado'].get().strip()
        grupo      = vars_['grupo'].get().strip()


        if not nombre or not paterno:

            messagebox.showwarning("Campos obligatorios", "Nombre y apellido paterno son obligatorios")
            return


        try:

            conn = sqlite3.connect("database/sistema_biometrico.db")
            cursor = conn.cursor()


            cursor.execute("""

                UPDATE usuarios
                SET
                    nombreUsuario = ?,
                    apellidoPaternoUsuario = ?,
                    apellidoMaternoUsuario = ?,
                    matriculaUsuario = ?,
                    telefonoUsuario = ?,
                    rolUsuario = ?
                WHERE idUsuario = ?

            """, (

                nombre,
                paterno,
                materno,
                matricula,
                telefono,
                rol,
                user_id

            ))


            cursor.execute("DELETE FROM alumnos WHERE fkIdUsuario = ?", (user_id,))
            cursor.execute("DELETE FROM maestros WHERE fkIdUsuario = ?", (user_id,))
            cursor.execute("DELETE FROM personal_escolar WHERE fkIdUsuario = ?", (user_id,))


            if rol == "alumno":

                cursor.execute("""

                    INSERT INTO alumnos
                    (fkIdUsuario, gradoAlumno, grupoAlumno, carreraAlumno)

                    VALUES (?, ?, ?, ?)

                """, (

                    user_id,
                    grado,
                    grupo,
                    carrera

                ))


            elif rol == "maestro":

                cursor.execute("""

                    INSERT INTO maestros
                    (fkIdUsuario, gradoImpartidoMaestro, materiaImpartidaMaestro)

                    VALUES (?, ?, ?)

                """, (

                    user_id,
                    grado,
                    carrera

                ))


            elif rol == "personal":

                cursor.execute("""

                    INSERT INTO personal_escolar
                    (fkIdUsuario, areaPersonalEscolar)

                    VALUES (?, ?)

                """, (

                    user_id,
                    grupo

                ))


            conn.commit()
            conn.close()


            messagebox.showinfo("Éxito", "Usuario actualizado correctamente")

            ventana.destroy()


        except Exception as e:

            messagebox.showerror("Error", f"No se pudo actualizar el usuario:\n{e}")
        
    # ── Método para re-tomar fotos ──
    def _retomar_fotos(self, usuario, ventana_actual):
        try:
            import tkinter as tk
            from tkinter import messagebox
            from views.nuevo_registro_view import NuevoRegistroView

            # Cerrar ventana actual
            ventana_actual.destroy()

            # Limpiar el contenedor principal
            for widget in self.parent.winfo_children():
                widget.destroy()

            # Crear vista de nuevo registro
            nuevo_reg = NuevoRegistroView(self.parent)

            # ── MODO RETOMAR FOTOS ──
            nuevo_reg.modo_retomar_fotos = True
            nuevo_reg.user_id_existente = usuario.get("id")

            # Asignar rol
            nuevo_reg.rol_actual = usuario.get('rol', 'alumno')

            # Mostrar formulario
            nuevo_reg._mostrar_formulario()

            # Mapear campos
            campo_map = {
                'nombreUsuario': 'nombre',
                'apellidoPaternoUsuario': 'paterno',
                'apellidoMaternoUsuario': 'materno',
                'matriculaUsuario': 'matricula',
                'telefonoUsuario': 'telefono',
                'correoUsuario': 'correo',
                'gradoAlumno': 'grado',
                'grupoAlumno': 'grupo',
                'carreraAlumno': 'carrera'
            }

            # Llenar formulario
            for entry_key, user_key in campo_map.items():
                valor = usuario.get(user_key, '')
                if entry_key in nuevo_reg.entries and valor:
                    nuevo_reg.entries[entry_key].delete(0, tk.END)
                    nuevo_reg.entries[entry_key].insert(0, valor)

            # Guardar valores para captura
            nuevo_reg.valores_form = {k: e.get().strip() for k, e in nuevo_reg.entries.items()}

            # Ir directo a captura
            nuevo_reg.parent.after(200, nuevo_reg._mostrar_captura)

        except Exception as e:
            messagebox.showerror("Error", f"No se pudo iniciar la captura: {e}")

    # ── Eliminar — usa sp_eliminar_usuario ────────────────────────────────────

    def eliminar_usuario(self):
        if not self.usuario_seleccionado:
            return
        u = self.usuario_seleccionado
        confirmar = messagebox.askyesno(
            "Confirmar eliminación",
            f"¿Estás seguro de eliminar a:\n\n"
            f"{u['nombre']} ({u['rol']})\n\n"
        )
        if not confirmar:
            return
        try:
            conn = get_db()
            sp_eliminar_usuario(conn, u['id'])
            conn.commit()
            conn.close()

            self.usuario_seleccionado = None
            self.acciones_frame.pack_forget()
            self.crear_panel_detalles()
            self.cargar_datos()
            messagebox.showinfo("✅ Eliminado", f"{u['nombre']} eliminado correctamente.")

        except Exception as e:
            messagebox.showerror("Error", f"No se pudo eliminar: {e}")

    def _papelera(self):
        win = ctk.CTkToplevel(self.parent)
        win.title("Papelera de Usuarios")
        win.geometry("900x500")
        win.configure(fg_color=COLORS['background'])
        win.grab_set()

        ctk.CTkLabel(
            win,
            text="🗑 Usuarios Inactivos",
            font=("Segoe UI", 18, "bold"),
            text_color=COLORS['text_dark']
        ).pack(pady=10)

        tabla = ttk.Treeview(
            win,
            columns=("id","nombre","rol","matricula"),
            show="headings",
            height=15
        )
        tabla.heading("id", text="ID")
        tabla.heading("nombre", text="Nombre")
        tabla.heading("rol", text="Rol")
        tabla.heading("matricula", text="Matrícula")
        tabla.column("id", width=60, anchor="center")
        tabla.column("nombre", width=280)
        tabla.column("rol", width=120, anchor="center")
        tabla.column("matricula", width=150, anchor="center")
        tabla.pack(fill="both", expand=True, padx=15, pady=10)

        # ── Cargar usuarios inactivos (SP) ──
        try:
            conn = get_db()
            rows = sp_get_usuarios_inactivos(conn)
            conn.close()

            for r in rows:
                nombre = f"{r[1]} {r[2] or ''} {r[3] or ''}".strip()
                tabla.insert("", "end", values=(r[0], nombre, r[5], r[4] or "N/A"))

        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar la papelera:\n{e}")
            return

        # ── Restaurar usuario ──
        def restaurar():
            sel = tabla.selection()
            if not sel:
                messagebox.showwarning("Atención", "Selecciona un usuario")
                return

            user_id = tabla.item(sel[0])['values'][0]

            confirmar = messagebox.askyesno(
                "Confirmar restauración",
                "¿Restaurar este usuario?"
            )
            if not confirmar:
                return

            try:
                conn = get_db()
                sp_restaurar_usuario(conn, user_id)
                conn.commit()
                conn.close()

                messagebox.showinfo("Restaurado", "Usuario restaurado correctamente")
                win.destroy()
                self.cargar_datos()

            except Exception as e:
                messagebox.showerror("Error", f"No se pudo restaurar:\n{e}")

        ctk.CTkButton(
            win,
            text="♻️ Restaurar Usuario",
            fg_color=COLORS['primary'],
            hover_color=COLORS['primary_dark'],
            text_color=COLORS['white'],
            font=("Segoe UI", 12, "bold"),
            corner_radius=10,
            height=38,
            command=restaurar
        ).pack(pady=10)