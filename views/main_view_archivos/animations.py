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


class AnimationsMixin:
    def _anim_btn(self, step=0):
        if not self._anim_running:
            return
        frames = [
    f"⏳ {t('iniciando')}",
    f"⏳ {t('iniciando')}.",
    f"⏳ {t('iniciando')}..",
    f"⏳ {t('iniciando')}..."
]
        try:
            self._btn_iniciar.configure(text=frames[step % len(frames)], fg_color="#f59e0b")
        except Exception:
            return
        self.main_frame.after(400, self._anim_btn, step + 1)

    def _mostrar_anim_camara(self):
        self._anim_cam_activa   = True
        self._anim_cam_radio    = 44
        self._anim_cam_fase     = 0
        self._anim_cam_scan     = 0.0
        self._anim_cam_dots     = 0
        self._anim_cam_prog     = 0.0
        self._anim_cam_dots_str = "   "
        self._tick_anim_cam_ring()
        self._tick_anim_cam_dots()
        self._tick_anim_cam_prog()

    def _tick_anim_cam_ring(self):
        if not getattr(self, '_anim_cam_activa', False):
            return
        if self._anim_cam_fase == 0:
            self._anim_cam_radio = min(50, self._anim_cam_radio + 1)
            if self._anim_cam_radio >= 50:
                self._anim_cam_fase = 1
        else:
            self._anim_cam_radio = max(42, self._anim_cam_radio - 1)
            if self._anim_cam_radio <= 42:
                self._anim_cam_fase = 0
        self._anim_cam_scan = (self._anim_cam_scan + 0.06) % 1.0
        self._dibujar_anim_camara()
        self.main_frame.after(40, self._tick_anim_cam_ring)

    def _tick_anim_cam_dots(self):
        if not getattr(self, '_anim_cam_activa', False):
            return
        puntos = ["   ", "•  ", "•• ", "•••"]
        self._anim_cam_dots_str = puntos[self._anim_cam_dots % 4]
        self._anim_cam_dots    += 1
        self.main_frame.after(400, self._tick_anim_cam_dots)

    def _tick_anim_cam_prog(self):
        if not getattr(self, '_anim_cam_activa', False):
            return
        target = 1.0
        delta  = (target - self._anim_cam_prog) * 0.06
        self._anim_cam_prog = min(target, self._anim_cam_prog + max(delta, 0.003))
        self._dibujar_anim_camara()
        if self._anim_cam_prog < 0.999:
            self.main_frame.after(60, self._tick_anim_cam_prog)
        else:
            self._anim_cam_activa = False
            self.main_frame.after(200, self._abrir_camara)

    def _dibujar_anim_camara(self):
        try:
            canvas = self._cam_canvas
            canvas.delete("all")
            c  = self.colors
            w  = canvas.winfo_width()  or 640
            h  = canvas.winfo_height() or 480
            cx, cy = w // 2, h // 2 - 40
            color  = c['info']

            r = self._anim_cam_radio
            canvas.create_oval(cx-r, cy-r, cx+r, cy+r, outline=color, width=2)
            canvas.create_rectangle(cx-22, cy-14, cx+22, cy+14, outline=color, width=2, fill="")
            canvas.create_oval(cx-9, cy-9, cx+9, cy+9, outline=color, width=1.5, fill="")
            canvas.create_oval(cx-4, cy-4, cx+4, cy+4, fill=color, outline="")
            canvas.create_rectangle(cx+14, cy-14, cx+22, cy-8, outline=color, width=1.5, fill="")
            scan_y = cy - 12 + int(self._anim_cam_scan * 24)
            canvas.create_line(cx-18, scan_y, cx+18, scan_y, fill=color, width=1)

            dots = self._anim_cam_dots_str
            canvas.create_text(cx, cy + 60,
                text=f"{t('iniciando_camara')} {dots}",
                font=("Segoe UI", 14, "bold"), fill=color)

            bar_w = 220
            bar_x = cx - bar_w // 2
            bar_y = cy + 90
            canvas.create_rectangle(bar_x, bar_y, bar_x+bar_w, bar_y+6,
                fill=c['cam_bg'], outline=c['cam_border'], width=1)
            if self._anim_cam_prog > 0:
                canvas.create_rectangle(bar_x, bar_y,
                    bar_x + int(bar_w * self._anim_cam_prog), bar_y + 6,
                    fill=color, outline="")
            canvas.create_text(cx, bar_y + 22,
                text=t("preparando"), font=("Segoe UI", 10), fill=c['text_gray'])
        except Exception:
            pass