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
        win.grab_set()
        win.overrideredirect(True)

        width, height = 340, 460
        root = self.parent.winfo_toplevel()
        root.update_idletasks()
        win.geometry(f"{width}x{height}+{root.winfo_rootx()}+{root.winfo_rooty()}")
        win.minsize(width, height)
        win.maxsize(width, height)

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

        scroll = ctk.CTkFrame(win, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        def make_entry(parent, label, var, key=None):
            row = ctk.CTkFrame(parent, fg_color="transparent")
            row.pack(fill="x", padx=8, pady=1)
            ctk.CTkLabel(row, text=label, width=95, anchor="w",
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
        make_entry(scroll, t("nombre_req"),          vars_['nombre'])
        make_entry(scroll, t("apellido_paterno_req"), vars_['paterno'])
        make_entry(scroll, t("apellido_materno"),     vars_['materno'])
        make_entry(scroll, t("matricula"),            vars_['matricula'])
        make_entry(scroll, t("telefono"),             vars_['telefono'])
        make_entry(scroll, t("fecha_nacimiento"),     vars_['fecha_nacimiento'], "fecha_nacimiento")
        make_entry(scroll, t("tipo_sangre"),          vars_['tipo_sangre'],      "tipo_sangre")

        # Selector de rol
        rol_row = ctk.CTkFrame(scroll, fg_color="transparent")
        rol_row.pack(fill="x", padx=8, pady=4)
        ctk.CTkLabel(rol_row, text=t("rol"), width=95, anchor="w",
                     font=("Segoe UI", 9),
                     text_color=c['text_gray']).pack(side="left")
        combo_rol = ttk.Combobox(rol_row, textvariable=vars_['rol'],
                                 values=["alumno", "maestro", "personal"],
                                 state="readonly", width=10)
        combo_rol.pack(side="left")

        role_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        role_frame.pack(fill="x")

        def build_role(*_):
            for w in role_frame.winfo_children():
                w.destroy()
            rol = vars_['rol'].get()
            if rol == "alumno":
                make_entry(role_frame, t("facultad"),    vars_['facultad'])
                make_entry(role_frame, t("carrera"),     vars_['carrera'])
                make_entry(role_frame, t("grado"),       vars_['grado'])
                make_entry(role_frame, t("grupo"),       vars_['grupo'])
            elif rol == "maestro":
                make_entry(role_frame, t("grado_imparte"), vars_['grado'])
                make_entry(role_frame, t("materia"),       vars_['materia'])
            else:
                make_entry(role_frame, t("puesto"), vars_['puesto'])
                make_entry(role_frame, t("area"),   vars_['area'])

        combo_rol.bind("<<ComboboxSelected>>", build_role)
        build_role()

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

    def _guardar_edicion(self, user_id, vars_, ventana):
        import re
        g = lambda k: vars_[k].get().strip()

        nombre   = g('nombre')
        paterno  = g('paterno')
        matricula = g('matricula')
        telefono  = g('telefono')
        correo    = g('correo') if 'correo' in vars_ else ''
        rol       = g('rol')

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
        longitud_matricula = 8 if rol == "alumno" else 6
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
                  g('fecha_nacimiento'), g('tipo_sangre'), rol, user_id))

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