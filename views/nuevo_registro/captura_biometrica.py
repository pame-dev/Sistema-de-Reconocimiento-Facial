# views/captura_biometrica.py
import os
import time
import threading
import hashlib
from datetime import datetime

import cv2
import numpy as np
import tkinter as tk
from tkinter import messagebox, ttk
from PIL import Image, ImageTk
import customtkinter as ctk

from camera import Camera
from config import COLORS, get_colors, get_db
from idiomas import t
from admin.biometric_system.reconocimiento import ReconocerFacial
from views.nuevo_registro.constants import (
    ROL_CONFIG, POSTURAS, TOTAL_FOTOS,
    FRAMES_ESTABLE, CAPTURE_DELAY, haar_path,
)
from database.queries import (
    sp_insertar_usuario,
    sp_insertar_alumno,
    sp_insertar_maestro,
    sp_insertar_personal,
    sp_insertar_biometria,
    sp_restaurar_usuario,
)


class CapturaBiometricaMixin:
    """
    Mixin que añade la pantalla de captura biométrica (Paso 4).
    Requiere: self.container, self.colors, self.rol_actual, self.valores_form,
    self.camara, self.capturando, self._limpiar_container(),
    self._mostrar_seleccion_rol(), self._mostrar_formulario().
    También espera que la clase base inicialice los detectores Haar.
    """

    _CAPTURA_SMALL_BREAKPOINT = 900
    # Perfil balanceado en pantalla pequeña: más espacio para la guía.
    _CAPTURA_SMALL_CAM_RATIO = 0.22
    _CAPTURA_SMALL_CAM_MIN_H = 140
    _CAPTURA_SMALL_CAM_MAX_H = 180
    _CAPTURA_SMALL_GUIA_MIN_H = 220

    # ── Pantalla principal de captura ─────────────────────────────────────────
    def _mostrar_captura(self):
        self._anim_activa = False
        self._limpiar_container()
        self._reset_estado_captura()

        cfg   = ROL_CONFIG[self.rol_actual]
        color = cfg["color"]
        c     = self.colors

        header = ctk.CTkFrame(self.container, fg_color="transparent")
        header.pack(fill="x", pady=(0, 8))
        ctk.CTkButton(header, text="← " + t("volver_formulario"),
                      fg_color='#16A34A', hover_color="#15803D",
                      text_color="#ffffff",
                      font=("Segoe UI", 8, "bold"),
                      corner_radius=8, height=32,
                      command=self._volver_formulario).pack(side="left")
        ctk.CTkLabel(header,text=t("paso_captura"),
                     font=("Segoe UI", 8),
                     text_color=c['text_gray']).pack(side="left", padx=15)

        ttk.Separator(self.container, orient="horizontal").pack(fill="x", pady=(0, 8))

        prog_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        prog_frame.pack(fill="x", padx=4, pady=(0, 6))
        self.bar_total_ctk = ctk.CTkProgressBar(prog_frame, height=12,
                                                  corner_radius=6,
                                                  progress_color=color,
                                                  fg_color=COLORS['border'])
        self.bar_total_ctk.set(0)
        self.bar_total_ctk.pack(fill="x", padx=8)

        body = ctk.CTkFrame(self.container, fg_color="transparent")
        body.pack(fill="both", expand=True)
        self._captura_body = body

        self.panel_guia = ctk.CTkFrame(body, fg_color=c['card_bg'],
                width=340, height=600, corner_radius=12,
                        border_width=1, border_color=COLORS['border'])
        self.panel_guia.pack(side="left", fill="y", padx=(0, 10))
        self.panel_guia.pack_propagate(False)

        # Columna que agrupa cámara arriba y controles (estado+botones) abajo
        cam_column = ctk.CTkFrame(body, fg_color="transparent")
        cam_column.pack(side="left", fill="both", expand=True)
        self._captura_cam_column = cam_column

        cam_panel = ctk.CTkFrame(cam_column, fg_color=c['card_bg'],
                      corner_radius=12, border_width=1,
                      border_color=COLORS['border'])
        cam_panel.pack(side="top", fill="both", expand=True)
        self._captura_cam_panel = cam_panel

        # Controles (estado, subestado, botones) en una sección separada
        controls_frame = ctk.CTkFrame(cam_column, fg_color="transparent")
        controls_frame.pack(side="top", fill="x")
        self._captura_controls = controls_frame

        self.video_label = tk.Label(cam_panel, bg=COLORS['content_bg'])
        self.video_label.pack(fill="both", expand=True, padx=8, pady=(8, 4))

        self.bar_postura_ctk = ctk.CTkProgressBar(self._captura_cam_panel, height=8,
                                corner_radius=4,
                                progress_color=color,
                                fg_color=COLORS['border'])
        self.bar_postura_ctk.set(0)
        self.bar_postura_ctk.pack(fill="x", padx=8, pady=(0, 4))
        estado_panel = ctk.CTkFrame(self._captura_controls, fg_color=c['content_bg'], corner_radius=8)
        estado_panel.pack(fill="x", padx=6, pady=(2, 2))

        self.lbl_estado = ctk.CTkLabel(estado_panel,
                text=t("iniciando_camara_estado"),
                font=("Segoe UI", 13, "bold"),
                text_color=c['text_gray'])
        self.lbl_estado.pack(pady=(2, 0))

        self.lbl_sub_estado = ctk.CTkLabel(estado_panel, text="",
                    font=("Segoe UI", 10),
                    text_color=c['text_gray'])
        self.lbl_sub_estado.pack(pady=(0, 2))

        btn_row = ctk.CTkFrame(estado_panel, fg_color="transparent")
        btn_row.pack(fill="x", padx=4, pady=(2, 2))

        self._btn_pausar = ctk.CTkButton(btn_row, text=t("pausar"),
                  fg_color=c['accent'], hover_color="#D97706",
                  text_color="#ffffff",
                  font=("Segoe UI", 10, "bold"),
                  corner_radius=6, height=26, width=86,
                  command=self._toggle_pausa)
        self._btn_pausar.pack(side="right", padx=(4, 0))

        ctk.CTkButton(btn_row, text=t("cancelar"),
              fg_color="#DC2626", hover_color="#B91C1C",
              text_color="#ffffff",
              font=("Segoe UI", 10, "bold"),
              corner_radius=6, height=26, width=86,
              command=self._cancelar_captura).pack(side="right", padx=(0, 4))

        self._setup_captura_responsive()

        self._construir_panel_guia(color)
        self._precache_engines_duplicado()
        self._disable_top_controls()
        self._iniciar_camara_auto()

    def _setup_captura_responsive(self):
        # Evita registrar múltiples handlers al volver a abrir la vista de captura.
        bind_id = getattr(self, "_captura_resize_bind_id", None)
        if bind_id:
            try:
                self.container.unbind("<Configure>", bind_id)
            except Exception:
                pass

        self._captura_layout_vertical = None
        self._captura_resize_bind_id = self.container.bind(
            "<Configure>", self._on_captura_container_resize, add="+"
        )

        try:
            self.container.update_idletasks()
            width = self.container.winfo_width()
        except Exception:
            width = 0
        self._apply_captura_layout(width)

    def _on_captura_container_resize(self, event):
        if event.widget is not self.container:
            return
        self._apply_captura_layout(event.width)

    def _apply_captura_layout(self, width):
        body = getattr(self, "_captura_body", None)
        cam_panel = getattr(self, "_captura_cam_panel", None)
        cam_column = getattr(self, "_captura_cam_column", None)
        panel_guia = getattr(self, "panel_guia", None)

        if not body or not cam_panel or not panel_guia:
            return
        if not (body.winfo_exists() and cam_panel.winfo_exists() and panel_guia.winfo_exists()):
            return

        small = width < self._CAPTURA_SMALL_BREAKPOINT
        if small == getattr(self, "_captura_layout_vertical", None):
            return

        try:
            if cam_column and cam_column.winfo_exists():
                cam_column.pack_forget()
            panel_guia.pack_forget()
        except Exception:
            pass

        if small:
            # Pantalla compacta: cámara arriba, guía de posturas abajo.
            try:
                body_h = body.winfo_height() or self.container.winfo_height() or 640
            except Exception:
                body_h = 640

            cam_h = int(body_h * self._CAPTURA_SMALL_CAM_RATIO)
            cam_h = max(self._CAPTURA_SMALL_CAM_MIN_H, min(self._CAPTURA_SMALL_CAM_MAX_H, cam_h))
            if cam_panel:
                cam_panel.configure(height=cam_h)
                cam_panel.pack_propagate(False)
            if cam_column:
                cam_column.pack(side="top", fill="x", expand=False, pady=(0, 8))

            panel_guia.configure(width=0)
            panel_guia.pack(side="top", fill="x", expand=False, padx=(0, 0), pady=(0, 0))
            panel_guia.pack_propagate(True)
        else:
            panel_guia.configure(width=260)
            panel_guia.pack(side="left", fill="y", padx=(0, 10), pady=(0, 0))
            panel_guia.pack_propagate(False)
            if cam_panel:
                cam_panel.configure(height=0)
                cam_panel.pack_propagate(True)
            if cam_column:
                cam_column.pack(side="left", fill="both", expand=True, pady=(0, 0))

        self._captura_layout_vertical = small

    def _precache_engines_duplicado(self):
        # Precarga en segundo plano para que la alerta de inactivos no llegue tarde.
        def _warmup():
            try:
                self._obtener_engine_duplicados()
            except Exception:
                pass
            try:
                self._obtener_engine_inactivos()
            except Exception:
                pass

        threading.Thread(target=_warmup, daemon=True).start()

    def _reset_estado_captura(self):
        self.fotos_temp           = []
        self.postura_idx          = 0
        self.fotos_postura        = 0
        self.posturas_completadas = []
        self._auto_activo         = False
        self._frames_con_cara     = 0
        self._ultima_captura      = 0.0
        self._countdown           = 0
        self._guardando           = False
        self._pausado             = False
        self._ultima_muestra_gray = None
        if self._countdown_job:
            try:
                self.container.after_cancel(self._countdown_job)
            except Exception:
                pass
            self._countdown_job = None

    # ── Panel guía ────────────────────────────────────────────────────────────
    def _construir_panel_guia(self, color):
        for w in self.panel_guia.winfo_children():
            w.destroy()

        postura = POSTURAS[self.postura_idx]
        c       = self.colors
        small_layout = bool(getattr(self, "_captura_layout_vertical", False))
        try:
            guia_h = self.panel_guia.winfo_height()
        except Exception:
            guia_h = 0
        compact = small_layout or (0 < guia_h < self._CAPTURA_SMALL_GUIA_MIN_H + 40)

        titulo_font = ("Segoe UI", 10 if compact else 13, "bold")
        text_font = ("Segoe UI", 8 if compact else 10)
        img_size = 160 if compact else 280
        wrap_title = 260 if compact else 320
        wrap_info = 220 if compact else 300
        side_pad = 2 if compact else 6

        # Estructura: imagen (izq) | información y lista de posturas (der)
        top_frame = ctk.CTkFrame(self.panel_guia, fg_color="transparent")
        top_frame.pack(fill="x", pady=(2 if compact else 8, 2))

        img_frame = ctk.CTkFrame(top_frame, fg_color="transparent", width=img_size)
        img_frame.pack(side="left", padx=(0, 4))
        img_frame.pack_propagate(False)

        info_frame = ctk.CTkFrame(top_frame, fg_color="transparent")
        info_frame.pack(side="left", fill="both", expand=True, padx=(0, max(0, side_pad-2)))

        # Título e instrucción en la columna derecha (más compactos)
        ctk.CTkLabel(info_frame,
                 text=f"{t('postura')} {self.postura_idx + 1} / {len(POSTURAS)}",
                 font=text_font, text_color=c['text_gray']).pack(anchor="w", pady=(0, 0))
        ctk.CTkLabel(info_frame, text=t(postura["titulo"]),
                 font=titulo_font,
                 text_color=color, wraplength=wrap_title, justify="left").pack(anchor="w", pady=(0, 0))

        # Imagen en la columna izquierda
        img_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), postura["imagen"])
        img_loaded = False
        if os.path.exists(img_path):
            try:
                img = Image.open(img_path).resize((img_size, img_size), Image.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                lbl_img = tk.Label(img_frame, image=photo, bg=COLORS['card_bg'])
                lbl_img.image = photo
                lbl_img.pack(expand=True, pady=1, padx=(0, 0))
                img_loaded = True
            except Exception:
                img_loaded = False
        if not img_loaded:
            ctk.CTkLabel(img_frame, text=postura["icono"],
                         font=("Segoe UI Emoji", 22 if compact else 54)).pack(expand=True, pady=1, padx=(0, 0))

        # Lista compacta de posturas a la derecha, debajo de título/instrucción
        list_frame = ctk.CTkFrame(info_frame, fg_color="transparent")
        list_frame.pack(fill="both", expand=True)

        # Separador visual
        ctk.CTkFrame(self.panel_guia, fg_color=COLORS['border'],
                     height=1, corner_radius=0).pack(fill="x", padx=max(4, side_pad-2), pady=1)

        # Dos columnas: main_col (frente/izquierda/derecha) y side_col (perfiles)
        main_col = ctk.CTkFrame(list_frame, fg_color="transparent")
        side_col = ctk.CTkFrame(list_frame, fg_color="transparent")

        list_frame.grid_columnconfigure(0, weight=1)
        list_frame.grid_columnconfigure(1, weight=0)

        main_col.grid(row=0, column=0, sticky="nsew")
        side_col.grid(row=0, column=1, sticky="nsew", padx=(2, 0))

        list_padx = max(0, side_pad-2)
        for i, p in enumerate(POSTURAS):
            if i in self.posturas_completadas:
                icono, fg = "✅", COLORS['primary']
            elif i == self.postura_idx:
                icono, fg = "▶", color
            else:
                icono, fg = "○", COLORS['text_gray']

            target = side_col if p.get('id') in ("perfil_izq", "perfil_der") else main_col
            ctk.CTkLabel(target,
                         text=f"{icono} {t(p['titulo'])}",
                         font=text_font,
                         text_color=fg, anchor="w").pack(fill="x", padx=1, pady=(0, 0))

    # ── Cámara y detección ────────────────────────────────────────────────────
    def _iniciar_camara_auto(self):
        try:
            self.camara = Camera()
            self.camara.start()
            time.sleep(0.8)
            self.capturando   = True
            self._auto_activo = True
            self._iniciar_countdown()
        except Exception as e:
            self._set_estado(t("error_iniciar_camara"), str(e), "danger")

    def _iniciar_countdown(self):
        self._countdown = 3
        self._set_estado(
            f"📷 {t('preparate_postura')} {POSTURAS[self.postura_idx]['titulo']}",
            f"{t('comenzando_en')} {self._countdown}...", "info")
        self._tick_countdown()

    def _tick_countdown(self):
        if not self.capturando:
            return
        if self._countdown > 0:
            self._set_sub(f"{t('comenzando_en')} {self._countdown}...")
            self._countdown -= 1
            self._countdown_job = self.container.after(900, self._tick_countdown)
        else:
            self._set_sub(t("manten_posicion"))
            self._auto_activo = True
            self._actualizar_video()

    def _toggle_pausa(self):
        self._pausado = not self._pausado
        if self._pausado:
            self._btn_pausar.configure(text=t("reanudar"), fg_color=COLORS['primary'])
            self._set_estado(t("pausado"), t("presiona_reanudar"), "gray")
        else:
            self._btn_pausar.configure(text=t("pausar"), fg_color=self.colors['accent'])
            self._set_estado(t("reanudando"), "", "info")

    def _filtrar_caras(self, caras, frame_shape):
        h_f, w_f = frame_shape[:2]
        area_min = (w_f * 0.10) * (h_f * 0.10)
        resultado = []
        for (x, y, w, h) in caras:
            if w * h < area_min:
                continue
            if x < 8 or y < 8 or (x + w) > w_f - 8:
                continue
            resultado.append((x, y, w, h))
        return resultado

    def _detectar_cara(self, frame, gray, postura_id):
        PARAMS = {
            "frontal":    dict(scaleFactor=1.1,  minNeighbors=7, minSize=(90, 90)),
            "izquierda":  dict(scaleFactor=1.05, minNeighbors=5, minSize=(70, 70)),
            "derecha":    dict(scaleFactor=1.05, minNeighbors=5, minSize=(70, 70)),
            "perfil_izq": dict(scaleFactor=1.1,  minNeighbors=6, minSize=(70, 70)),
            "perfil_der": dict(scaleFactor=1.1,  minNeighbors=6, minSize=(70, 70)),
        }
        p = PARAMS.get(postura_id, PARAMS["frontal"])

        if postura_id in ("izquierda", "derecha"):
            for det in [self.detector_alt, self.detector_frontal]:
                caras = det.detectMultiScale(gray, **p)
                filtradas = self._filtrar_caras(caras, gray.shape)
                if filtradas:
                    return filtradas
            gray_flip = cv2.flip(gray, 1)
            flip_w    = gray_flip.shape[1]
            for det in [self.detector_alt, self.detector_frontal]:
                caras = det.detectMultiScale(gray_flip, **p)
                if len(caras) > 0:
                    caras = [(flip_w - x - w, y, w, h) for (x, y, w, h) in caras]
                    filtradas = self._filtrar_caras(caras, gray.shape)
                    if filtradas:
                        return filtradas
            return []

        elif postura_id == "perfil_izq":
            gray_flip = cv2.flip(gray, 1)
            caras = self.detector_perfil.detectMultiScale(gray_flip, **p)
            if len(caras) > 0:
                flip_w = gray_flip.shape[1]
                caras  = [(flip_w - x - w, y, w, h) for (x, y, w, h) in caras]
                return self._filtrar_caras(caras, gray.shape)
            return []

        elif postura_id == "perfil_der":
            caras = self.detector_perfil.detectMultiScale(gray, **p)
            if len(caras) > 0:
                return self._filtrar_caras(caras, gray.shape)
            gray_flip = cv2.flip(gray, 1)
            caras = self.detector_perfil.detectMultiScale(gray_flip, **p)
            if len(caras) > 0:
                flip_w = gray_flip.shape[1]
                caras  = [(flip_w - x - w, y, w, h) for (x, y, w, h) in caras]
                return self._filtrar_caras(caras, gray.shape)
            return []

        else:
            caras = self.detector_frontal.detectMultiScale(gray, **p)
            return self._filtrar_caras(caras, gray.shape) if len(caras) > 0 else []

    def _rostro_apto_para_guardar(self, rostro_bgr):
        try:
            gray = cv2.cvtColor(rostro_bgr, cv2.COLOR_BGR2GRAY)
            if float(cv2.Laplacian(gray, cv2.CV_64F).var()) < 40.0:
                return False, t("rostro_borroso")
            brillo = float(np.mean(gray))
            if brillo < 45.0 or brillo > 215.0:
               return False, t("ajusta_iluminacion")
            self._ultima_muestra_gray = gray
            return True, ""
        except Exception:
            return True, ""

    def _obtener_engine_duplicados(self):
        if getattr(self, "_engine_duplicados", None) is None:
            try:
                engine = ReconocerFacial()
                if not engine.cargar_o_reentrenar():
                    self._engine_duplicados = False
                    return None
                self._engine_duplicados = engine
            except Exception:
                self._engine_duplicados = False
                return None
        if self._engine_duplicados is False:
            return None
        return self._engine_duplicados

    def _fingerprint_inactivos(self):
        conn = get_db()
        if not conn:
            return None
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT u.idUsuario, b.encodeBiometria
                FROM usuarios u
                INNER JOIN biometria b ON u.idUsuario = b.fkIdUsuario
                WHERE b.encodeBiometria IS NOT NULL
                  AND LOWER(TRIM(u.estadoUsuario)) = 'inactivo'
                ORDER BY u.idUsuario ASC, b.idBiometria ASC
            """)
            items = []
            for user_id, imagen_bytes in cursor.fetchall():
                if imagen_bytes is None:
                    continue
                items.append((int(user_id), hashlib.md5(imagen_bytes).hexdigest()))
            return tuple(items)
        except Exception:
            return None
        finally:
            conn.close()

    def _obtener_engine_inactivos(self):
        fingerprint = self._fingerprint_inactivos()
        if fingerprint is None:
            self._engine_inactivos = False
            self._engine_inactivos_fp = None
            return None

        if (getattr(self, "_engine_inactivos", None) not in (None, False)
                and self._engine_inactivos_fp == fingerprint):
            return self._engine_inactivos

        conn = get_db()
        if not conn:
            self._engine_inactivos = False
            self._engine_inactivos_fp = fingerprint
            return None

        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    u.idUsuario,
                    u.nombreUsuario,
                    u.apellidoPaternoUsuario,
                    u.apellidoMaternoUsuario,
                    b.encodeBiometria
                FROM usuarios u
                INNER JOIN biometria b ON u.idUsuario = b.fkIdUsuario
                WHERE b.encodeBiometria IS NOT NULL
                  AND LOWER(TRIM(u.estadoUsuario)) = 'inactivo'
                ORDER BY u.idUsuario ASC, b.idBiometria ASC
            """)
            filas = cursor.fetchall()
        except Exception:
            self._engine_inactivos = False
            self._engine_inactivos_fp = fingerprint
            return None
        finally:
            conn.close()

        if not filas:
            self._engine_inactivos = False
            self._engine_inactivos_fp = fingerprint
            return None

        engine = ReconocerFacial()
        faces_tmp = []
        labels_tmp = []
        nombres_tmp = {}

        for fila in filas:
            user_id = int(fila[0])
            nombre_completo = f"{fila[1]} {fila[2] or ''} {fila[3] or ''}".strip()
            nombres_tmp[user_id] = nombre_completo

            imagen_bytes = fila[4]
            if not imagen_bytes:
                continue

            try:
                nparr = np.frombuffer(imagen_bytes, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                if img is None:
                    continue

                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                gray = cv2.equalizeHist(gray)
                caras = engine._detectar_caras(img, gray)
                if len(caras) > 0:
                    x, y, w, h = max(caras, key=lambda item: item[2] * item[3])
                    fh, fw = gray.shape[:2]
                    pad = int(min(w, h) * 0.08)
                    x1 = max(0, x - pad)
                    y1 = max(0, y - pad)
                    x2 = min(fw, x + w + pad)
                    y2 = min(fh, y + h + pad)
                    rostro_gray = gray[y1:y2, x1:x2]
                    if rostro_gray.size == 0:
                        continue
                else:
                    rostro_gray = gray

                rostro_gray = cv2.resize(rostro_gray, (100, 100))
                faces_tmp.append(rostro_gray)
                labels_tmp.append(user_id)

            except Exception:
                continue

        if not faces_tmp:
            self._engine_inactivos = False
            self._engine_inactivos_fp = fingerprint
            return None

        engine.faces = faces_tmp
        engine.labels = labels_tmp
        engine.nombres = nombres_tmp

        try:
            engine.recognizer.train(faces_tmp, np.array(labels_tmp, dtype=np.int32))
            engine._ajustar_tolerancia_post_entreno()
        except Exception:
            self._engine_inactivos = False
            self._engine_inactivos_fp = fingerprint
            return None

        self._engine_inactivos = engine
        self._engine_inactivos_fp = fingerprint
        return engine

    def _detectar_usuario_duplicado(self, rostro_bgr):
        engine = self._obtener_engine_duplicados()
        if engine:
            try:
                user_id, conf = engine._reconocer_rostro(rostro_bgr)
                if user_id != t("desconocido"):
                    if self.modo_retomar_fotos and self.user_id_existente == user_id:
                        return None

                    activo = engine._usuario_activo(user_id)

                    return {
                        "user_id": user_id,
                        "nombre": engine.nombres.get(user_id, t("usuario")),
                        "confianza": conf,
                        "estado": "activo" if activo else "inactivo",
                    }

            except Exception:
                pass

        backup = self._obtener_engine_inactivos()
        if not backup:
            return None

        try:
            user_id, conf = backup._reconocer_rostro(rostro_bgr)
            if user_id == t("desconocido"):
                return None

            if self.modo_retomar_fotos and self.user_id_existente == user_id:
                return None

            return {
                "user_id": user_id,
                "nombre": backup.nombres.get(user_id, t("usuario")),
                "confianza": conf,
                "estado": "inactivo",
            }
        except Exception:
            return None

    def _abrir_alerta_duplicado(self, duplicado):
        if self._alerta_duplicado_abierta:
            return

        self._alerta_duplicado_abierta = True
        self._usuario_duplicado_detectado = duplicado.get("user_id")
        self._detener_camara_silencio()

        win = ctk.CTkToplevel(self.parent)
        es_activo = duplicado.get("estado") == "activo"
        titulo = t("usuario_ya_registrado") if es_activo else t("usuario_inactivo_detectado")
        win.title(titulo)
        win.geometry("460x240")
        win.resizable(False, False)
        win.grab_set()
        win.focus_force()

        def _cerrar():
            self._alerta_duplicado_abierta = False
            try:
                win.destroy()
            except Exception:
                pass

        win.protocol("WM_DELETE_WINDOW", _cerrar)

        c = self.colors
        card = ctk.CTkFrame(win, fg_color=c['background'])
        card.pack(fill="both", expand=True, padx=16, pady=16)

        ctk.CTkLabel(card, text="⚠️", font=("Segoe UI Emoji", 38)).pack(pady=(6, 2))
        ctk.CTkLabel(
            card,
            text=titulo,
            font=("Segoe UI", 16, "bold"),
            text_color=self.colors['text_dark'],
        ).pack(pady=(0, 4))
        ctk.CTkLabel(
            card,
            text=(
                f"{t('se_detecto')}: {duplicado.get('nombre', t('usuario'))}\n"
                + (t("pregunta_editar_usuario") if es_activo
                   else t("pregunta_restaurar_usuario"))
            ),
            font=("Segoe UI", 11),
            text_color=self.colors['text_gray'],
            justify="center",
        ).pack(pady=(0, 16))

        btns = ctk.CTkFrame(card, fg_color="transparent")
        btns.pack(fill="x", padx=8, pady=(0, 4))
        btns.grid_columnconfigure((0, 1), weight=1, uniform="dup")

        def _editar():
            _cerrar()
            self._ir_a_editar_usuario_duplicado(duplicado.get("user_id"))

        def _restaurar():
            _cerrar()
            self._restaurar_usuario_duplicado(duplicado.get("user_id"), duplicado.get("nombre", t("usuario")))

        def _cancelar():
            _cerrar()
            self._cancelar_registro_duplicado()

        primary_text = t("editar_usuario")if es_activo else t("restaurar_usuario")
        primary_color = "#16A34A" if es_activo else "#2563EB"
        primary_hover = "#15803D" if es_activo else "#1D4ED8"

        ctk.CTkButton(
            btns,
            text=primary_text,
            fg_color=primary_color,
            hover_color=primary_hover,
            text_color="#ffffff",
            command=_editar if es_activo else _restaurar,
        ).grid(row=0, column=0, padx=(0, 6), sticky="ew")

        ctk.CTkButton(
            btns,
            text=t("cancelar_registro"),
            fg_color="#DC2626",
            hover_color="#B91C1C",
            text_color="#ffffff",
            command=_cancelar,
        ).grid(row=0, column=1, padx=(6, 0), sticky="ew")

    def _ir_a_editar_usuario_duplicado(self, user_id):
        app = getattr(self.parent.winfo_toplevel(), "sentinel_app", None)
        if not app or not getattr(app, "main_view", None):
            messagebox.showinfo(t("editar_usuario"), t("error_abrir_edicion"))
            self._cancelar_registro_duplicado()
            return

        try:
            app.main_view.show_informacion_escolar(preselect_user_id=user_id)
        except Exception as e:
            messagebox.showerror(t("editar_usuario"), t("error_abrir_edicion"))
            self._cancelar_registro_duplicado()

    def _restaurar_usuario_duplicado(self, user_id, nombre):
        try:
            conn = get_db()
            if not conn:
                raise RuntimeError(t("error_db"))

            sp_restaurar_usuario(conn, user_id)
            conn.commit()
            conn.close()
            self._engine_inactivos = None
            self._engine_inactivos_fp = None
            messagebox.showinfo(t("usuario_restaurado"), t("usuario_restaurado_mensaje").format(nombre))
            self._ir_a_editar_usuario_duplicado(user_id)
        except Exception as e:
            messagebox.showerror(t("restaurar_usuario"), t("error_restaurar_usuario").format(e))
            self._cancelar_registro_duplicado()

    def _cancelar_registro_duplicado(self):
        self._alerta_duplicado_abierta = False
        self._usuario_duplicado_detectado = None
        self._reset_estado_captura()
        self._mostrar_seleccion_rol()

    # ── Loop de video ─────────────────────────────────────────────────────────
    def _actualizar_video(self):
        if not self.capturando or self.camara is None:
            return
        if self._guardando:
            return

        try:
            frame = self.camara.read()
            if frame is None:
                self.video_label.after(30, self._actualizar_video)
                return
        except Exception:
            self.video_label.after(30, self._actualizar_video)
            return

        gray       = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        postura_id = POSTURAS[self.postura_idx]["id"]
        caras      = self._detectar_cara(frame, gray, postura_id)

        cara_detectada = len(caras) > 0
        ahora          = time.time()

        if cara_detectada:
            self._frames_con_cara += 1
            x, y, w, h = max(caras, key=lambda c: c[2] * c[3])
            listo      = self._frames_con_cara >= FRAMES_ESTABLE
            rect_color = (0, 220, 0) if listo else (0, 180, 255)
            cv2.rectangle(frame, (x, y), (x+w, y+h), rect_color, 2)

            if (not self._pausado
                    and self._auto_activo
                    and listo
                    and (ahora - self._ultima_captura) >= CAPTURE_DELAY):

                rostro_bgr = frame[y:y+h, x:x+w]
                rostro_bgr = cv2.resize(rostro_bgr, (200, 200))
                apto, msg = self._rostro_apto_para_guardar(rostro_bgr)
                if not apto:
                    self._set_sub(msg)
                    self.video_label.after(15, self._actualizar_video)
                    return

                duplicado = self._detectar_usuario_duplicado(rostro_bgr)
                if duplicado:
                    self._abrir_alerta_duplicado(duplicado)
                    return

                _, buf = cv2.imencode('.jpg', rostro_bgr,
                                      [cv2.IMWRITE_JPEG_QUALITY, 92])
                self.fotos_temp.append(buf.tobytes())
                self.fotos_postura  += 1
                self._ultima_captura = ahora

                total_fotos    = POSTURAS[self.postura_idx]["fotos"]
                progreso_pos   = self.fotos_postura / total_fotos
                progreso_total = len(self.fotos_temp) / TOTAL_FOTOS

                try:
                    self.bar_postura_ctk.set(progreso_pos)
                    self.bar_total_ctk.set(progreso_total)
                except Exception:
                    pass

                if self.fotos_postura < total_fotos:
                    self._set_estado(
                        f"✅ {t('capturando')} {POSTURAS[self.postura_idx]['titulo']}",
                        f"{t('manten_posicion')} {int(progreso_pos * 100)}%", "ok")
                else:
                    self._postura_completada()
                    return
        else:
            self._frames_con_cara = 0
            if not self._pausado and self._auto_activo:
                self._set_estado(t("no_detecta_cara"), t("acercate_iluminacion"), "warn")
            cv2.putText(frame, t("sin_cara"), (12, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (30, 30, 220), 2)

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h_f, w_f  = frame_rgb.shape[:2]
        try:
            lw = self.video_label.winfo_width()  or 480
            lh = self.video_label.winfo_height() or 360
        except Exception:
            lw, lh = 480, 360
        scale  = min(lw / w_f, lh / h_f, 1.0)
        nw, nh = max(1, int(w_f * scale)), max(1, int(h_f * scale))
        frame_rgb = cv2.resize(frame_rgb, (nw, nh))
        img       = Image.fromarray(frame_rgb)
        imgtk     = ImageTk.PhotoImage(image=img)
        try:
            self.video_label.imgtk = imgtk
            self.video_label.config(image=imgtk)
        except Exception:
            pass

        self.video_label.after(15, self._actualizar_video)

    # ── Ciclo de posturas ─────────────────────────────────────────────────────
    def _postura_completada(self):
        self._auto_activo = False
        self.posturas_completadas.append(self.postura_idx)
        self.bar_postura_ctk.set(1.0)

        if self.postura_idx < len(POSTURAS) - 1:
            siguiente = POSTURAS[self.postura_idx + 1]
            self._set_estado(
                t("postura_completada"),
                f"{t('preparate_para')} {siguiente['titulo']} — {t('cambiando_en_2s')}")
            self.container.after(1800, self._pasar_a_siguiente_postura)
        else:
            self.bar_total_ctk.set(1.0)
            self._set_estado(t("todas_posturas"), t("guardando_auto"), "ok")
            self.container.after(800, self._guardar_automatico)

    def _pasar_a_siguiente_postura(self):
        if not self.capturando:
            return
        self.postura_idx     += 1
        self.fotos_postura    = 0
        self._frames_con_cara = 0
        self._countdown       = 3
        color = ROL_CONFIG[self.rol_actual]["color"]
        self.bar_postura_ctk.set(0)
        self._construir_panel_guia(color)
        postura = POSTURAS[self.postura_idx]
        self._set_estado(
            f"🔄 {t('nueva_postura')} {postura['titulo']}",
            f"Comenzando en {self._countdown}...", "info")
        self._tick_countdown_postura()

    def _tick_countdown_postura(self):
        if not self.capturando:
            return
        if self._countdown > 0:
            self._set_sub(f"{t('comenzando_en')} {self._countdown}...")
            self._countdown -= 1
            self._countdown_job = self.container.after(900, self._tick_countdown_postura)
        else:
            self._set_sub(t("manten_posicion"))
            self._auto_activo = True
            self._actualizar_video()

    # ── Estado UI ─────────────────────────────────────────────────────────────
    def _set_estado(self, texto, subtexto="", tipo="info"):
        COLORES = {
            "ok":     "#16a34a",
            "warn":   "#d97706",
            "danger": "#dc2626",
            "info":   self.colors['info'],
            "gray":   self.colors['text_gray'],
        }
        color = COLORES.get(tipo, self.colors['text_gray'])
        try:
            self.lbl_estado.configure(text=texto, text_color=color)
            self.lbl_sub_estado.configure(text=subtexto, text_color=self.colors['text_gray'])
        except Exception:
            pass

    def _set_sub(self, texto):
        try:
            self.lbl_sub_estado.configure(text=texto)
        except Exception:
            pass

    # ── Guardado en BD ────────────────────────────────────────────────────────
    def _guardar_automatico(self):
        self._guardando = True
        self._detener_camara_silencio()
        threading.Thread(target=self._guardar_en_bd, daemon=True).start()

    def _guardar_en_bd(self):
        try:
            rol = self.rol_actual
            v   = getattr(self, 'valores_form', {})

            def val(key, upper=True):
                texto = v.get(key, "").strip()
                return texto.upper() if upper else texto

            conn  = get_db()
            ahora = datetime.now()

            if self.modo_retomar_fotos:
                user_id = self.user_id_existente
                cursor  = conn.cursor()
                cursor.execute("DELETE FROM biometria WHERE fkIdUsuario = ?", (user_id,))
                for foto_bytes in self.fotos_temp:
                    sp_insertar_biometria(conn, user_id, foto_bytes, ahora)
                conn.commit()
                conn.close()
                self.container.after(0, lambda: self._fin_guardado(
                    t("fotos_actualizadas"),
                    t("se_actualizaron_fotos").format(len(self.fotos_temp))
                ))
                return

            user_id = sp_insertar_usuario(conn, {
                'nombre':    val('nombreUsuario'),
                'paterno':   val('apellidoPaternoUsuario'),
                'materno':   val('apellidoMaternoUsuario'),
                'matricula': val('matriculaUsuario', upper=False),
                'rol':       rol,
                'telefono':  val('telefonoUsuario',  upper=False),
                'correo':    val('correoUsuario',    upper=False),
                'fecha_nacimiento': val('fechaNacimientoUsuario', upper=False),
                'tipo_sangre': val('tipoSangreUsuario', upper=False),
                'direccion': val('direccionUsuario', upper=False)
            })

            if rol == "alumno":
                sp_insertar_alumno(conn, user_id, {
                    'grado':    val('gradoAlumno', upper=False),
                    'grupo':    val('grupoAlumno', upper=False),
                    'facultad': val('facultadAlumno'),
                    'carrera':  val('carreraAlumno'),
                })
            elif rol == "maestro":
                sp_insertar_maestro(conn, user_id, {
                    'grado':   val('gradoImpartidoMaestro', upper=False),
                    'materia': val('materiaImpartidaMaestro'),
                })
            elif rol == "personal":
                sp_insertar_personal(conn, user_id, {
                    'puesto': val('puestoPersonalEscolar'),
                    'area':   val('areaPersonalEscolar'),
                })

            for foto_bytes in self.fotos_temp:
                sp_insertar_biometria(conn, user_id, foto_bytes, ahora)

            conn.commit()
            conn.close()

            # ── Guardar el ID del usuario para posibles reintentosself._user_id_creado = user_id
            cfg             = ROL_CONFIG[rol]
            nombre_completo = f"{val('nombreUsuario')} {val('apellidoPaternoUsuario')}"
            self.container.after(0, lambda: self._fin_guardado(
                t("registro_exitoso"),
                f"{cfg['icono']} {nombre_completo} ({cfg['titulo']})\n"
                f"{t('fotos_registradas')} {len(self.fotos_temp)} {t('fotos')}"
            ))

        except Exception as e:
            self.container.after(0, lambda: messagebox.showerror(
                t("error"), f"{t('error_guardar')} {e}"))
            self._guardando = False

    def _fin_guardado(self, titulo, mensaje):
        self._guardando = False
        self._mostrar_resultado_final(titulo, mensaje)

    def _mostrar_resultado_final(self, titulo, mensaje):
        """Pantalla de resultado final con opciones de Aceptar, Cancelar y Repetir"""
        self._enable_top_controls()
        self._detener_camara_silencio()
        self._limpiar_container()

        c = self.colors
        cfg = ROL_CONFIG[self.rol_actual]
        color = cfg["color"]

        # Container principal centrado
        outer = ctk.CTkFrame(self.container, fg_color="transparent")
        outer.pack(fill="both", expand=True, padx=30, pady=30)

        # Card con el resultado
        card = ctk.CTkFrame(
            outer, fg_color=c['card_bg'], corner_radius=16,
            border_width=2, border_color=color
        )
        card.pack(fill="both", expand=True, padx=20, pady=20)

        # Contenido interior
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=32, pady=32)

        # Título con icono
        header_frame = ctk.CTkFrame(inner, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 20))
        ctk.CTkLabel(
            header_frame,
            text="✅" if "exitoso" in titulo.lower() or "actualizadas" in titulo.lower() else "ℹ️",
            font=("Segoe UI Emoji", 48)
        ).pack(pady=(0, 12))
        ctk.CTkLabel(
            header_frame,
            text=titulo,
            font=("Segoe UI", 20, "bold"),
            text_color=color
        ).pack()

        # Mensaje
        ctk.CTkLabel(
            inner,
            text=mensaje,
            font=("Segoe UI", 12),
            text_color=c['text_dark'],
            wraplength=400,
            justify="center"
        ).pack(fill="x", pady=20)

        # Separador
        ctk.CTkFrame(
            inner, fg_color=COLORS['border'], height=1, corner_radius=0
        ).pack(fill="x", pady=20)

        # Botones
        btn_frame = ctk.CTkFrame(inner, fg_color="transparent")
        btn_frame.pack(fill="x")
        btn_frame.grid_columnconfigure((0, 1), weight=1, uniform="btn")

        # Botón Repetir (izquierda)
        ctk.CTkButton(
            btn_frame,
            text="🔄 " + t("repetir"),
            fg_color="#F59E0B",
            hover_color="#D97706",
            text_color="#ffffff",
            font=("Segoe UI", 12, "bold"),
            corner_radius=8,
            height=40,
            command=self._accion_repetir
        ).grid(row=0, column=0, padx=4, sticky="ew")

        # Botón Aceptar (derecha)
        ctk.CTkButton(
            btn_frame,
            text=t("aceptar"),
            fg_color="#16A34A",
            hover_color="#15803D",
            text_color="#ffffff",
            font=("Segoe UI", 12, "bold"),
            corner_radius=8,
            height=40,
            command=self._accion_aceptar
        ).grid(row=0, column=1, padx=4, sticky="ew")

    def _accion_aceptar(self):
        """Usuario acepta el registro, vuelve a selección de rol"""
        # Limpiar el ID guardado si existe
        self._user_id_creado = None
        self._mostrar_seleccion_rol()

    def _accion_repetir(self):
        """Usuario quiere repetir captura, limpia fotos y vuelve a capturar"""
        # Preparar para actualizar fotos del usuario creado
        if hasattr(self, '_user_id_creado') and self._user_id_creado:
            self.modo_retomar_fotos = True
            self.user_id_existente = self._user_id_creado
        
        # Reiniciar el estado de captura para volver a tomar fotos
        self._reset_estado_captura()
        self._mostrar_captura()

    # ── Helpers cámara ────────────────────────────────────────────────────────
    def _detener_camara_silencio(self):
        self.capturando   = False
        self._auto_activo = False
        if self.camara:
            try:
                self.camara.stop()
            except Exception:
                pass
            self.camara = None

    def _detener_camara(self):
        self._detener_camara_silencio()
        try:
            self.video_label.config(image='')
        except Exception:
            pass

    def _volver_formulario(self):
        self._enable_top_controls()
        self._detener_camara()
        self._mostrar_formulario()

    def _cancelar_captura(self):
        self._enable_top_controls()
        self._detener_camara()
        self._mostrar_seleccion_rol()