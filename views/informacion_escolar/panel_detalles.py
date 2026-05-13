# views/informacion_escolar/panel_detalles.py
import customtkinter as ctk
from config import COLORS
from idiomas import t
from views.informacion_escolar.estilos import ROL_COLOR, ROL_ICONO, principal_rol


def roles_mostrados(rol):
    if not rol:
        return '—'
    roles = [r.strip() for r in str(rol).split(',') if r.strip()]
    if not roles:
        return '—'
    return ', '.join(r.capitalize() for r in roles)


class PanelDetallesMixin:
    """
    Panel colapsable con la información completa del usuario seleccionado.
    Requiere: self.colors, self.detalles_frame, self.acciones_frame,
    self.tabla_frame, self.btn_editar, self.btn_eliminar, self.btn_restaurar,
    self.filtro_estado, self.usuario_seleccionado, self._is_alive(),
    self._is_small_screen().
    """

    def crear_panel_detalles(self):
        if not self._is_alive():
            return
        for w in self.detalles_frame.winfo_children():
            w.destroy()
        if not self.usuario_seleccionado:
            return

        c     = self.colors
        u     = self.usuario_seleccionado
        rol   = principal_rol(u.get('rol', ''))
        color = ROL_COLOR.get(rol, COLORS['primary'])
        icono = ROL_ICONO.get(rol, '👤')

        # Cabecera coloreada
        ph = ctk.CTkFrame(self.detalles_frame, fg_color=color, corner_radius=0, height=36)
        ph.pack(fill="x")
        ph.pack_propagate(False)

        nombre_completo = (
            f"{u.get('nombre','')} "
            f"{u.get('apellido_paterno','')} "
            f"{u.get('apellido_materno','')}".strip()
        )
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

        # Cuerpo de campos
        body = ctk.CTkFrame(self.detalles_frame, fg_color="transparent")
        body.pack(fill="x", padx=16, pady=10)

        is_small = self._is_small_screen()
        for col_items in self._get_cols_data(u, rol):
            col_frame = ctk.CTkFrame(body, fg_color="transparent")
            side = "top" if is_small else "left"
            col_frame.pack(side=side, fill="x", expand=True,
                           padx=(0, 16), pady=(0, 8) if is_small else 0)
            for label, valor in col_items:
                self._detail_item(col_frame, label, valor, color)

    def _get_cols_data(self, u, rol):
        col1 = [
            (t("nombre"),          u.get('nombre', '—')),
            (t("apellido_paterno"), u.get('apellido_paterno', '—')),
            (t("apellido_materno"), u.get('apellido_materno', '—')),
        ]
        col2 = [
            (t("matricula"),        u.get('matricula', '—')),
            (t("telefono"),         u.get('telefono', '—')),
            (t("fecha_nacimiento"), u.get('fecha_nacimiento', '—')),
            (t("tipo_sangre"),      u.get('tipo_sangre', '—')),
            (t("rol"),              roles_mostrados(u.get('rol', rol))),
        ]
        col3 = []
        if rol == 'alumno':
            col3 = [
                (t("facultad"), u.get('facultad', '—')),
                (t("carrera"),  u.get('carrera',  '—')),
                (t("grado"),    u.get('grado',    '—')),
                (t("grupo"),    u.get('grupo',    '—')),
            ]
        elif rol == 'maestro':
            col3 = [
                (t("materia"),       u.get('materia', '—')),
                (t("grado_imparte"), u.get('grado',   '—')),
            ]
        elif rol == 'personal':
            col3 = [
                (t("puesto"), u.get('puesto', '—')),
                (t("area"),   u.get('area',   '—')),
            ]
        return [c for c in [col1, col2, col3] if c]

    def _detail_item(self, parent, label, valor, color):
        c   = self.colors
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=2)
        ctk.CTkLabel(row, text=label + ":",
                     font=("Segoe UI", 10),
                     text_color=c['text_gray'],
                     width=130, anchor="w").pack(side="left")
        ctk.CTkLabel(row, text=str(valor),
                     font=("Segoe UI", 10, "bold"),
                     text_color=c['text_dark'],
                     anchor="w").pack(side="left")

    # ── Visibilidad del panel ─────────────────────────────────────────────────
    def mostrar_detalles_panel(self):
        if not self._is_alive():
            return
        if not self.detalles_frame.winfo_ismapped():
            self.detalles_frame.pack(fill="x", pady=(0, 8), before=self.tabla_frame)
        if not self.acciones_frame.winfo_ismapped():
            self.acciones_frame.pack(fill="x", pady=(0, 6), before=self.detalles_frame)

        for widget in self.acciones_frame.winfo_children():
            widget.pack_forget()

        if self.filtro_estado.get() == t("inactivos"):
            self.btn_restaurar.pack(side="left")
        else:
            self.btn_editar.pack(side="left", padx=(0, 8))
            self.btn_eliminar.pack(side="left")

        ctk.CTkButton(
            self.acciones_frame,
            text="❌ " + t("ocultar_detalles"),
            fg_color=self.colors['danger'],
            hover_color=COLORS['danger_dark'],
            text_color="#ffffff",
            font=("Segoe UI", 12, "bold"),
            corner_radius=10, height=36,
            command=self.ocultar_detalles_panel,
        ).pack(side="left", padx=(8, 0))

        self.container.update_idletasks()

    def ocultar_detalles_panel(self):
        if not self._is_alive():
            return
        if self.acciones_frame.winfo_ismapped():
            self.acciones_frame.pack_forget()
        if self.detalles_frame.winfo_ismapped():
            self.detalles_frame.pack_forget()

    def toggle_detalles(self):
        if self.detalles_frame.winfo_ismapped():
            self.ocultar_detalles_panel()
        elif self.usuario_seleccionado:
            self.mostrar_detalles_panel()
            self.crear_panel_detalles()
        else:
            from tkinter import messagebox
            messagebox.showinfo(t("detalles"), t("selecciona_usuario"))