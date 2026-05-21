import os
import sys
import time
import cv2

class Camera:
    """
    read() devuelve un frame en BGR (OpenCV).
    Raspberry Pi: Picamera2 (libcamera)
    Windows: cv2.VideoCapture
    """

    def __init__(self, index: int = 0, size=(640, 480), warmup_frames: int = 5):
        self.index = index
        self.size = size
        self.warmup_frames = warmup_frames
        self.backend = None
        self.cap = None

    def _select_backend(self) -> str:
        force = os.environ.get("CAM_BACKEND", "").strip().lower()
        if force in ("picamera2", "pi", "libcamera"):
            return "picamera2"
        if force in ("opencv", "cv2", "windows"):
            return "opencv"

        # default
        return "picamera2" if sys.platform.startswith("linux") else "opencv"

    def start(self):
        self.backend = self._select_backend()

        if self.backend == "picamera2":
            from picamera2 import Picamera2  # import aquí para que Windows no falle
            self.cap = Picamera2()

            config = self.cap.create_preview_configuration(
                main={"format": "RGB888", "size": self.size}
            )
            self.cap.configure(config)
            self.cap.start()

            # warmup (evita frames raros al inicio)
            for _ in range(max(0, int(self.warmup_frames))):
                _ = self.cap.capture_array()
                time.sleep(0.01)
            # Picamera2 configurado con RGB888 suele devolver RGB; convertimos a BGR por defecto
            # para mantener el contrato de read(). Si alguna instalación concreta ya entrega BGR,
            # puede desactivarse con CAM_FORCE_CONVERT=0.
            env = os.environ.get("CAM_FORCE_CONVERT", "").strip().lower()
            if env in ("0", "false", "no"):
                self._picamera2_needs_convert = False
            else:
                self._picamera2_needs_convert = True
            return

        # backend opencv
        api = cv2.CAP_DSHOW if os.name == "nt" and hasattr(cv2, "CAP_DSHOW") else 0
        self.cap = cv2.VideoCapture(self.index, api)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.size[0])
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.size[1])

        if not self.cap.isOpened():
            raise RuntimeError("No se pudo abrir la cámara con OpenCV")

    def read(self):
        if not self.cap:
            return None

        if self.backend == "picamera2":
            frame_rgb = self.cap.capture_array()                 # RGB (o BGR en algunas builds)
            if frame_rgb is None:
                return None
            if getattr(self, "_picamera2_needs_convert", True):
                try:
                    frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
                except Exception:
                    frame_bgr = frame_rgb[..., ::-1]
                return frame_bgr
            else:
                return frame_rgb

        ok, frame = self.cap.read()
        if not ok:
            return None
        return frame

    def stop(self):
        if not self.cap:
            return
        try:
            if self.backend == "picamera2":
                try:
                    self.cap.stop()
                except Exception:
                    pass
                try:
                    # clave: liberar el recurso del sistema
                    self.cap.close()
                except Exception:
                    pass
            else:
                self.cap.release()
        finally:
            self.cap = None
            self.backend = None