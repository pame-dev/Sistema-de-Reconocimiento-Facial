# views/animacion_camara.py
import tkinter as tk
import customtkinter as ctk

from config import COLORS, get_colors
from idiomas import t
from views.nuevo_registro.constants import ROL_CONFIG


class AnimacionCamaraMixin:
    """
    Mixin que añade la pantalla de animación de carga de cámara (Paso intermedio).
    Requiere: self.container, self.colors, self.rol_actual,
    self._limpiar_container(), self._mostrar_captura().
    """

    def _mostrar_animacion_camara(self):
        self._limpiar_container()
        cfg   = ROL_CONFIG[self.rol_actual]
        color = cfg["color"]
        c     = self.colors

        self._anim_activa = True
        self._prog_valor  = 0.0
        self._dots_estado = 0
        self._anim_fase   = 0
        self._anim_radio  = 44
        self._scan_pos    = 0.0

        outer = ctk.CTkFrame(self.container, fg_color="transparent")
        outer.pack(fill="both", expand=True)

        card = ctk.CTkFrame(outer, fg_color=c['card_bg'], corner_radius=18,
                            border_width=1, border_color=COLORS['border'],
                            width=340, height=320)
        card.place(relx=0.5, rely=0.45, anchor="center")
        card.pack_propagate(False)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(expand=True)

        self._cam_canvas = tk.Canvas(inner, width=110, height=110,
                                     bg=c['card_bg'], highlightthickness=0)
        self._cam_canvas.pack(pady=(22, 8))
        self._dibujar_icono_camara(color)

        ctk.CTkLabel(inner, text=t("iniciando_camara"),
                     font=("Segoe UI", 15, "bold"),
                     text_color=c['text_dark']).pack()

        self._dots_label = ctk.CTkLabel(inner, text="",
                                         font=("Segoe UI", 18), text_color=color)
        self._dots_label.pack(pady=2)

        self._prog_anim = ctk.CTkProgressBar(inner, width=220, height=6,
                                              corner_radius=3,
                                              progress_color=color,
                                              fg_color=COLORS['border'])
        self._prog_anim.set(0)
        self._prog_anim.pack(pady=(8, 4))

        self._lbl_sub_anim = ctk.CTkLabel(inner, text=t("preparando_biometria"),
                                           font=("Segoe UI", 10),
                                           text_color=c['text_gray'])
        self._lbl_sub_anim.pack(pady=(0, 20))

        self._tick_anim_dots()
        self._tick_anim_prog()
        self._tick_anim_ring()

        self.container.after(200, self._set_camara_lista)

    def _set_camara_lista(self):
        self._camara_lista = True

    def _dibujar_icono_camara(self, color):
        cv = self._cam_canvas
        cv.delete("all")
        cx, cy = 55, 58
        r = self._anim_radio
        cv.create_oval(cx-r, cy-r, cx+r, cy+r, outline=color, width=2)
        cv.create_rectangle(cx-22, cy-14, cx+22, cy+14, outline=color, width=2, fill="")
        cv.create_oval(cx-9, cy-9, cx+9, cy+9, outline=color, width=1.5, fill="")
        cv.create_oval(cx-4, cy-4, cx+4, cy+4, fill=color, outline="")
        cv.create_rectangle(cx+14, cy-14, cx+22, cy-8, outline=color, width=1.5, fill="")
        scan_y = cy - 12 + int(self._scan_pos * 24)
        cv.create_line(cx-18, scan_y, cx+18, scan_y, fill=color, width=1)

    def _tick_anim_ring(self):
        if not self._anim_activa:
            return
        if self._anim_fase == 0:
            self._anim_radio = min(50, self._anim_radio + 1)
            if self._anim_radio >= 50:
                self._anim_fase = 1
        else:
            self._anim_radio = max(42, self._anim_radio - 1)
            if self._anim_radio <= 42:
                self._anim_fase = 0
        self._scan_pos = (self._scan_pos + 0.06) % 1.0
        color = ROL_CONFIG[self.rol_actual]["color"]
        self._dibujar_icono_camara(color)
        self.container.after(40, self._tick_anim_ring)

    def _tick_anim_dots(self):
        if not self._anim_activa:
            return
        puntos = ["   ", "•  ", "•• ", "•••"]
        self._dots_label.configure(text=puntos[self._dots_estado % 4])
        self._dots_estado += 1
        self.container.after(400, self._tick_anim_dots)

    def _tick_anim_prog(self):
        if not self._anim_activa:
            return
        target = 0.88 if not getattr(self, '_camara_lista', False) else 1.0
        delta  = (target - self._prog_valor) * 0.06
        self._prog_valor = min(target, self._prog_valor + max(delta, 0.003))
        try:
            self._prog_anim.set(self._prog_valor)
        except Exception:
            pass
        if self._prog_valor < 0.999:
            self.container.after(60, self._tick_anim_prog)
        else:
            self.container.after(300, self._mostrar_captura)