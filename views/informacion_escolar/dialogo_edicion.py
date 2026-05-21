# views/informacion_escolar/dialogo_edicion.py
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import customtkinter as ctk
from tkcalendar import DateEntry

from config import COLORS, get_db
from idiomas import t
from views.informacion_escolar.estilos import ROL_COLOR, ROL_ICONO, principal_rol


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
        color = ROL_COLOR.get(principal_rol(u.get('rol', '')), COLORS['primary'])
        roles_usuario = [r.strip() for r in u.get('rol', '').split(",") if r.strip()]

        def _rol_val(key, rol):
            return _val(key) if rol in roles_usuario else ''

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
            'facultad':         tk.StringVar(value=_rol_val('facultad', 'alumno')),
            'carrera':          tk.StringVar(value=_rol_val('carrera', 'alumno')),
            'grado_alumno':     tk.StringVar(value=_rol_val('grado', 'alumno')),
            'grupo':            tk.StringVar(value=_rol_val('grupo', 'alumno')),
            'grado_maestro':    tk.StringVar(value=_rol_val('grado', 'maestro')),
            'materia':          tk.StringVar(value=_rol_val('materia', 'maestro')),
            'puesto':           tk.StringVar(value=_rol_val('puesto', 'personal')),
            'area':             tk.StringVar(value=_rol_val('area', 'personal')),
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

        width, height = 390, 440
        win.geometry(f"{width}x{height}+{root.winfo_rootx()}+{root.winfo_rooty()}")
        win.minsize(width, height)

        # Header
        header = ctk.CTkFrame(win, fg_color=color, height=42)
        header.pack(fill="x")
        ctk.CTkLabel(header,
                     text=f"{ROL_ICONO.get(principal_rol(u.get('rol', '')), '👤')} Editar",
                     text_color="white",
                     font=("Segoe UI", 11, "bold")).pack(side="left", padx=10)
        ctk.CTkButton(header, text="✕", width=26, height=24,
                      fg_color="transparent", text_color="white",
                      command=win.destroy).pack(side="right", padx=6)

        content_frame = ctk.CTkFrame(win, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=12, pady=(4, 0))

        main_frame = ctk.CTkScrollableFrame(content_frame, fg_color="transparent")
        main_frame.pack(fill="both", expand=True)

        icon_map = {
            'nombre': '👤', 'paterno': '👨', 'materno': '👩',
            'matricula': '🎓', 'telefono': '☎️', 'fecha_nacimiento': '📅',
            'tipo_sangre': '🩸', 'rol': '👥', 'facultad': '🏫',
            'carrera': '📚', 'grado': '📊', 'grupo': '👥',
            'materia': '📖', 'puesto': '💼', 'area': '🗺️'
        }

        def make_entry(parent, label, var, key=None):
            row = ctk.CTkFrame(parent, fg_color="transparent")
            row.pack(fill="x", padx=8, pady=0)
            icon_text = (icon_map.get(key, '') + " ") if key in icon_map else ""
            ctk.CTkLabel(row, text=icon_text + label, width=95, anchor="w",
                         font=("Segoe UI", 9),
                         text_color=c['text_gray']).pack(side="left")
            if key == "fecha_nacimiento":

                hoy = datetime.now()
                fecha_maxima = hoy.replace(year=hoy.year - 17)

                e = DateEntry(row, date_pattern='dd-mm-yyyy', maxdate=fecha_maxima, textvariable=var, width=9, state="readonly")
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
        rol_row.pack(fill="x", padx=8, pady=2)
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
        ctk.CTkLabel(
            extras_frame,
            text=t("roles_extra"),
            width=95,
            anchor="w",
            font=("Segoe UI", 9),
            text_color=c['text_gray']
        ).pack(side="left")

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
            cb = ttk.Checkbutton(
                extras_frame,
                text=t(role),
                variable=roles_extras_vars[role]
            )
            cb.pack(side="left", padx=2)
            extras_cbs[role] = cb
            roles_extras_vars[role].trace_add("write", on_check_extra)
        

        def abrir_modal_campos_rol(rol):
            # Crea el toplevel
            top = tk.Toplevel(win)
            top.title(f"{t('completa_datos_rol')}: {t(rol)}")
            top.transient(win)
            top.grab_set()
            top.resizable(False, False)
            top.geometry("300x230+{}+{}".format(win.winfo_rootx()+60, win.winfo_rooty()+80))

            campos = []
            if rol == "alumno":
                campos = [
                    (t("facultad"), vars_['facultad']),
                    (t("carrera"), vars_['carrera']),
                    (t("grado"), vars_['grado_alumno']),
                    (t("grupo"), vars_['grupo'])
                ]
            elif rol == "maestro":
                campos = [
                    (t("grado_imparte"), vars_['grado_maestro']),
                    (t("materia"), vars_['materia'])
                ]
            elif rol == "personal":
                campos = [
                    (t("puesto"), vars_['puesto']),
                    (t("area"), vars_['area'])
                ]

            for i, (label, var) in enumerate(campos):
                ttk.Label(top, text=label, anchor="w").grid(row=i, column=0, sticky="w", padx=8, pady=4)
                ttk.Entry(top, textvariable=var, width=22).grid(row=i, column=1, padx=8, pady=4)

            def guardar_y_cerrar():
                # Puedes validar aquí si quieres
                top.destroy()

            ttk.Button(top, text=t("guardar"), command=guardar_y_cerrar).grid(row=len(campos), column=0, columnspan=2, pady=12)

            # Asegurarse que la ventana esté encima
            top.focus_force()

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

        # Asegurar que los checkboxes extra reflejen el rol principal seleccionado
        vars_['rol'].trace_add("write", lambda *_: update_extras_disabled())
        update_extras_disabled()

        # Botones
        btns = ctk.CTkFrame(main_frame, fg_color="transparent")
        btns.pack(fill="x", padx=3, pady=(0, 8))

        btn_guardar = ctk.CTkButton(btns, text="💾", width=60, height=26,
                                    fg_color=c['primary'],
                                    font=("Segoe UI", 9, "bold"),
                                    state="disabled",
                                    command=lambda: self._guardar_edicion(u['id'], vars_, roles_extras_vars, win))
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

    def _guardar_edicion(self, user_id, vars_, roles_extras_vars, ventana):
        import re
        g = lambda k: vars_[k].get().strip()

        def _warn(title, message):
            messagebox.showwarning(title, message, parent=ventana)
            ventana.after_idle(lambda: (ventana.lift(), ventana.focus_force()))

        def _error(title, message):
            messagebox.showerror(title, message, parent=ventana)
            ventana.after_idle(lambda: (ventana.lift(), ventana.focus_force()))

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
            _warn(t("campos_obligatorios"), t("error_nombre"))
            return

        for campo, clave in [
            (nombre,    "nombre"),
            (paterno,   "apellido_paterno"),
            (matricula, "matricula"),
            (telefono,  "telefono"),
        ]:
            if not campo:
                _warn(
                    t("campo_requerido"),
                    f"{t('campo_requerido')}: {t(clave)}"
                )
                return
            sin_minimo = ("matricula", "telefono", "grado_imparte", "grado", "grupo")   
            if clave not in sin_minimo and len(campo) < 3:
                _warn(
                    "Error",
                    f"{t(clave)} debe tener mínimo 3 caracteres"
                )
                return

        # ── 2. Formato nombre y apellido (solo letras) ────────────────────────
        regex_nombre = r"^[A-Za-zÁÉÍÓÚáéíóúÑñ\s]+$"
        if not re.match(regex_nombre, nombre):
            _warn("Error", t("nombre_invalido"))
            return
        if not re.match(regex_nombre, paterno):
            _warn("Error", t("apellido_invalido"))
            return

        # ── 3. Matrícula: solo dígitos, longitud exacta según rol ──────────────
        longitud_matricula = 8 if rol_principal == "alumno" else 6
        if not matricula.isdigit():
            _warn("Error", t("matricula_num"))
            return
        if len(matricula) != longitud_matricula:
            _warn(
                "Error",
                t("matricula_longitud").format(n=longitud_matricula)
            )
            return

        # ── 4. Teléfono: solo dígitos, entre 10 y 12 ─────────────────────────
        if not telefono.isdigit():
            _warn("Error", t("telefono_num"))
            return
        if len(telefono) < 10:
            _warn("Error", t("telefono_min"))
            return
        if len(telefono) > 12:
            _warn("Error", t("telefono_max"))
            return

        # ── 5. Correo (si el campo existe en la ventana) ──────────────────────
        if correo and not re.match(r"^[^@]+@[a-zA-Z]{3,}\.[a-zA-Z]{2,}$", correo):
            _warn("Error", t("correo_invalido"))
            return

        # ── 6. Campos por rol ─────────────────────────────────────────────────
        campos_rol_check = {
            "alumno":   [("facultad", g('facultad')), ("carrera", g('carrera')),
                         ("grado_alumno", g('grado_alumno')), ("grupo", g('grupo'))],
            "maestro":  [("grado_imparte", g('grado_maestro')), ("materia", g('materia'))],
            "personal": [("puesto", g('puesto')), ("area", g('area'))],
        }
        
        # Valida campos de todos los roles seleccionados
        selected_roles = [rol_principal] + roles_extra
        for rol in selected_roles:
            for clave, valor in campos_rol_check.get(rol, []):
                if not valor:
                    _warn(
                        t("campo_requerido"),
                        f"{t('campo_requerido')}: {t(clave)}"
                    )
                    return

                sin_minimo_rol = {
                    "alumno": {"grado_alumno", "grupo"},
                    "maestro": {"grado_imparte"},
                    "personal": set(),
                }
                if clave not in sin_minimo_rol.get(rol, set()) and len(valor) < 3:
                    _warn(
                        "Error",
                        t("campo_min_caracteres").format(campo=t(clave), min=3)
                    )
                    return

        # ── 7. Unicidad en BD (excluyendo el propio usuario) ──────────────────
        try:
            conn_check = get_db()
            if not conn_check:
                _error("Error", "No se pudo conectar a la base de datos")
                return
            cur = conn_check.cursor()

            cur.execute(
                "SELECT 1 FROM usuarios WHERE correoUsuario = ? AND idUsuario != ?",
                (correo, user_id)
            )
            if correo and cur.fetchone():
                _warn("Error", t("correo_existe"))
                conn_check.close()
                return

            cur.execute(
                "SELECT 1 FROM usuarios WHERE telefonoUsuario = ? AND idUsuario != ?",
                (telefono, user_id)
            )
            if cur.fetchone():
                _warn("Error", t("telefono_existe"))
                conn_check.close()
                return

            cur.execute(
                "SELECT 1 FROM usuarios WHERE matriculaUsuario = ? AND idUsuario != ?",
                (matricula, user_id)
            )
            if cur.fetchone():
                _warn("Error", t("matricula_existe"))
                conn_check.close()
                return

            conn_check.close()
        except Exception as e:
            _error(t("error"), f"Error al validar datos: {e}")
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

            roles_antes = {r.strip() for r in self.usuario_seleccionado.get('rol', '').split(',') if r.strip()}
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
                    """, (user_id, g('facultad'), g('carrera'), g('grado_alumno'), g('grupo')))
                elif rol == "maestro":
                    cursor.execute("""
                        INSERT INTO maestros
                        (fkIdUsuario, gradoImpartidoMaestro, materiaImpartidaMaestro)
                        VALUES (?, ?, ?)
                    """, (user_id, g('grado_maestro'), g('materia')))
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
                    """, (g('facultad'), g('carrera'), g('grado_alumno'), g('grupo'), user_id))
                elif rol == "maestro":
                    cursor.execute("""
                        UPDATE maestros
                        SET gradoImpartidoMaestro=?, materiaImpartidaMaestro=?
                        WHERE fkIdUsuario=?
                    """, (g('grado_maestro'), g('materia'), user_id))
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
        try:
            from views.nuevo_registro_view import NuevoRegistroView
            
            rol = principal_rol(usuario.get('rol', 'alumno')) or 'alumno'
            user_id = usuario.get('id')
            parent_frame = self.parent  # Guardar referencia antes de que se destruya

            try:
                main_view = getattr(parent_frame, 'main_view', None)
                if main_view:
                    main_view._stop_camera()
            except Exception:
                pass

            try:
                ventana_actual.grab_release()
            except Exception:
                pass
            try:
                ventana_actual.withdraw()
            except Exception:
                pass
            
            # Preparar valores del formulario
            valores_form = {
                'nombre':       usuario.get('nombre', ''),
                'paterno':      usuario.get('apellido_paterno', ''),
                'materno':      usuario.get('apellido_materno', ''),
                'matricula':    usuario.get('matricula', ''),
                'telefono':     usuario.get('telefono', ''),
                'correo':       usuario.get('correo', ''),
                'grado':        usuario.get('grado', ''),
                'grupo':        usuario.get('grupo', ''),
                'carrera':      usuario.get('carrera', ''),
            }
            
            # Callback para volver a información escolar con la vista reconstruida
            def volver_a_edicion():
                # Limpiar todos los widgets del parent
                for widget in parent_frame.winfo_children():
                    try:
                        widget.destroy()
                    except Exception:
                        pass

                try:
                    from views.informacion_escolar_view import InformacionEscolarView
                    vista = InformacionEscolarView(parent_frame)
                    parent_frame.update_idletasks()
                    try:
                        vista.mostrar_detalles_por_id(user_id)
                    except Exception:
                        pass
                except Exception:
                    pass

                try:
                    parent_frame.winfo_toplevel().grab_release()
                except Exception:
                    pass
                try:
                    parent_frame.focus_force()
                except Exception:
                    pass

                # La recaptura vuelve sin mostrar aviso; el guardado final ya se confirma en el flujo de captura.
            
            # Estado inicial con modo retomar fotos
            initial_state = {
                "modo_retomar_fotos": True,
                "rol_actual": rol,
                "user_id": user_id,
                "valores_form": valores_form,
            }
            
            # Cerrar el diálogo de edición actual en lugar de dejarlo oculto
            try:
                ventana_actual.grab_release()
            except Exception:
                pass
            try:
                ventana_actual.destroy()
            except Exception:
                pass
            
            # Limpiar widgets anteriores
            for widget in parent_frame.winfo_children():
                try:
                    widget.destroy()
                except Exception:
                    pass
            
            # Crear vista sin mostrar nada (se muestra después con _mostrar_captura)
            nuevo_reg = NuevoRegistroView(
                parent_frame,
                initial_state=initial_state,
                on_back_callback=volver_a_edicion
            )
            
            # Mostrar directamente la captura de fotos
            nuevo_reg._mostrar_captura()

        except Exception as e:
            messagebox.showerror(t("error"), t("error_captura").format(e))