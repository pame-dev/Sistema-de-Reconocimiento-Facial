# views/formulario.py
import tkinter as tk
from tkinter import messagebox, ttk
from datetime import datetime
import customtkinter as ctk
from tkcalendar import DateEntry

from config import COLORS, get_colors
from idiomas import t
from views.nuevo_registro.constants import ROL_CONFIG, CAMPOS_COMUNES, CAMPOS_POR_ROL
from views.font_scale import FontScale
from views.nuevo_registro.utils import darken


class FormularioMixin:
    """
    Mixin que añade la pantalla de formulario de registro.
    Requiere: self.container, self.colors, self.rol_actual,
    self.entries, self.valores_form, self._limpiar_container(),
    self._mostrar_seleccion_rol(), self._mostrar_animacion_camara().
    """

    def _mostrar_formulario(self):
        self._limpiar_container()
        self.entries = {}
        cfg   = ROL_CONFIG[self.rol_actual]
        color = cfg["color"]

        header = ctk.CTkFrame(self.container, fg_color="transparent")
        header.pack(fill="x", pady=(0, 12))
        ctk.CTkButton(
            header,
            text="← " + t("regresar"),
            fg_color="transparent",
            hover_color=COLORS['content_bg'],
            text_color=color,
            font=("Segoe UI", 10),
            width=65,
            height=26,
            corner_radius=6,
            command=self._mostrar_seleccion_rol
        ).pack(side="left", padx=(4, 2), pady=2)

        badge = ctk.CTkFrame(header, fg_color=color, corner_radius=10)
        badge.pack(side="left", padx=(2, 6))

        ctk.CTkLabel(
            badge,
            text=f"{cfg['icono']} {cfg['titulo']}",
            font=("Segoe UI", 11, "bold"),
            text_color=self.colors['white']
        ).pack(padx=4, pady=2)

        ctk.CTkLabel(
            header,
            text=t("paso_datos"),
            font=("Segoe UI", 12),
            text_color=self.colors['text_gray']
        ).pack(side="left", padx=(6, 0))

        ttk.Separator(self.container, orient="horizontal").pack(fill="x", pady=(0, 15))

        content = ctk.CTkFrame(self.container, fg_color="transparent")
        content.pack(fill="both", expand=True)
        
        scroll = ctk.CTkScrollableFrame(content, fg_color="transparent")
        scroll.pack(fill="both", expand=True)
        
        form_frame = ctk.CTkFrame(scroll, fg_color=self.colors['card_bg'],
                                   corner_radius=14, border_width=1,
                                   border_color=COLORS['border'], width=920)
        form_frame.pack(fill="x", expand=True, padx=24, pady=10)

        self._section_label(form_frame, t("datos_personales"), color)
        self._add_fields_grid(form_frame, CAMPOS_COMUNES, columns=2)

        campos_rol = CAMPOS_POR_ROL.get(self.rol_actual, [])
        if campos_rol:
            titulos = {
                "alumno":   t("info_academica"),
                "maestro":  t("info_docente"),
                "personal": t("info_laboral"),
            }
            self._section_label(form_frame,
                                titulos.get(self.rol_actual, "Datos adicionales"), color)
            self._add_fields_grid(form_frame, campos_rol, columns=2)

        # 👇 SOLO CAMBIÉ ESTO: ahora el botón vive dentro de "content"
        ctk.CTkButton(
            content,
            text=t("continuar_fotos"),
            fg_color=color,
            hover_color=darken(color),
            text_color=self.colors['white'],
            font=FontScale.fb(13),
            corner_radius=10,
            height=42,
            command=self._validar_y_continuar
        ).pack(pady=(30, 20))  # más abajo

        # Restaurar valores previos si los hay
        if hasattr(self, 'valores_form') and self.valores_form:
            for key, entry in self.entries.items():
                if key in self.valores_form:
                    try:
                        entry.delete(0, "end")
                        entry.insert(0, self.valores_form[key])
                    except Exception:
                        pass

    def _section_label(self, parent, text, color):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", pady=(14, 6), padx=12)
        ctk.CTkLabel(frame, text=text, text_color=color,
                     font=("Segoe UI", 12, "bold")).pack(anchor="w")
        ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=(3, 0))

    def _add_fields_grid(self, parent, fields, columns=2):
        grid = ctk.CTkFrame(parent, fg_color="transparent")
        grid.pack(fill="x", padx=12, pady=(0, 6))
        for col in range(columns):
            grid.grid_columnconfigure(col, weight=1, uniform="form_col")
        for idx, (label_text, key, required) in enumerate(fields):
            row = idx // columns
            col = idx % columns
            self._add_entry(grid, label_text, key, required, row, col)

    def _add_entry(self, parent, label_text, key, required, row, col):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.grid(row=row, column=col, sticky="ew", padx=8, pady=6)

        ctk.CTkLabel(
            frame,
            text=label_text + (" *" if required else ""),
            text_color=self.colors['text_dark'],
            font=("Segoe UI", 11),
            anchor="w"
        ).pack(anchor="w", pady=(0, 4))

        if key == "fechaNacimientoUsuario":
            entry = DateEntry(
                frame,
                date_pattern='dd-mm-yyyy',
                maxdate=datetime.now(),
                font=("Segoe UI", 11)
            )
            entry.pack(fill="x", expand=True)

        elif key == "tipoSangreUsuario":
            entry = ttk.Combobox(
                frame,
                values=["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"],
                state="readonly",
                font=("Segoe UI", 11)
            )
            entry.pack(fill="x", expand=True)

        else:
            entry = ctk.CTkEntry(
                frame,
                font=("Segoe UI", 11),
                height=34,
                corner_radius=8,
                border_color=COLORS['border']
            )
            entry.pack(fill="x", expand=True)

        self.entries[key] = entry

    def _validar_y_continuar(self):
        requeridos = {
            'nombreUsuario':          'nombre',
            'apellidoPaternoUsuario': 'apellido paterno',
            'telefonoUsuario':        'teléfono',
            'correoUsuario':          'correo',
        }
        for key in requeridos:
            if not self.entries.get(key, tk.Entry()).get().strip():
                messagebox.showwarning(t("campo_requerido"), t("nombre_obligatorio"))
                return

        for _, key, required in CAMPOS_POR_ROL.get(self.rol_actual, []):
            if required and not self.entries.get(key, tk.Entry()).get().strip():
                messagebox.showwarning(t("campo_requerido"),
                                       f"El campo '{key}' es obligatorio")
                return

        self.valores_form  = {k: e.get().strip() for k, e in self.entries.items()}
        self._camara_lista = False
        self._mostrar_animacion_camara()