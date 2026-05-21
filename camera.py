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
            try:
                import importlib
                Picamera2 = importlib.import_module("picamera2").Picamera2
            except Exception:
                self.backend = "opencv"
            else:
                self.cap = Picamera2()

                config = self.cap.create_preview_configuration(
                    main={"format": "BGR888", "size": self.size}
                )
                self.cap.configure(config)
                self.cap.start()

                # warmup (evita frames raros al inicio)
                for _ in range(max(0, int(self.warmup_frames))):
                    _ = self.cap.capture_array()
                    time.sleep(0.01)
                # BGR888 mantiene el contrato de read() y evita depender de una conversión posterior.
                # Si alguna instalación no soporta este formato, el backend caerá al manejo normal.
                self._picamera2_needs_convert = False
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
            frame_bgr = self.cap.capture_array()                 # BGR888 cuando el backend lo soporta
            if frame_bgr is None:
                return None
            if getattr(self, "_picamera2_needs_convert", False):
                try:
                    return cv2.cvtColor(frame_bgr, cv2.COLOR_RGB2BGR)
                except Exception:
                    return frame_bgr[..., ::-1]
            return frame_bgr

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