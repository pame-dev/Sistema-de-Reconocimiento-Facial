import threading
import time
import cv2
from PIL import Image, ImageTk
import os
from camera import Camera

from idiomas import t

from views.font_scale import FontScale


class CameraMainMixin:
    def _toggle_camera(self):
        if self._cam_running:
            self._stop_camera()
        else:
            self._start_camera()

    def _start_camera(self):
        if self._cam_running or not self._engine:
            return
        self.disable_top_controls()
        self._anim_running = True
        self._btn_iniciar.configure(state="disabled")
        self._anim_btn()
        self._anim_cam_lista = True
        self._mostrar_anim_camara()

    def _abrir_camara(self):
        try:
            self._cap = Camera()
            self._cap.start()
        except Exception:
            self._lbl_cam.configure(
                text="⬤  Error: No se pudo abrir cámara",
                text_color=self.colors['danger'])
            self._anim_running = False
            self._btn_iniciar.configure(text=t("iniciar"), fg_color="#16a34a", state="normal")
            return

        self._cam_running = True
        self._cam_thread  = threading.Thread(target=self._cam_loop, daemon=True)
        self._cam_thread.start()

        self._anim_running = False
        self._btn_iniciar.configure(text=t("detener"), fg_color="#dc2626", hover_color="#b91c1c", state="normal")
        self._lbl_cam.configure(text=t("camara_on"), text_color=self.colors['primary'])

    def _stop_camera(self):
        self._cam_running   = False
        self._anim_running  = False
        self._frame_pending = False
        if self._cap:
            try:
                self._cap.stop()
            except Exception:
                pass
            self._cap = None
        try:
            self._btn_iniciar.configure(text=t("iniciar"), fg_color="#16a34a", hover_color="#15803d", state="normal")
            self._lbl_cam.configure(text=t("camara_off"), text_color=self.colors['danger'])
        except Exception:
            pass
        self.enable_top_controls()
        try:
            self.main_frame.after(100, self._draw_placeholder)
        except Exception:
            pass

    def _cam_loop(self):
        sin_frame_count = 0
        while self._cam_running:
            if not self._cap:
                break
            try:
                frame = self._cap.read()
                if frame is None:
                    sin_frame_count += 1
                    if sin_frame_count == 45:
                        self.main_frame.after(0, lambda: self._lbl_cam.configure(
                            text="⬤  Cámara no detectada...",
                            text_color=self.colors['accent']))
                    time.sleep(0.02)
                    continue
                sin_frame_count = 0
            except Exception:
                break

            frame = self._engine.procesar_frame(frame)

            if not self._frame_pending:
                self._frame_pending = True
                self.main_frame.after(0, self._show_frame, frame.copy())

        self._cam_running = False

    def _show_frame(self, frame_bgr):
        try:
            rgb   = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            img   = Image.fromarray(rgb)
            cw    = self._cam_canvas.winfo_width()  or 640
            ch    = self._cam_canvas.winfo_height() or 480
            img   = img.resize((cw, ch), Image.BILINEAR)
            photo = ImageTk.PhotoImage(img)
            self._cam_canvas.delete("all")
            self._cam_photo = photo
            self._cam_canvas.create_image(0, 0, anchor="nw", image=photo)
        except Exception:
            pass
        finally:
            self._frame_pending = False

    def _draw_placeholder(self):
        if self._cam_running:
            return
        c = self.colors
        try:
            self._cam_canvas.delete("all")
            w = self._cam_canvas.winfo_width()  or 600
            h = self._cam_canvas.winfo_height() or 400
            self._cam_canvas.configure(bg=c['cam_bg'])
            self._cam_canvas.create_rectangle(20, 20, w-20, h-20,
                outline=c['cam_border'], width=2, dash=(8, 4))
            sz = 20
            for (cx2, cy2), (dx, dy) in [
                ((20, 20),     ( 1,  1)),
                ((w-20, 20),   (-1,  1)),
                ((20, h-20),   ( 1, -1)),
                ((w-20, h-20), (-1, -1)),
            ]:
                self._cam_canvas.create_line(cx2, cy2, cx2+dx*sz, cy2,        fill=c['info'], width=3)
                self._cam_canvas.create_line(cx2, cy2, cx2, cy2+dy*sz,        fill=c['info'], width=3)
            try:
                if not hasattr(self, "_placeholder_logo") or self._placeholder_logo is None:
                    logo_path = os.path.join(os.path.dirname(__file__), "..", "assets",
                                             "sentinelSystemIconoo.png")
                    img = Image.open(logo_path).resize((100, 100), Image.LANCZOS)
                    self._placeholder_logo = ImageTk.PhotoImage(img)
                self._cam_canvas.create_image(w//2, h//2 - 28, image=self._placeholder_logo)
                self._cam_canvas.create_text(w//2, h//2 + 24,
                    text="UnimoraAccess", font=("Segoe UI", 22, "bold"), fill=c['info'])
            except Exception:
                self._cam_canvas.create_text(w//2, h//2 - 22,
                    text="🛡  UnimoraAccess", font=("Segoe UI", 22, "bold"), fill=c['info'])
            self._cam_canvas.create_text(w//2, h//2 + 48,
                text=t("presiona_iniciar"), font=("Segoe UI", 16), fill=c['text_gray'])
        except Exception:
            pass