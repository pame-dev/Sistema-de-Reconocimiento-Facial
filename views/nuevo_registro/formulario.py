# views/formulario.py
import tkinter as tk
from tkinter import messagebox, ttk
from datetime import datetime
import customtkinter as ctk
from tkcalendar import DateEntry

from config import COLORS, get_colors, get_db
from idiomas import t
from views.nuevo_registro.constants import ROL_CONFIG, CAMPOS_COMUNES, CAMPOS_POR_ROL
from views.font_scale import FontScale
from views.nuevo_registro.utils import darken
from database.queries import sp_existe_matricula, sp_existe_telefono, sp_existe_correo

class FormularioMixin:

    def _mostrar_formulario(self):
        self._limpiar_container()
        self.entries = {}

        cfg   = ROL_CONFIG[self.rol_actual]
        color = cfg["color"]

        # ── Header ─────────────────────────────────────
        header = ctk.CTkFrame(self.container, fg_color="transparent")
        header.pack(fill="x", pady=(0, 12))

        ctk.CTkButton(
            header,
            text="← " + t("regresar"),
            fg_color="transparent",
            hover_color=COLORS['content_bg'],
            text_color=color,
            font=("Segoe UI", 14),
            width=65,
            height=26,
            corner_radius=6,
            command=self._mostrar_seleccion_rol
        ).pack(side="left", padx=(4, 2), pady=2)

        badge = ctk.CTkFrame(header, fg_color=color, corner_radius=10)
        badge.pack(side="left", padx=(2, 6))

        ctk.CTkLabel(
            badge,
            text=f"{cfg['icono']} {t(cfg['titulo'])}",  # 🔥 traducido
            font=("Segoe UI", 14, "bold"),
            text_color=self.colors['white']
        ).pack(padx=4, pady=2)

        ctk.CTkLabel(
            header,
            text=t("paso_datos"),
            font=("Segoe UI", 14),
            text_color=self.colors['text_gray']
        ).pack(side="left", padx=(6, 0))

        ttk.Separator(self.container, orient="horizontal").pack(fill="x", pady=(0, 15))

        # ── Contenido ──────────────────────────────────
        content = ctk.CTkFrame(self.container, fg_color="transparent")
        content.pack(fill="both", expand=True)

        scroll = ctk.CTkScrollableFrame(content, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        form_frame = ctk.CTkFrame(
            scroll,
            fg_color=self.colors['card_bg'],
            corner_radius=14,
            border_width=1,
            border_color=COLORS['border'],
            width=920
        )
        form_frame.pack(fill="x", expand=True, padx=24, pady=10)

        # ── Datos personales ───────────────────────────
        self._section_label(form_frame, t("datos_personales"), color)
        self._add_fields_grid(form_frame, CAMPOS_COMUNES, columns=2)

        # ── Datos por rol ──────────────────────────────
        campos_rol = CAMPOS_POR_ROL.get(self.rol_actual, [])
        if campos_rol:
            titulos = {
                "alumno":   t("info_academica"),
                "maestro":  t("info_docente"),
                "personal": t("info_laboral"),
            }

            self._section_label(
                form_frame,
                titulos.get(self.rol_actual, t("datos_personales")),
                color
            )

            self._add_fields_grid(form_frame, campos_rol, columns=2)

        # ── Botón continuar ───────────────────────────
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
        ).pack(pady=(30, 20))

        # ── Restaurar valores ─────────────────────────
        if hasattr(self, 'valores_form') and self.valores_form:
            for key, entry in self.entries.items():
                if key in self.valores_form:
                    try:
                        entry.delete(0, "end")
                        entry.insert(0, self.valores_form[key])
                    except Exception:
                        pass

    # ────────────────────────────────────────────────
    def _section_label(self, parent, text, color):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", pady=(14, 6), padx=12)

        ctk.CTkLabel(
            frame,
            text=text,
            text_color=color,
            font=("Segoe UI", 12, "bold")
        ).pack(anchor="w")

        ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=(3, 0))

    # ────────────────────────────────────────────────
    def _add_fields_grid(self, parent, fields, columns=2):
        grid = ctk.CTkFrame(parent, fg_color="transparent")
        grid.pack(fill="x", padx=12, pady=(0, 6))

        for col in range(columns):
            grid.grid_columnconfigure(col, weight=1, uniform="form_col")

        for idx, (label_text, key, required) in enumerate(fields):
            row = idx // columns
            col = idx % columns
            self._add_entry(grid, label_text, key, required, row, col)

    # ────────────────────────────────────────────────
    def _add_entry(self, parent, label_text, key, required, row, col):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.grid(row=row, column=col, sticky="ew", padx=8, pady=6)

        # TRADUCCIÓN AQUÍ
        texto_label = t(label_text)

        ctk.CTkLabel(
            frame,
            text=texto_label + (" *" if required else ""),
            text_color=self.colors['text_dark'],
            font=("Segoe UI", 11),
            anchor="w"
        ).pack(anchor="w", pady=(0, 4))

        # ── Inputs ─────────────────────────────
        if key == "fechaNacimientoUsuario":

            hoy = datetime.now()
            fecha_maxima = hoy.replace(year=hoy.year - 17)
            
            entry = DateEntry(
                frame,
                date_pattern='dd-mm-yyyy',
                maxdate=fecha_maxima,
                font=("Segoe UI", 11),
                state="readonly"
            )
            entry.pack(fill="x", expand=True)
            entry.bind("<Key>", lambda e: "break")
            entry.bind("<Control-v>", lambda e: "break")
            entry.bind("<Control-V>", lambda e: "break")
            entry.bind("<Button-1>", self._bloquear_click_fecha, add="+")
            entry.bind("<Double-Button-1>", self._bloquear_click_fecha, add="+")

        elif key == "tipoSangreUsuario":
            entry = ttk.Combobox(
                frame,
                values=["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-", "Desconocido"],
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
        self.entries[key].label = label_text  

    def _bloquear_click_fecha(self, event):
        try:
            widget = event.widget
            ancho = widget.winfo_width() or 0
            # Solo permitimos clic en el tramo derecho donde está la flecha.
            if ancho and event.x < max(0, ancho - 30):
                return "break"
        except Exception:
            return "break"
        return None

    # ────────────────────────────────────────────────
    def _validar_y_continuar(self):

        import re

        requeridos = {
            'nombreUsuario': 'nombre',
            'apellidoPaternoUsuario': 'apellido_paterno',
            'matriculaUsuario': 'matricula',
            'telefonoUsuario': 'telefono',
            'correoUsuario': 'correo',
            'tipoSangreUsuario': 'tipo_sangre',
        }

        # ─────────────────────────────
        # 1. VALIDAR CAMPOS BÁSICOS
        # ─────────────────────────────
        for key, nombre_clave in requeridos.items():
            entry = self.entries.get(key)
            valor = entry.get().strip()

            if not valor:
                messagebox.showwarning(
                    t("campo_requerido"),
                    f"{t('campo_requerido')}: {t(nombre_clave)}"
                )
                return

            if key != "tipoSangreUsuario" and len(valor) < 3:
                messagebox.showwarning(
                    "Error",
                    f"{t(nombre_clave)} debe tener mínimo 3 caracteres"
                )
                return

        # ─────────────────────────────
        # 2. VALIDAR CAMPOS POR ROL
        # ─────────────────────────────
        for _, key, required in CAMPOS_POR_ROL.get(self.rol_actual, []):
            entry = self.entries.get(key)
            valor = entry.get().strip()
            label = t(entry.label)

            if required and not valor:
                messagebox.showwarning(
                    t("campo_requerido"),
                    f"{t('campo_requerido')}: {label}"
                )
                return
            sin_minimo = {"gradoImpartidoMaestro", "gradoAlumno", "grupoAlumno"}
            if required and key not in sin_minimo and len(valor) < 3:
                messagebox.showwarning(
                    "Error",
                    t("campo_min_caracteres").format(campo=label, min=3)
                )
                return

        # ─────────────────────────────
        # 3. VALIDAR FORMATO
        # ─────────────────────────────

        # Matrícula
        matricula = self.entries.get('matriculaUsuario').get().strip()
        if not matricula.isdigit():
            messagebox.showwarning("Error", t("matricula_num"))
            return
        longitud_matricula = 8 if self.rol_actual == "alumno" else 6
        if len(matricula) != longitud_matricula:
            messagebox.showwarning(
                "Error",
                t("matricula_longitud").format(n=longitud_matricula)
            )
            return

        #  Teléfono
        telefono = self.entries.get('telefonoUsuario').get().strip()
        if not telefono.isdigit():
            messagebox.showwarning("Error", t("telefono_num"))
            return
        if len(telefono) < 10:
            messagebox.showwarning("Error", t("telefono_min"))
            return
        if len(telefono) > 13:
            messagebox.showwarning("Error", t("telefono_max"))
            return

        # Correo
        correo = self.entries.get('correoUsuario').get().strip()
        if not re.match(r"^[^@]+@[a-zA-Z]{3,}\.[a-zA-Z]{2,}$", correo):
            messagebox.showwarning(
                "Error",
                t("correo_invalido")
            )
            return
        
        #  Nombre y apellido
        regex_nombre = r"^[A-Za-zÁÉÍÓÚáéíóúÑñ\s]+$"

        nombre = self.entries.get('nombreUsuario').get().strip()
        apellido = self.entries.get('apellidoPaternoUsuario').get().strip()

        if not re.match(regex_nombre, nombre):
            messagebox.showwarning("Error", t("nombre_invalido"))
            return

        if not re.match(regex_nombre, apellido):
            messagebox.showwarning("Error", t("apellido_invalido"))
            return


        # ─────────────────────────────
        # 4. VALIDACIONES EN BASE DE DATOS
        # ─────────────────────────────
        conn = get_db()

        if not conn:
            messagebox.showerror("Error", "No se pudo conectar a la base de datos")
            return

        try:
            if sp_existe_correo(conn, correo):
                messagebox.showwarning("Error", t("correo_existe"))
                return

            if sp_existe_telefono(conn, telefono):
                messagebox.showwarning("Error", t("telefono_existe"))
                return

            if sp_existe_matricula(conn, matricula):
                messagebox.showwarning("Error", t("matricula_existe"))
                return

        finally:
            conn.close()

        # ─────────────────────────────
        # 5. TODO CORRECTO
        # ─────────────────────────────
        self.valores_form = {k: e.get().strip() for k, e in self.entries.items()}
        self._camara_lista = False
        self._mostrar_animacion_camara()