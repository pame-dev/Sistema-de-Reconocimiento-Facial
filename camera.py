#archivo para poder usar la camara de la raspberry y tambien la de windows
import os

try:
    from picamera2 import Picamera2
    import cv2
    USE_PI_CAMERA = True
except ImportError:
    import cv2
    USE_PI_CAMERA = False


class Camera:
    def __init__(self):
        self.cap = None

    def start(self):
        if USE_PI_CAMERA:
            self.cap = Picamera2()
            config = self.cap.create_preview_configuration(
                main={"format": "RGB888", "size": (640, 480)}
            )
            self.cap.configure(config)
            self.cap.start()
        else:
            # En Windows, CAP_DSHOW suele abrir más rápido y con menos bloqueos.
            if os.name == "nt" and hasattr(cv2, "CAP_DSHOW"):
                self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            else:
                self.cap = cv2.VideoCapture(0)

            if not self.cap or not self.cap.isOpened():
                raise RuntimeError("No se pudo abrir la cámara")

    def read(self):
        if not self.cap:
            return None

        if USE_PI_CAMERA:
            frame = self.cap.capture_array()
            return cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        else:
            ret, frame = self.cap.read()
            if not ret:
                return None
            return frame

    def stop(self):
        if not self.cap:
            return

        if USE_PI_CAMERA:
            self.cap.stop()
        else:
            self.cap.release()

        self.cap = None