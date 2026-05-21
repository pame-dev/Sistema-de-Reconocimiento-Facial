# views/informacion_escolar/acciones_usuario.py
from tkinter import messagebox
from config import get_db
from idiomas import t
from database.queries import sp_eliminar_usuario, sp_restaurar_usuario


class AccionesUsuarioMixin:
    """
    Eliminar y restaurar usuarios, y navegar a detalles o edición por ID.
    Requiere: self.usuario_seleccionado, self.datos, self.tabla,
    self.filtro_estado, self.cargar_datos(), self.ocultar_detalles_panel(),
    self.mostrar_detalles_panel(), self.crear_panel_detalles(),
    self.editar_usuario(), self._is_alive().
    """

    def eliminar_usuario(self):
        if not self.usuario_seleccionado:
            return
        u = self.usuario_seleccionado
        if not messagebox.askyesno(
            t("confirm_deletion"),
            t("delete_user_msg").format(
                nombre=u['nombre'],
                apellido=u.get('apellido_paterno', ''),
                rol=u['rol'],
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
            messagebox.showinfo(t("eliminado"), t("usuario_eliminado").format(u['nombre']))
        except Exception as e:
            messagebox.showerror(t("error"), t("error_eliminar").format(e))

    def restaurar_usuario(self):
        if not self.usuario_seleccionado:
            return
        u = self.usuario_seleccionado
        if not messagebox.askyesno(
            t("confirm_restoration"),
            t("restore_user_msg").format(nombre=u['nombre'])
        ):
            return
        try:
            conn = get_db()
            sp_restaurar_usuario(conn, u['id'])
            conn.commit()
            conn.close()
            messagebox.showinfo(t("restaurado"), t("usuario_restaurado").format(u['nombre']))
            self.usuario_seleccionado = None
            self.ocultar_detalles_panel()
            self.filtro_estado.set(t("activos"))
            self.cargar_datos()
        except Exception as e:
            messagebox.showerror(t("error"), t("error_restaurar").format(e))

    def mostrar_edicion_por_id(self, user_id: int):
        """Selecciona un usuario por ID y abre su edición directamente."""
        if not self._is_alive():
            return
        if not self.datos:
            self.cargar_datos()

        usuario = next((u for u in self.datos if u['id'] == user_id), None)
        if not usuario:
            messagebox.showwarning(t("atencion"), t("selecciona_usuario"))
            return

        self.usuario_seleccionado = usuario
        try:
            self.tabla.selection_set(str(user_id))
            self.tabla.focus(str(user_id))
            self.tabla.see(str(user_id))
        except Exception:
            pass

        self.mostrar_detalles_panel()
        self.crear_panel_detalles()
        self.editar_usuario()

    def mostrar_detalles_por_id(self, user_id: int):
        """Selecciona un usuario por ID y muestra solo su panel de detalles."""
        if not self._is_alive():
            return
        if not self.datos:
            self.cargar_datos()

        usuario = next((u for u in self.datos if u['id'] == user_id), None)
        if not usuario:
            messagebox.showwarning(t("atencion"), t("selecciona_usuario"))
            return

        self.usuario_seleccionado = usuario
        try:
            self.tabla.selection_set(str(user_id))
            self.tabla.focus(str(user_id))
            self.tabla.see(str(user_id))
        except Exception:
            pass

        self.mostrar_detalles_panel()
        self.crear_panel_detalles()