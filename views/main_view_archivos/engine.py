import tkinter as tk
import customtkinter as ctk
import os
import sys
import threading
import time
import cv2
from datetime import datetime
from camera import Camera
from config import COLORS, get_colors, toggle_theme, SIDEBAR_WIDTH, HEADER_HEIGHT, get_db
from views.nuevo_registro_view import NuevoRegistroView
from views.informacion_escolar_view import InformacionEscolarView
from views.historial_accesos_view import HistorialAccesosView
from PIL import Image, ImageTk
from tkinter import messagebox
from idiomas import t, cambiar_idioma

from views.font_scale import FontScale


class EngineMixin:
    def _init_engine(self):
        ok = self._engine.cargar_o_reentrenar()
        n  = len(self._engine.nombres) if ok else 0
        try:
            if ok:
                self.main_frame.after(0, lambda: self._lbl_cam.configure(
                    text=f"⬤  Modelo listo · {n} usuarios",
                    text_color=self.colors['primary']))
            else:
                self.main_frame.after(0, lambda: self._lbl_cam.configure(
                    text="⬤  Sin datos — registra usuarios primero",
                    text_color=self.colors['accent']))
        except Exception:
            pass
    
    def _cb_resultado(self, nombre, confianza, tipo, distancia=None):
        es_aceptado = (tipo == "aceptado")
        color_borde = "#16a34a" if es_aceptado else "#dc2626"

        def _actualizar():
            try:
                self._cancelar_reset_por_ausencia()
                self._animar_borde(color_borde)

                # Beep — solo Windows
                try:
                    import winsound
                    winsound.Beep(1000, 200) if es_aceptado else winsound.Beep(400, 500)
                except Exception:
                    pass

                datos_bd = self._get_datos_usuario(nombre)
                self._construir_panel_usuario(nombre, datos_bd, tipo, confianza, distancia)

            except Exception as e:
                print(f"Error en _cb_resultado: {e}")

        self.main_frame.after(0, _actualizar)

    def _cb_status(self, texto):
        try:
            self.main_frame.after(0, lambda: self._lbl_cam.configure(
                text=f"⬤  {texto}", text_color=self.colors['info']))
        except Exception:
            pass

    def _cb_sin_cara(self):
        self.main_frame.after(0, self._programar_reset_por_ausencia)

    # ── Datos completos del usuario desde BD ──────────────────────────────────
    def _get_datos_usuario(self, nombre_completo):
        datos = {'rol': 'usuario', 'nombre_display': nombre_completo}
        try:
            conn = get_db()
            if not conn:
                return datos
            cur = conn.cursor()

            cur.execute("""
                SELECT u.idUsuario,
                       u.nombreUsuario, u.apellidoPaternoUsuario, u.apellidoMaternoUsuario,
                       u.matriculaUsuario, u.telefonoUsuario, u.correoUsuario, u.rolUsuario
                FROM usuarios u
                WHERE UPPER(u.nombreUsuario || ' ' || COALESCE(u.apellidoPaternoUsuario,''))
                      = UPPER(?)
                LIMIT 1
            """, (nombre_completo.strip(),))
            row = cur.fetchone()

            if not row:
                partes = nombre_completo.strip().split()
                primer = partes[0] if partes else nombre_completo
                cur.execute("""
                    SELECT u.idUsuario,
                           u.nombreUsuario, u.apellidoPaternoUsuario, u.apellidoMaternoUsuario,
                           u.matriculaUsuario, u.telefonoUsuario, u.correoUsuario, u.rolUsuario
                    FROM usuarios u
                    WHERE UPPER(u.nombreUsuario) = UPPER(?)
                    LIMIT 1
                """, (primer,))
                row = cur.fetchone()

            if not row:
                conn.close()
                return datos

            user_id = row[0]
            rol     = row[7] or 'usuario'
            nombre  = row[1] or ''
            paterno = row[2] or ''
            materno = row[3] or ''

            datos = {
                'id':             user_id,
                'nombre':         nombre,
                'paterno':        paterno,
                'materno':        materno,
                'nombre_display': f"{nombre} {paterno} {materno}".strip(),
                'matricula':      row[4] or '—',
                'telefono':       row[5] or '—',
                'correo':         row[6] or '—',
                'rol':            rol,
            }

            if rol == 'alumno':
                cur.execute("""
                    SELECT facultadAlumno, carreraAlumno, gradoAlumno, grupoAlumno
                    FROM alumnos WHERE fkIdUsuario = ?
                """, (user_id,))
                r = cur.fetchone()
                if r:
                    datos.update({'facultad': r[0] or '—', 'carrera': r[1] or '—',
                                  'grado': r[2] or '—', 'grupo': r[3] or '—'})
            elif rol == 'maestro':
                cur.execute("""
                    SELECT gradoImpartidoMaestro, materiaImpartidaMaestro
                    FROM maestros WHERE fkIdUsuario = ?
                """, (user_id,))
                r = cur.fetchone()
                if r:
                    datos.update({'grado': r[0] or '—', 'materia': r[1] or '—'})
            elif rol == 'personal':
                cur.execute("""
                    SELECT puestoPersonalEscolar, areaPersonalEscolar
                    FROM personal_escolar WHERE fkIdUsuario = ?
                """, (user_id,))
                r = cur.fetchone()
                if r:
                    datos.update({'puesto': r[0] or '—', 'area': r[1] or '—'})

            conn.close()
        except Exception as e:
            print(f"Error _get_datos_usuario: {e}")
        return datos