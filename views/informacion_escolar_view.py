# views/informacion_escolar_view.py
import tkinter as tk
from tkinter import ttk, messagebox
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
)

class InformacionEscolarView:

    def __init__(self, parent):
        self.parent = parent
        self.container = tk.Frame(parent, bg=COLORS['white'])
        self.container.pack(fill="both", expand=True, padx=30, pady=30)

        self.usuario_seleccionado = None
        self.datos = []
        self._placeholder_activo = True

        self.crear_interfaz()

    def crear_interfaz(self):
        # === CABECERA ===
        header_frame = tk.Frame(self.container, bg=COLORS['white'])
        header_frame.pack(fill="x", pady=(0, 20))

        tk.Label(header_frame, text="📚 Información Escolar",
                 font=("Arial", 20, "bold"), bg=COLORS['white'],
                 fg=COLORS['text_dark']).pack(side="left")

        tk.Button(header_frame, text="🔄 Actualizar",
                  bg=COLORS['primary'], fg=COLORS['white'],
                  font=("Arial", 10), relief="flat", padx=15, pady=5,
                  command=self.cargar_datos).pack(side="right")

        # === FILTROS ===
        filtros_frame = tk.Frame(self.container, bg=COLORS['white'])
        filtros_frame.pack(fill="x", pady=(0, 15))

        tk.Label(filtros_frame, text="Buscar:", bg=COLORS['white'],
                 fg=COLORS['text_dark'], font=("Arial", 11)).pack(side="left", padx=(0, 5))

        self.busqueda_var = tk.StringVar()
        self.entrada_busqueda = tk.Entry(
            filtros_frame, textvariable=self.busqueda_var,
            font=("Arial", 11), width=30, relief="solid", borderwidth=1,
            fg=COLORS['text_gray']
        )
        self.entrada_busqueda.pack(side="left", padx=(0, 15))
        self.entrada_busqueda.insert(0, "Nombre, matrícula o carrera...")
        self.entrada_busqueda.bind("<FocusIn>",   self.limpiar_placeholder)
        self.entrada_busqueda.bind("<FocusOut>",  self.restaurar_placeholder)
        self.entrada_busqueda.bind("<KeyRelease>", lambda e: self.filtrar_tabla())

        tk.Label(filtros_frame, text="Rol:", bg=COLORS['white'],
                 fg=COLORS['text_dark'], font=("Arial", 11)).pack(side="left", padx=(0, 5))

        self.filtro_rol = ttk.Combobox(
            filtros_frame, values=["Todos", "alumno", "maestro", "personal"],
            state="readonly", width=15, font=("Arial", 11)
        )
        self.filtro_rol.set("Todos")
        self.filtro_rol.pack(side="left")
        self.filtro_rol.bind('<<ComboboxSelected>>', lambda e: self.filtrar_tabla())

        # === PANEL DETALLES (bottom) ===
        self.detalles_frame = tk.Frame(self.container, bg=COLORS['content_bg'],
                                       relief="solid", borderwidth=1)
        self.detalles_frame.pack(fill="x", pady=(10, 0), side="bottom")
        self.crear_panel_detalles()

        # === BOTONES ACCIÓN (bottom, ocultos al inicio) ===
        self.acciones_frame = tk.Frame(self.container, bg=COLORS['white'])

        izq = tk.Frame(self.acciones_frame, bg=COLORS['white'])
        izq.pack(side="left")

        self.btn_editar = tk.Button(
            izq, text="✏️ Editar Información",
            bg=COLORS['header'], fg=COLORS['white'],
            font=("Arial", 11), relief="flat", padx=20, pady=8,
            command=self.editar_usuario
        )
        self.btn_editar.pack(side="left", padx=(0, 8))

        self.btn_eliminar = tk.Button(
            izq, text="🗑️ Eliminar Usuario",
            bg=COLORS['danger'], fg=COLORS['white'],
            font=("Arial", 11), relief="flat", padx=20, pady=8,
            command=self.eliminar_usuario
        )
        self.btn_eliminar.pack(side="left")

        self.btn_papelera = tk.Button(
            self.acciones_frame, text="🗑",
            bg=COLORS['white'], fg=COLORS['text_gray'],
            font=("Arial", 20), relief="flat", padx=8, pady=4,
            cursor="hand2", command=self._papelera
        )
        self.btn_papelera.pack(side="right", padx=5)

        # === TABLA (centro, toma espacio restante) ===
        tabla_frame = tk.Frame(self.container, bg=COLORS['white'])
        tabla_frame.pack(fill="both", expand=True, pady=(0, 10))

        scroll_y = tk.Scrollbar(tabla_frame)
        scroll_y.pack(side="right", fill="y")
        scroll_x = tk.Scrollbar(tabla_frame, orient="horizontal")
        scroll_x.pack(side="bottom", fill="x")

        self.tabla = ttk.Treeview(
            tabla_frame,
            columns=("id", "nombre", "matricula", "rol", "carrera", "grado", "grupo", "fotos"),
            show="headings", yscrollcommand=scroll_y.set,
            xscrollcommand=scroll_x.set, height=12
        )
        scroll_y.config(command=self.tabla.yview)
        scroll_x.config(command=self.tabla.xview)

        headers = [("id",50,"center"),("nombre",250,"w"),("matricula",120,"center"),
                   ("rol",100,"center"),("carrera",200,"w"),("grado",80,"center"),
                   ("grupo",80,"center"),("fotos",80,"center")]
        labels  = {"id":"ID","nombre":"Nombre Completo","matricula":"Matrícula",
                   "rol":"Rol","carrera":"Carrera/Materia","grado":"Grado",
                   "grupo":"Grupo","fotos":"Fotos"}
        for col, w, anchor in headers:
            self.tabla.heading(col, text=labels[col])
            self.tabla.column(col, width=w, anchor=anchor)

        self.tabla.pack(fill="both", expand=True)
        self.tabla.bind('<<TreeviewSelect>>', self.on_select)

    # ── Panel detalles ───────────────────────────────────────────────────────

    def crear_panel_detalles(self):
        for w in self.detalles_frame.winfo_children():
            w.destroy()

        tk.Label(self.detalles_frame, text="📋 Detalles del Usuario",
                 font=("Arial", 12, "bold"), bg=COLORS['content_bg'],
                 fg=COLORS['text_dark']).pack(anchor="w", padx=15, pady=(10, 5))

        info_frame = tk.Frame(self.detalles_frame, bg=COLORS['content_bg'])
        info_frame.pack(fill="x", padx=15, pady=5)

        if self.usuario_seleccionado:
            self.mostrar_detalles_usuario(info_frame)
        else:
            tk.Label(info_frame, text="Selecciona un usuario para ver sus detalles",
                     bg=COLORS['content_bg'], fg=COLORS['text_gray'],
                     font=("Arial", 11, "italic")).pack(pady=15)

    def mostrar_detalles_usuario(self, parent):
        u = self.usuario_seleccionado
        self._fila(parent, "Nombre:",    u.get('nombre', ''),      0)
        self._fila(parent, "Matrícula:", u.get('matricula', ''),   1)
        self._fila(parent, "Rol:",       u.get('rol', ''),         2)
        self._fila(parent, "Teléfono:",  u.get('telefono', 'N/A'), 3)

        if u.get('rol') == 'alumno':
            self._fila(parent, "Carrera:",     u.get('carrera', 'N/A'),  4)
            self._fila(parent, "Grado/Grupo:", f"{u.get('grado','')}° {u.get('grupo','')}", 5)
            self._fila(parent, "Facultad:",    u.get('facultad', 'N/A'), 6)

        stats = tk.Frame(parent, bg=COLORS['content_bg'])
        stats.grid(row=7, column=0, columnspan=2, pady=(10, 0), sticky="w")
        tk.Label(stats, text=f"📸 Fotos: {u.get('fotos', 0)}",
                 bg=COLORS['content_bg'], fg=COLORS['primary'],
                 font=("Arial", 10, "bold")).pack(side="left", padx=(0, 20))
        tk.Label(stats, text=f"🔐 Accesos: {u.get('accesos', 0)}",
                 bg=COLORS['content_bg'], fg=COLORS['header'],
                 font=("Arial", 10, "bold")).pack(side="left")

    def _fila(self, parent, label, valor, fila):
        tk.Label(parent, text=label, bg=COLORS['content_bg'], fg=COLORS['text_gray'],
                 font=("Arial", 10), width=15, anchor="w"
                 ).grid(row=fila, column=0, sticky="w", pady=2)
        tk.Label(parent, text=valor, bg=COLORS['content_bg'], fg=COLORS['text_dark'],
                 font=("Arial", 10, "bold"), anchor="w"
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
        if self._placeholder_activo:
            self.actualizar_tabla(); return
        texto      = self.busqueda_var.get().lower().strip()
        rol_filtro = self.filtro_rol.get()
        resultado  = [
            u for u in self.datos
            if (rol_filtro == "Todos" or u['rol'] == rol_filtro)
            and (not texto or texto in u['nombre'].lower()
                 or texto in u['matricula'].lower()
                 or texto in u['carrera'].lower())
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
        if not self.acciones_frame.winfo_ismapped():
            self.acciones_frame.pack(fill="x", pady=(0, 8), side="bottom",
                                     before=self.detalles_frame)
        self.crear_panel_detalles()

    # ── Editar — usa sp_actualizar_* ─────────────────────────────────────────

    def editar_usuario(self):
        if not self.usuario_seleccionado:
            messagebox.showwarning("Atención", "Selecciona un usuario primero")
            return

        u       = self.usuario_seleccionado
        partes  = u['nombre'].split()

        win = tk.Toplevel(self.parent)
        win.title("Editar Usuario")
        win.geometry("480x580")
        win.configure(bg=COLORS['white'])
        win.grab_set()

        tk.Label(win, text="✏️ Editar Usuario", font=("Arial", 16, "bold"),
                 bg=COLORS['white'], fg=COLORS['text_dark']).pack(pady=(20, 5))
        tk.Label(win, text=f"ID: {u['id']}  |  Rol actual: {u['rol']}",
                 font=("Arial", 10), bg=COLORS['white'],
                 fg=COLORS['text_gray']).pack(pady=(0, 15))

        form = tk.Frame(win, bg=COLORS['white'])
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
            tk.Label(parent, text=label, bg=COLORS['white'], fg=COLORS['text_gray'],
                     font=("Arial", 10), anchor="w").grid(row=row, column=0, sticky="w", pady=4)
            e = tk.Entry(parent, textvariable=var, font=("Arial", 11),
                         relief="solid", borderwidth=1, width=28, state=state)
            e.grid(row=row, column=1, sticky="w", padx=(10, 0), pady=4)
            return e

        campo(form, "Nombre:",       vars_['nombre'],    0)
        campo(form, "Apellido P.:",  vars_['paterno'],   1)
        campo(form, "Apellido M.:",  vars_['materno'],   2)
        campo(form, "Matrícula:",    vars_['matricula'], 3)
        campo(form, "Teléfono:",     vars_['telefono'],  4)

        # Rol
        tk.Label(form, text="Rol:", bg=COLORS['white'], fg=COLORS['text_gray'],
                 font=("Arial", 10), anchor="w").grid(row=5, column=0, sticky="w", pady=4)

        combo_rol = ttk.Combobox(
            form,
            textvariable=vars_['rol'],
            values=["alumno","maestro","personal"],
            state="readonly",
            width=26,
            font=("Arial", 11)
        )
        combo_rol.grid(row=5, column=1, sticky="w", padx=(10, 0), pady=4)

        e_carrera = campo(form, "Carrera/Materia:", vars_['carrera'], 6)
        e_grado   = campo(form, "Grado:",           vars_['grado'],   7)
        e_grupo   = campo(form, "Grupo/Área:",      vars_['grupo'],   8)

        def actualizar_campos(*_):
            rol = vars_['rol'].get()
            e_carrera.config(state="normal" if rol in ("alumno","maestro") else "disabled")
            e_grado.config(  state="normal" if rol in ("alumno","maestro") else "disabled")
            e_grupo.config(  state="normal" if rol == "alumno" else "disabled")

        combo_rol.bind("<<ComboboxSelected>>", actualizar_campos)
        actualizar_campos()


        # Botones
        btn_frame = tk.Frame(win, bg=COLORS['white'])
        btn_frame.pack(pady=20)

        btn_guardar = tk.Button(
            btn_frame,
            text="💾 Guardar Cambios",
            bg=COLORS['primary'],
            fg=COLORS['white'],
            font=("Arial", 11),
            relief="flat",
            padx=20,
            pady=8,
            command=lambda: self._guardar_edicion(u['id'], vars_, win)
        )
        btn_guardar.pack(side="left", padx=8)
        btn_guardar.config(state="disabled")

        tk.Button(
            btn_frame,
            text="Cancelar",
            bg=COLORS['danger'],
            fg=COLORS['white'],
            font=("Arial", 11),
            relief="flat",
            padx=20,
            pady=8,
            command=win.destroy
        ).pack(side="left")

        tk.Button(
            btn_frame,
            text="🔁 Volver a tomar fotos",
            bg="#E67E22",
            fg=COLORS['white'],
            font=("Arial", 11),
            relief="flat",
            padx=20,
            pady=8,
            command=lambda: self._retomar_fotos(u, win)
        ).pack(side="left", padx=8)

        # 🔧 DETECTOR DE CAMBIOS (esto habilita el botón)
        def detectar_cambios(*args):

            for k, v in vars_.items():
                if v.get() != originales[k]:
                    btn_guardar.config(state="normal")
                    return

            btn_guardar.config(state="disabled")

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
            f"Se borrarán también sus fotos y registros de acceso.\n"
            f"Esta acción no se puede deshacer."
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
        pass  # Sin funcionalidad aún