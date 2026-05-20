import cv2
import os
import sys
import platform
import time
from datetime import datetime, timedelta

from idiomas import t
from camera import Camera

from .mixins.database_mixin       import DatabaseMixin
from .mixins.deteccion_mixin      import DeteccionMixin
from .mixins.modelo_mixin         import ModeloMixin
from .mixins.reconocimiento_mixin import ReconocimientoMixin
from .mixins.acceso_mixin         import AccesoMixin
from .mixins.overlay_mixin        import OverlayMixin

_PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)


# ── Haar cascades (multiplataforma: Windows + Debian/Raspberry) ──────────────
def haar_path(filename: str) -> str:
    """
    Devuelve ruta absoluta a Haar cascade.
    - Windows (opencv-python) suele tener: cv2.data.haarcascades
    - Debian/Raspberry: opencv-data -> /usr/share/opencv4/haarcascades
    """
    if hasattr(cv2, "data") and hasattr(cv2.data, "haarcascades"):
        return os.path.join(cv2.data.haarcascades, filename)

    debian_dir = "/usr/share/opencv4/haarcascades"
    p = os.path.join(debian_dir, filename)
    if os.path.exists(p):
        return p

    # fallback adicional por si alguna distro lo ubica distinto
    for base in ("/usr/share/opencv/haarcascades",):
        p2 = os.path.join(base, filename)
        if os.path.exists(p2):
            return p2

    raise FileNotFoundError(
        f"No encontré Haar cascade '{filename}'. "
        f"En Debian instala: sudo apt install opencv-data"
    )


