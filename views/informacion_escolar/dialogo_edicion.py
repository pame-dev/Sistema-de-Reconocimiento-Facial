# views/informacion_escolar/dialogo_edicion.py
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import customtkinter as ctk
from tkcalendar import DateEntry

from config import COLORS, get_db
from idiomas import t
from views.informacion_escolar.estilos import ROL_COLOR, ROL_ICONO


class DialogoEdicionMixin:
    """
    Ventana emergente para editar un usuario y retomar fotos biométricas.
    Requiere: self.colors, self.parent, self.usuario_seleccionado,
    self.cargar_datos(), self._is_alive().
    """

    def editar_usuario(self):
        if not self.usuario_seleccionado:
            messagebox.showwarning(t("atencion"), t("selecciona_usuario"))
            return

        c = self.colors
        u = self.usuario_seleccionado
        color = ROL_COLOR.get(u.get('rol', ''), COLORS['primary'])

        def _val(key):
            v = u.get(key, '')
            return '' if v in ('—', None) else str(v)

        vars_ = {
            'nombre':           tk.StringVar(value=_val('nombre')),
            'paterno':          tk.StringVar(value=_val('apellido_paterno')),
            'materno':          tk.StringVar(value=_val('apellido_materno')),
            'matricula':        tk.StringVar(value=_val('matricula')),
            'telefono':         tk.StringVar(value=_val('telefono')),
            'fecha_nacimiento': tk.StringVar(value=_val('fecha_nacimiento')),
            'tipo_sangre':      tk.StringVar(value=_val('tipo_sangre')),
            'rol':              tk.StringVar(value=u['rol']),
            'facultad':         tk.StringVar(value=_val('facultad')),
            'carrera':          tk.StringVar(value=_val('carrera')),
            'grado':            tk.StringVar(value=_val('grado')),
            'grupo':            tk.StringVar(value=_val('grupo')),
            'materia':          tk.StringVar(value=_val('materia')),
            'puesto':           tk.StringVar(value=_val('puesto')),
            'area':             tk.StringVar(value=_val('area')),
        }
        originales = {k: v.get() for k, v in vars_.items()}

        win = ctk.CTkToplevel(self.parent)
        win.configure(fg_color=c['background'])
        win.update_idletasks()
        win.wait_visibility()
        win.grab_set()
        win.overrideredirect(True)

        root = self.parent.winfo_toplevel()
        root.update_idletasks()

        width, height = 390, 320
        win.geometry(f"{width}x{height}+{root.winfo_rootx()}+{root.winfo_rooty()}")
        win.minsize(width, 400)
        win.maxsize(width, 800)

        # Header
        header = ctk.CTkFrame(win, fg_color=color, height=42)
        header.pack(fill="x")
        ctk.CTkLabel(header,
                     text=f"{ROL_ICONO.get(u['rol'], '👤')} Editar",
                     text_color="white",
                     font=("Segoe UI", 11, "bold")).pack(side="left", padx=10)
        ctk.CTkButton(header, text="✕", width=26, height=24,
                      fg_color="transparent", text_color="white",
                      command=win.destroy).pack(side="right", padx=6)

        main_frame = ctk.CTkFrame(win, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=12, pady=(10, 2))

        btns = ctk.CTkFrame(win, fg_color="transparent")
        btns.pack(fill="x", padx=6, pady=4, side="bottom")

        icon_map = {
            'nombre': '👤', 'paterno': '👨', 'materno': '👩',
            'matricula': '🎓', 'telefono': '☎️', 'fecha_nacimiento': '📅',
            'tipo_sangre': '🩸', 'rol': '👥', 'facultad': '🏫',
            'carrera': '📚', 'grado': '📊', 'grupo': '👥',
            'materia': '📖', 'puesto': '💼', 'area': '🗺️'
        }

        def make_entry(parent, label, var, key=None):
            row = ctk.CTkFrame(parent, fg_color="transparent")
            row.pack(fill="x", padx=8, pady=1)
            icon_text = (icon_map.get(key, '') + " ") if key in icon_map else ""
            ctk.CTkLabel(row, text=icon_text + label, width=95, anchor="w",
                         font=("Segoe UI", 9),
                         text_color=c['text_gray']).pack(side="left")
            if key == "fecha_nacimiento":
                e = DateEntry(row, date_pattern='dd-mm-yyyy', textvariable=var, width=9)
            elif key == "tipo_sangre":
                e = ttk.Combobox(row,
                                 values=["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"],
                                 state="readonly", textvariable=var, width=4)
            else:
                e = ctk.CTkEntry(row, textvariable=var, height=24, font=("Segoe UI", 9))
            e.pack(side="left", fill="x", expand=True)


        # Campos comunes
        make_entry(main_frame, t("nombre"),          vars_['nombre'], 'nombre')
        make_entry(main_frame, t("apellido_paterno"), vars_['paterno'], 'paterno')
        make_entry(main_frame, t("apellido_materno"),     vars_['materno'], 'materno')
        make_entry(main_frame, t("matricula"),            vars_['matricula'], 'matricula')
        make_entry(main_frame, t("telefono"),             vars_['telefono'], 'telefono')
        make_entry(main_frame, t("fecha_nacimiento"),     vars_['fecha_nacimiento'], "fecha_nacimiento")
        make_entry(main_frame, t("tipo_sangre"),          vars_['tipo_sangre'],      "tipo_sangre")

        roles_usuario = u.get('rol', '').split(",") if u.get('rol') else []       
        rol_principal = roles_usuario[0] if roles_usuario else "alumno"
        vars_['rol'].set(rol_principal)
        available_roles = ["alumno", "maestro", "personal"]
        roles_extras_vars = {
            role: tk.BooleanVar(value=False)
            for role in available_roles
        }
        for r in roles_usuario[1:]:
            if r in roles_extras_vars:
                roles_extras_vars[r].set(True)


        # Selector de rol principal
        rol_row = ctk.CTkFrame(main_frame, fg_color="transparent")
        rol_row.pack(fill="x", padx=8, pady=4)
        ctk.CTkLabel(rol_row, text="👥 " + t("rol"), width=95, anchor="w",
                     font=("Segoe UI", 9),
                     text_color=c['text_gray']).pack(side="left")
        combo_rol = ttk.Combobox(rol_row, textvariable=vars_['rol'],
                                 values=["alumno", "maestro", "personal"],
                                 state="readonly", width=10)
        combo_rol.pack(side="left")

        def on_principal_selected(event):
            selected = vars_['rol'].get()
            abrir_modal_campos_rol(selected)
        combo_rol.bind("<<ComboboxSelected>>", on_principal_selected)

        extras_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        extras_frame.pack(fill="x", padx=8, pady=0)
        ctk.CTkLabel(extras_frame, text="Roles extra", width=95, anchor="w",
                    font=("Segoe UI", 9), text_color=c['text_gray']).pack(side="left")

        extras_cbs = {}
        def on_check_extra(*_):
            for role, var in roles_extras_vars.items():
                # Solo abrir si acaban de marcarlo (valor True y antes era False)
                if var.get() and (not hasattr(var, "_opened") or not var._opened):
                    var._opened = True  # marca que ya mostró la ventana
                    abrir_modal_campos_rol(role)
                elif not var.get():
                    var._opened = False  # si desmarcan, deja que pueda volver a abrir

        for role in available_roles:
            cb = ttk.Checkbutton(extras_frame, text=role.capitalize(), variable=roles_extras_vars[role])
            cb.pack(side="left", padx=2)
            extras_cbs[role] = cb
            roles_extras_vars[role].trace_add("write", on_check_extra)
        

        def abrir_modal_campos_rol(rol):
            # Crea el toplevel
            top = tk.Toplevel(win)
            top.title(f"Completa los datos para el rol: {rol}")
            top.transient(win)
            top.grab_set()
            top.resizable(False, False)
            top.geometry("300x230+{}+{}".format(win.winfo_rootx()+60, win.winfo_rooty()+80))

            campos = []
            if rol == "alumno":
                campos = [("Facultad", vars_['facultad']), ("Carrera", vars_['carrera']),
                        ("Grado", vars_['grado']), ("Grupo", vars_['grupo'])]
            elif rol == "maestro":
                campos = [("Grado que imparte", vars_['grado']), ("Materia", vars_['materia'])]
            elif rol == "personal":
                campos = [("Puesto", vars_['puesto']), ("Área", vars_['area'])]

            for i, (label, var) in enumerate(campos):
                ttk.Label(top, text=label, anchor="w").grid(row=i, column=0, sticky="w", padx=8, pady=4)
                ttk.Entry(top, textvariable=var, width=22).grid(row=i, column=1, padx=8, pady=4)

            def guardar_y_cerrar():
                # Puedes validar aquí si quieres
                top.destroy()

            ttk.Button(top, text="Guardar", command=guardar_y_cerrar).grid(row=len(campos), column=0, columnspan=2, pady=12)

            # Asegurarse que la ventana esté encima
            top.focus_force()

        btns = ctk.CTkFrame(win, fg_color="transparent")
        btns.pack(fill="x", padx=6, pady=4, side="bottom")

        btn_guardar = ctk.CTkButton(btns, text="💾", width=60, height=26,
                                    fg_color=c['primary'],
                                    font=("Segoe UI", 9, "bold"),
                                    state="normal",
                                    command=lambda: self._guardar_edicion(u['id'], vars_, win))
        btn_guardar.pack(side="left", padx=2)

        ctk.CTkButton(btns, text="📸", width=60, height=26,
                    fg_color=c['accent'],
                    font=("Segoe UI", 9, "bold"),
                    command=lambda: self._retomar_fotos(u, win)).pack(side="left", padx=2)

        ctk.CTkButton(btns, text="✖", width=60, height=26,
                    fg_color=c['content_bg'], text_color=c['text_dark'],
                    command=win.destroy).pack(side="right", padx=2)

        # Evita seleccionar el mismo en principal y extra
        def update_extras_disabled(*_):
            principal = vars_['rol'].get()
            for role, cb in extras_cbs.items():
                if role == principal:
                    cb.config(state="disabled")
                    if roles_extras_vars[role].get():
                        roles_extras_vars[role].set(False)
                else:
                    cb.config(state="normal")

        # Botones
        btns = ctk.CTkFrame(win, fg_color="transparent")
        btns.pack(fill="x", padx=6, pady=4)

        btn_guardar = ctk.CTkButton(btns, text="💾", width=60, height=26,
                                    fg_color=c['primary'],
                                    font=("Segoe UI", 9, "bold"),
                                    state="disabled",
                                    command=lambda: self._guardar_edicion(u['id'], vars_, win))
        btn_guardar.pack(side="left", padx=2)

        ctk.CTkButton(btns, text="📸", width=60, height=26,
                      fg_color=c['accent'],
                      font=("Segoe UI", 9, "bold"),
                      command=lambda: self._retomar_fotos(u, win)).pack(side="left", padx=2)

        ctk.CTkButton(btns, text="✖", width=60, height=26,
                      fg_color=c['content_bg'], text_color=c['text_dark'],
                      command=win.destroy).pack(side="right", padx=2)

        def detectar(*_):
            changed = any(v.get() != originales[k] for k, v in vars_.items())
            btn_guardar.configure(state="normal" if changed else "disabled")

        for v in vars_.values():
            v.trace_add("write", detectar)
        
        for var in roles_extras_vars.values():
            var.trace_add("write", detectar)

    def _guardar_edicion(self, user_id, vars_, ventana):
        import re
        g = lambda k: vars_[k].get().strip()

        nombre   = g('nombre')
        paterno  = g('paterno')
        matricula = g('matricula')
        telefono  = g('telefono')
        correo    = g('correo') if 'correo' in vars_ else ''
        rol_principal = g('rol')
        roles_extra = [role for role, var in roles_extras_vars.items() if var.get() and role != rol_principal]
        rol_full = ",".join([rol_principal] + roles_extra)

        # ── 1. Campos obligatorios ────────────────────────────────────────────
        if not nombre or not paterno:
            messagebox.showwarning(t("campos_obligatorios"), t("error_nombre"))
            return

        for campo, clave in [
            (nombre,    "nombre"),
            (paterno,   "apellido_paterno"),
            (matricula, "matricula"),
            (telefono,  "telefono"),
        ]:
            if not campo:
                messagebox.showwarning(
                    t("campo_requerido"),
                    f"{t('campo_requerido')}: {t(clave)}"
                )
                return
            if clave not in ("matricula", "telefono") and len(campo) < 3:
                messagebox.showwarning(
                    "Error",
                    f"{t(clave)} debe tener mínimo 3 caracteres"
                )
                return

        # ── 2. Formato nombre y apellido (solo letras) ────────────────────────
        regex_nombre = r"^[A-Za-zÁÉÍÓÚáéíóúÑñ\s]+$"
        if not re.match(regex_nombre, nombre):
            messagebox.showwarning("Error", t("nombre_invalido"))
            return
        if not re.match(regex_nombre, paterno):
            messagebox.showwarning("Error", t("apellido_invalido"))
            return

        # ── 3. Matrícula: solo dígitos, longitud exacta según rol ──────────────
        longitud_matricula = 8 if rol_principal == "alumno" else 6
        if not matricula.isdigit():
            messagebox.showwarning("Error", t("matricula_num"))
            return
        if len(matricula) != longitud_matricula:
            messagebox.showwarning(
                "Error",
                t("matricula_longitud").format(n=longitud_matricula)
            )
            return

        # ── 4. Teléfono: solo dígitos, entre 10 y 12 ─────────────────────────
        if not telefono.isdigit():
            messagebox.showwarning("Error", t("telefono_num"))
            return
        if len(telefono) < 10:
            messagebox.showwarning("Error", t("telefono_min"))
            return
        if len(telefono) > 12:
            messagebox.showwarning("Error", t("telefono_max"))
            return

        # ── 5. Correo (si el campo existe en la ventana) ──────────────────────
        #if correo and not re.match(r"^[^@]+@[a-zA-Z]{3,}\.[a-zA-Z]{2,}$", correo):
            messagebox.showwarning("Error", t("correo_invalido"))
            return

        # ── 6. Campos por rol ─────────────────────────────────────────────────
        campos_rol_check = {
            "alumno":   [("facultad", g('facultad')), ("carrera", g('carrera')),
                         ("grado",    g('grado')),    ("grupo",   g('grupo'))],
            "maestro":  [("grado_imparte", g('grado')), ("materia", g('materia'))],
            "personal": [("puesto", g('puesto')), ("area", g('area'))],
        }
        
        # Valida campos de todos los roles seleccionados
        selected_roles = [rol_principal] + roles_extra
        for rol in selected_roles:
            for clave, valor in campos_rol_check.get(rol, []):
                if not valor:
                    messagebox.showwarning(
                        t("campo_requerido"),
                        f"{t('campo_requerido')}: {t(clave)}"
                    )
                    return
            if len(valor) < 3:
                messagebox.showwarning(
                    "Error",
                    t("campo_min_caracteres").format(campo=t(clave), min=3)
                )
                return

        # ── 7. Unicidad en BD (excluyendo el propio usuario) ──────────────────
        try:
            conn_check = get_db()
            if not conn_check:
                messagebox.showerror("Error", "No se pudo conectar a la base de datos")
                return
            cur = conn_check.cursor()

            cur.execute(
                "SELECT 1 FROM usuarios WHERE correoUsuario = ? AND idUsuario != ?",
                (correo, user_id)
            )
            if correo and cur.fetchone():
                messagebox.showwarning("Error", t("correo_existe"))
                conn_check.close()
                return

            cur.execute(
                "SELECT 1 FROM usuarios WHERE telefonoUsuario = ? AND idUsuario != ?",
                (telefono, user_id)
            )
            if cur.fetchone():
                messagebox.showwarning("Error", t("telefono_existe"))
                conn_check.close()
                return

            cur.execute(
                "SELECT 1 FROM usuarios WHERE matriculaUsuario = ? AND idUsuario != ?",
                (matricula, user_id)
            )
            if cur.fetchone():
                messagebox.showwarning("Error", t("matricula_existe"))
                conn_check.close()
                return

            conn_check.close()
        except Exception as e:
            messagebox.showerror(t("error"), f"Error al validar datos: {e}")
            return

        # ── 8. Todo correcto → guardar ────────────────────────────────────────
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
            """, (nombre, paterno, g('materno'), matricula, telefono,
                  g('fecha_nacimiento'), g('tipo_sangre'), rol_full, user_id))

            cursor.execute("DELETE FROM alumnos          WHERE fkIdUsuario = ?", (user_id,))
            cursor.execute("DELETE FROM maestros         WHERE fkIdUsuario = ?", (user_id,))
            cursor.execute("DELETE FROM personal_escolar WHERE fkIdUsuario = ?", (user_id,))

            roles_antes = set(self.usuario_seleccionado.get('rol', '').split(',')) if self.usuario_seleccionado.get('rol') else set()
            roles_despues = set(selected_roles)

            # ELIMINA registros de roles que ya NO tiene
            for rol in roles_antes - roles_despues:
                if rol == "alumno":
                    cursor.execute("DELETE FROM alumnos WHERE fkIdUsuario = ?", (user_id,))
                elif rol == "maestro":
                    cursor.execute("DELETE FROM maestros WHERE fkIdUsuario = ?", (user_id,))
                elif rol == "personal":
                    cursor.execute("DELETE FROM personal_escolar WHERE fkIdUsuario = ?", (user_id,))

            # AGREGA registros nuevos de roles que antes no había
            for rol in roles_despues - roles_antes:
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
            # Si sigue teniendo el rol, ACTUALIZA datos según nuevos inputs (¡opcional pero deseable!)
            for rol in roles_despues & roles_antes:
                if rol == "alumno":
                    cursor.execute("""
                        UPDATE alumnos
                        SET facultadAlumno=?, carreraAlumno=?, gradoAlumno=?, grupoAlumno=?
                        WHERE fkIdUsuario=?
                    """, (g('facultad'), g('carrera'), g('grado'), g('grupo'), user_id))
                elif rol == "maestro":
                    cursor.execute("""
                        UPDATE maestros
                        SET gradoImpartidoMaestro=?, materiaImpartidaMaestro=?
                        WHERE fkIdUsuario=?
                    """, (g('grado'), g('materia'), user_id))
                elif rol == "personal":
                    cursor.execute("""
                        UPDATE personal_escolar
                        SET puestoPersonalEscolar=?, areaPersonalEscolar=?
                        WHERE fkIdUsuario=?
                    """, (g('puesto'), g('area'), user_id))

            conn.commit()
            conn.close()
            messagebox.showinfo(t("actualizado"), t("usuario_actualizado"))
            ventana.destroy()
            self.cargar_datos()

        except Exception as e:
            messagebox.showerror(t("error"), t("no_actualizar").format(e))

    def _retomar_fotos(self, usuario, ventana_actual):
        import tkinter as tk
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