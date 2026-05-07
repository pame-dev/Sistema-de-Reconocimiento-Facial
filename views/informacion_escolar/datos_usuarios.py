# views/informacion_escolar/datos_usuarios.py
from tkinter import messagebox
from config import get_db
from idiomas import t
from database.queries import sp_get_usuarios, sp_get_usuarios_inactivos


class DatosUsuariosMixin:
    """
    Carga, filtrado y actualización del Treeview de usuarios.
    Requiere: self.datos, self.tabla, self.lbl_conteo, self.filtro_rol,
    self.busqueda_var, self._placeholder_activo, self._is_alive(),
    self.actualizar_tabla(), self.ocultar_detalles_panel().
    """

    def _fila_desde_row(self, row) -> dict:
        """Convierte una tupla de BD en el dict interno de usuario."""
        (
            user_id, nombre, apellido_paterno, apellido_materno,
            matricula, rol, telefono, correo, fecha_nacimiento,
            tipo_sangre, direccion, carrera, grado, grupo, facultad,
            materia, grado_impartido, puesto, area, fotos, accesos,
        ) = row

        if rol == 'alumno':
            carrera = carrera or '—'
            grado   = grado   or '—'
            grupo   = grupo   or '—'
        elif rol == 'maestro':
            carrera = materia         or '—'
            grado   = grado_impartido or '—'
            grupo   = '—'
        else:
            carrera = puesto or '—'
            grado   = '—'
            grupo   = '—'

        return {
            'id':               user_id,
            'nombre':           nombre           or '',
            'apellido_paterno': apellido_paterno or '—',
            'apellido_materno': apellido_materno or '—',
            'matricula':        matricula        or '—',
            'rol':              rol,
            'telefono':         telefono         or '—',
            'correo':           correo           or '—',
            'fecha_nacimiento': fecha_nacimiento or '—',
            'tipo_sangre':      tipo_sangre      or '—',
            'carrera':          carrera,
            'grado':            grado,
            'grupo':            grupo,
            'materia':          materia          or '—',
            'puesto':           puesto           or '—',
            'area':             area             or '—',
            'facultad':         facultad if rol == 'alumno' else '—',
            'fotos':            fotos            or 0,
            'accesos':          accesos          or 0,
        }

    def cargar_datos(self):
        if not self._is_alive():
            return
        try:
            conn = get_db()
            if not conn:
                messagebox.showerror(t("error"), t("error_db"))
                return
            resultados = sp_get_usuarios(conn)
            conn.close()
            self.datos = [self._fila_desde_row(r) for r in resultados]
            self.actualizar_tabla()
        except Exception as e:
            messagebox.showerror(t("error"), t("error_cargar_datos").format(e))
            self.datos = []

    def cargar_inactivos(self):
        if not self._is_alive():
            return
        try:
            conn = get_db()
            if not conn:
                return
            resultados = sp_get_usuarios_inactivos(conn)
            conn.close()
            self.datos = [self._fila_desde_row(r) for r in resultados]
            self.actualizar_tabla()
        except Exception as e:
            messagebox.showerror(t("error"), t("error_cargar_inactivos").format(e))

    def actualizar_tabla(self, datos_filtrados=None):
        if not self._is_alive():
            return
        for item in self.tabla.get_children():
            self.tabla.delete(item)

        lista = datos_filtrados if datos_filtrados is not None else self.datos
        for u in lista:
            nombre_completo = (
                f"{u.get('nombre','')} "
                f"{u.get('apellido_paterno','')} "
                f"{u.get('apellido_materno','')}".strip()
            )
            self.tabla.insert("", "end", iid=str(u['id']), values=(
                nombre_completo,
                u['matricula'],
                u.get('fecha_nacimiento', '—'),
                u.get('tipo_sangre', '—'),
                u['rol'],
                u['fotos'],
            ), tags=(u.get('rol', ''),))

        total = len(lista)
        self.lbl_conteo.configure(
            text=t("usuarios_total").format(total, "s" if total != 1 else "")
        )
        self.usuario_seleccionado = None
        self.ocultar_detalles_panel()

    def filtrar_tabla(self):
        if not self._is_alive():
            return

        rol_filtro = self.filtro_rol.get()

        # Mapeo texto visible → valor real en BD
        ROL_MAP = {
            t("estudiante"): "alumno",
            t("docente"):    "maestro",
            t("personal"):   "personal",
        }
        rol_bd = ROL_MAP.get(rol_filtro)  # None si es "Todos"

        texto = "" if self._placeholder_activo else self.busqueda_var.get().lower().strip()

        resultado = [
            u for u in self.datos
            if (rol_bd is None or u.get('rol', '') == rol_bd)
            and (not texto
                or texto in str(u.get('nombre', '')).lower()
                or texto in str(u.get('matricula', '')).lower()
                or texto in str(u.get('carrera', '')).lower())
        ]
        self.actualizar_tabla(resultado)

    def cambiar_estado(self):
        if not self._is_alive():
            return
        if self.filtro_estado.get() == t("activos"):
            self.cargar_datos()
        else:
            self.cargar_inactivos()

    def _actualizar_todo(self):
        """Reinicia búsqueda y filtros, luego recarga."""
        import tkinter as tk
        self.filtro_rol.set(t("todos"))
        self.busqueda_var.set("")
        self.entrada_busqueda.delete(0, tk.END)
        self.entrada_busqueda.insert(0, t("placeholder_busqueda"))
        self.entrada_busqueda.configure(text_color=self.colors['text_gray'])
        self._placeholder_activo = True
        self.cargar_datos()