class ReconocerFacial(
    DatabaseMixin,
    DeteccionMixin,
    ModeloMixin,
    ReconocimientoMixin,
    AccesoMixin,
    OverlayMixin,
):

    def __init__(self, db_path='database/sistema_biometrico.db'):
        self.db_path       = db_path
        self.project_root  = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.artifacts_dir = os.path.join(self.project_root, 'database')

        # Archivos de persistencia
        self.model_path     = os.path.join(self.artifacts_dir, 'lbph_model.yml')
        self.data_path      = os.path.join(self.artifacts_dir, 'lbph_data.pkl')
        self.ids_hash_path  = os.path.join(self.artifacts_dir, 'ids_hash.pkl')
        self._modelo_version = 12  # sube versión por cambios de lógica

        # flag que indica si el modelo está listo para predecir ──
        self._modelo_listo = False

        # ── Detectores Haar ────────────────────────────────────────────────────
        self._haar_frontal = cv2.CascadeClassifier(
            haar_path('haarcascade_frontalface_default.xml')
        )
        self._haar_alt = cv2.CascadeClassifier(
            haar_path('haarcascade_frontalface_alt2.xml')
        )
        self._haar_perfil = cv2.CascadeClassifier(
            haar_path('haarcascade_profileface.xml')
        )

        # Detector de ojos (no crítico; si no carga, soltamos solo una advertencia)
        self._haar_eyes = cv2.CascadeClassifier(
            haar_path('haarcascade_eye.xml')
        )

        # Validación (si no cargan, fallará la detección y "parece que no detecta nada")
        if self._haar_frontal.empty():
            raise RuntimeError("No se pudo cargar haarcascade_frontalface_default.xml")
        if self._haar_alt.empty():
            raise RuntimeError("No se pudo cargar haarcascade_frontalface_alt2.xml")
        if self._haar_perfil.empty():
            raise RuntimeError("No se pudo cargar haarcascade_profileface.xml")
        if self._haar_eyes.empty():
            print("⚠️ No se pudo cargar haarcascade_eye.xml — validación de ojos desactivada")

        # ── Reconocedor LBPH ───────────────────────────────────────────────────
        self.recognizer = self._crear_lbph_recognizer()

        # ── Datos de reconocimiento ────────────────────────────────────────────
        self.nombres = {}   # dict[int, str]    — user_id → nombre completo

        # ── Parámetros de reconocimiento ───────────────────────────────────────
        # En LBPH "conf" es una distancia/error: más bajo = mejor match.
        self.tolerancia                   = 83.0
        self._TOLERANCIA_MIN              = 60.0
        self._TOLERANCIA_MAX              = 95.0
        self._MARGEN_RECONOCIMIENTO_SUAVE = 0.0

        # ── Votación ───────────────────────────────────────────────────────────
        self._votos         = []
        # Aumentado a 5 para requerir coincidencia en múltiples frames y evitar
        # falsos positivos cuando distancia es muy alta por mismatch de captura.
        self._frames_votar  = 8
        self._procesar_cada = 1      # procesa cada frame para responder más rápido
        self._frame_counter = 0
        self._ultimo_resultado = []

        # ── Cooldown de registros en BD ────────────────────────────────────────
        self._ultimo_registro   = {}
        self._cooldown_segundos = 4

        # ── Overlay en frame ──────────────────────────────────────────────────
        self._overlay_texto    = ""
        self._overlay_color    = (0, 0, 0)
        self._overlay_frames   = 0
        self._overlay_duracion = 40

        # ── Ausencia de cara ──────────────────────────────────────────────────
        self._frames_sin_cara = 0
        self._umbral_sin_cara = 150
        self._cara_presente   = False

        # ── Estado de acceso ──────────────────────────────────────────────────
        self._ultimo_tipo       = None
        self._desconocido_desde = None

        self._tolerancia_segundos  = 0.4
        self._fast_accept_margin   = 0.0
        self._desconocido_hold_seg = 0.5

        self._ultimo_usuario_aceptado  = None
        self._ultimo_aceptado_ts       = None
        self._ventana_recuperacion_seg = 15.0
        self._margen_recuperacion      = 0.0

        # Cooldown corto tras acceso aceptado para evitar duplicados sin bloquear
        # demasiado tiempo el reconocimiento de una nueva persona.
        self._cooldown_post_aceptado_seg = 6
        self._frame_limpio = None

        # ── Callbacks ─────────────────────────────────────────────────────────
        self.on_resultado = None
        self.on_status    = None
        self.on_sin_cara  = None

        # ── Estadísticas ──────────────────────────────────────────────────────
        self.total_aceptados       = 0
        self.total_denegados       = 0
        self._cerradura_en_proceso = False

        # ── Cooldown después de acceso aceptado ──────────────────────────────
        self._cooldown_hasta      = None
        self._ultimo_detectado_ts = None

        # ── Perfil automático por dispositivo ────────────────────────────────
        self._is_raspberry = self._detectar_raspberry_pi()
        if self._is_raspberry:
            # La cámara de Raspberry suele tener más ruido/variación de luz.
            # Mantener tolerancia ESTRICTA
            self.tolerancia      = 83.0
            self._TOLERANCIA_MIN = 60.0
            self._TOLERANCIA_MAX = 95.0
            # Sin márgenes adicionales para ser estricto
            self._MARGEN_RECONOCIMIENTO_SUAVE = 0.0
            self._margen_recuperacion         = 0.0
            self._fast_accept_margin          = 0.0
            # Mantener frames_votar en 5 para estabilidad multi-frame (no forzar 1).
            self._frames_votar                = max(self._frames_votar, 5)
            self._desconocido_hold_seg        = max(self._desconocido_hold_seg, 0.7)

    @staticmethod
    def _detectar_raspberry_pi() -> bool:
        """Detecta si se está ejecutando en Raspberry Pi (Linux ARM)."""
        try:
            machine = platform.machine().lower()
            if "arm" not in machine and "aarch" not in machine:
                return False

            model_paths = [
                "/proc/device-tree/model",
                "/sys/firmware/devicetree/base/model",
            ]
            for p in model_paths:
                if os.path.exists(p):
                    with open(p, "r", encoding="utf-8", errors="ignore") as f:
                        txt = f.read().lower()
                    if "raspberry" in txt:
                        return True

            # Fallback para ARM Linux cuando no se puede leer model.
            return platform.system().lower() == "linux"
        except Exception:
            return False

    # ─────────────────────────────────────────────────────────────────────────
    # Procesamiento de frame
    # ─────────────────────────────────────────────────────────────────────────
    def procesar_frame(self, frame):
        # ── CORRECCIÓN 5: bloquear procesamiento hasta que el modelo esté listo ──
        if not self._modelo_listo:
            return frame

        self._frame_counter += 1
        self._frame_limpio   = frame.copy()

        ahora = datetime.now()
        if self._cooldown_hasta and ahora < self._cooldown_hasta:
            if self._ultimo_detectado_ts and (ahora - self._ultimo_detectado_ts).total_seconds() >= 6.0:
                self._cooldown_hasta          = None
                self._ultimo_usuario_aceptado = None
                self._ultimo_detectado_ts     = None
                self._votos                   = []
                self._desconocido_desde       = None
            else:
                # Durante cooldown limpiar votos para no contaminar el siguiente intento
                self._votos = []
                self._desconocido_desde = None
                return frame

        if self._frame_counter % self._procesar_cada == 0:
            gray      = self._preprocess_gray(frame)
            faces_det = self._detectar_caras(frame, gray)
            self._ultimo_resultado = []

            if faces_det:
                self._frames_sin_cara = 0
                self._cara_presente   = True

                x, y, w, h = max(faces_det, key=lambda r: r[2] * r[3])
                fh, fw = frame.shape[:2]
                pad    = int(min(w, h) * 0.08)
                x1 = max(0,  x - pad)
                y1 = max(0,  y - pad)
                x2 = min(fw, x + w + pad)
                y2 = min(fh, y + h + pad)

                rostro_bgr = frame[y1:y2, x1:x2]
                if rostro_bgr.size != 0:
                    label_anterior = self._votos[-1][0] if self._votos else None

                    label_raw, dist_raw = self._reconocer_rostro(rostro_bgr)
                    if label_raw != "Desconocido":
                        print("DEBUG match", label_raw, "conf", dist_raw, "tol", self.tolerancia)

                    # Fast-path: match muy bueno → aceptar sin esperar votación
                    if (isinstance(label_raw, int) and label_raw > 0
                            and dist_raw is not None
                            and dist_raw <= (self.tolerancia - self._fast_accept_margin)):

                        if self._usuario_activo(label_raw):
                            self._votos             = []
                            self._desconocido_desde = None
                            nombre = self.nombres.get(label_raw, "Desconocido")
                            self.registrar_acceso(label_raw, "aceptado", dist_raw)
                            self._cooldown_hasta          = ahora + timedelta(seconds=self._cooldown_post_aceptado_seg)
                            self._ultimo_usuario_aceptado = label_raw
                            self._ultimo_detectado_ts     = ahora
                            self._ultimo_resultado = [(x, y, w, h, nombre, dist_raw, (30, 200, 60))]
                    else:
                        if label_raw == self._ultimo_usuario_aceptado:
                            self._ultimo_detectado_ts = ahora

                        if (label_anterior is not None
                                and label_raw != label_anterior
                                and label_anterior != "Desconocido"
                                and label_raw != "Desconocido"):
                            self._votos = []

                        # ── CORRECCIÓN 6: acumular votos correctamente antes de llamar _votar ──
                        self._votos.append((label_raw, dist_raw))
                        if len(self._votos) > self._frames_votar:
                            self._votos.pop(0)

                        labels_v    = [v[0] for v in self._votos]
                        distancias_v = [v[1] for v in self._votos]
                        label, distancia = self._votar(labels_v, distancias_v)

                        if label is None:
                            self._ultimo_resultado = [(x, y, w, h, None, 0, (0, 165, 255))]
                        elif label == "Desconocido":
                            ahora = datetime.now()
                            if self._desconocido_desde is None:
                                self._desconocido_desde = ahora
                            transcurrido = (ahora - self._desconocido_desde).total_seconds()

                            if self._ultimo_tipo == "aceptado":
                                if transcurrido >= self._tolerancia_segundos:
                                    self._desconocido_desde = None
                                    self._ultimo_tipo       = None
                                    self._votos             = []
                                    self.registrar_acceso(
                                        None, "denegado", dist_raw,
                                        frame_limpio=self._frame_limpio
                                    )
                                    self._ultimo_resultado = [(x, y, w, h, "Desconocido", dist_raw, (40, 40, 220))]
                                else:
                                    self._ultimo_resultado = [(x, y, w, h, None, 0, (0, 200, 255))]
                            else:
                                if transcurrido >= self._desconocido_hold_seg:
                                    self._desconocido_desde = None
                                    self._votos             = []
                                    self.registrar_acceso(
                                        None, "denegado", dist_raw,
                                        frame_limpio=self._frame_limpio
                                    )
                                    self._ultimo_resultado = [(x, y, w, h, "Desconocido", dist_raw, (40, 40, 220))]
                                else:
                                    self._ultimo_resultado = [(x, y, w, h, None, 0, (0, 200, 255))]
                        else:
                            if label == self._ultimo_usuario_aceptado:
                                self._ultimo_detectado_ts = ahora

                            # VALIDACIÓN ESTRICTA: solo aceptar IDs de usuarios válidos (int > 0)
                            if not isinstance(label, int) or label <= 0:
                                self._desconocido_desde = None
                                self._votos = []
                                self.registrar_acceso(
                                    None, "denegado", distancia or dist_raw,
                                    frame_limpio=self._frame_limpio
                                )
                                self._ultimo_resultado = [(x, y, w, h, "Desconocido", distancia or dist_raw, (40, 40, 220))]
                            elif not self._usuario_activo(label):
                                self._desconocido_desde = None
                                self.registrar_acceso(
                                    None, "denegado", dist_raw,
                                    frame_limpio=self._frame_limpio
                                )
                                self._ultimo_resultado = [(x, y, w, h, "Desconocido", dist_raw, (40, 40, 220))]
                            elif distancia is not None and distancia <= self.tolerancia:
                                # Aceptar solo si ALL condiciones se cumplen
                                self._desconocido_desde = None
                                nombre = self.nombres.get(label, "Desconocido")
                                self.registrar_acceso(label, "aceptado", distancia)
                                self._cooldown_hasta          = ahora + timedelta(seconds=self._cooldown_post_aceptado_seg)
                                self._ultimo_usuario_aceptado = label
                                self._ultimo_detectado_ts     = ahora
                                self._ultimo_resultado = [(x, y, w, h, nombre, distancia or 0, (30, 200, 60))]
                            else:
                                # Distancia fuera del umbral, rechazar
                                self._desconocido_desde = None
                                self._votos = []
                                self.registrar_acceso(
                                    None, "denegado", distancia or dist_raw,
                                    frame_limpio=self._frame_limpio
                                )
                                self._ultimo_resultado = [(x, y, w, h, "Desconocido", distancia or dist_raw, (40, 40, 220))]

            else:
                self._cara_presente    = False
                self._frames_sin_cara += 1
                self._votos            = []
                self._desconocido_desde = None

                if self._frames_sin_cara >= self._umbral_sin_cara and self.on_sin_cara:
                    self._ultimo_tipo     = None
                    self.on_sin_cara()
                    self._frames_sin_cara = 0

        # Dibujar rectángulos con esquinas
        for (x, y, w, h, nombre, dist, color) in self._ultimo_resultado:
            cv2.rectangle(frame, (x, y), (x+w, y+h), color, 1)
            sz     = 16
            grosor = 3
            for (px, py), (dx, dy) in [
                ((x,   y),   ( 1,  1)),
                ((x+w, y),   (-1,  1)),
                ((x,   y+h), ( 1, -1)),
                ((x+w, y+h), (-1, -1)),
            ]:
                cv2.line(frame, (px, py), (px + dx*sz, py),         color, grosor)
                cv2.line(frame, (px, py), (px,         py + dy*sz), color, grosor)

        if self._overlay_frames > 0:
            self._dibujar_overlay(frame)
            self._overlay_frames -= 1

        return frame

    # ─────────────────────────────────────────────────────────────────────────
    # Modo standalone
    # ─────────────────────────────────────────────────────────────────────────
    def iniciar(self):
        print("=" * 55)
        print("🚀 SISTEMA DE RECONOCIMIENTO FACIAL — ")
        print("=" * 55)

        try:
            self.camara = Camera()
            self.camara.start()
            time.sleep(1)
            print(t("camara_iniciada"))
        except Exception as e:
            print(t("sin_camara"))
            return

        if not self.cargar_o_reentrenar():
            print("❌ No se pudieron cargar el modelo LBPH")
            return

        print(f"🎯 Tolerancia: {self.tolerancia}  |  +/- para ajustar  |  q para salir")
        print("=" * 55)

        try:
            while True:
                frame = self.camara.read()
                if frame is None:
                    continue

                frame = self.procesar_frame(frame)

                cv2.putText(
                    frame,
                    f"{t('tolerancia')}: {self.tolerancia:.1f}  |  +/- {t('ajustar')}  |  q {t('salir')}",
                    (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 0), 2
                )
                cv2.imshow("Reconocimiento Facial — UnimoraAccess", frame)

                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                elif key in (ord('+'), ord('='), 43, 61):
                    self.tolerancia = min(self._TOLERANCIA_MAX,
                                          round(self.tolerancia + 0.5, 2))
                    self._votos = []
                    print(f"🎯 Tolerancia subida → {self.tolerancia}")
                elif key in (ord('-'), ord('_'), 45, 95):
                    self.tolerancia = max(self._TOLERANCIA_MIN,
                                          round(self.tolerancia - 0.5, 2))
                    self._votos = []
                    print(f"🎯 Tolerancia bajada → {self.tolerancia}")

        finally:
            if getattr(self, "camara", None):
                try:
                    self.camara.stop()
                except Exception:
                    pass
            cv2.destroyAllWindows()
            print(t("cerrado"))


if __name__ == "__main__":
    reconocedor = ReconocerFacial()
    reconocedor.iniciar()