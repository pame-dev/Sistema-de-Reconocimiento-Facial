import cv2
import numpy as np
import sqlite3
import os
import sys
import platform
import threading
from datetime import datetime, timedelta
import pickle
import hashlib
from collections import Counter
import time
from idiomas import t

_PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from camera import Camera

try:
    from admin.biometric_system.contro_cerradura import ejecutar_cerradura as ejecutar_test_cerradura
except Exception:
    ejecutar_test_cerradura = None
try:
    from test_buzzer import beep as ejecutar_buzzer_concedido
except Exception as e:
    print(f"⚠️ Buzzer concedido no disponible: {e}")
    ejecutar_buzzer_concedido = None

try:
    from test_buzzer2 import beep as ejecutar_buzzer_denegado
except Exception as e:
    print(f"⚠️ Buzzer denegado no disponible: {e}")
    ejecutar_buzzer_denegado = None

try:
    from tools.access_counter import AccessCounter
except Exception:
    AccessCounter = None


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

class ReconocerFacial:
    
    def __init__(self, db_path='database/sistema_biometrico.db'):
        self.db_path       = db_path
        self.project_root  = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.artifacts_dir = os.path.join(self.project_root, 'database')

        # Archivos de persistencia
        self.model_path     = os.path.join(self.artifacts_dir, 'lbph_model.yml')
        self.data_path      = os.path.join(self.artifacts_dir, 'lbph_data.pkl')
        self.ids_hash_path  = os.path.join(self.artifacts_dir, 'ids_hash.pkl')
        self._modelo_version = 11  # sube versión por cambios de lógica

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
        # AJUSTE: Umbral ESTRICTO - solo acepta confianza > 25 (distancia < 75)
        self.tolerancia                   = 75.0
        self._TOLERANCIA_MIN              = 75.0
        self._TOLERANCIA_MAX              = 75.0
        self._MARGEN_RECONOCIMIENTO_SUAVE = 0.0

        # ── Votación ───────────────────────────────────────────────────────────
        self._votos         = []
        # Aumentado a 5 para requerir coincidencia en múltiples frames y evitar
        # falsos positivos cuando distancia es muy alta por mismatch de captura.
        self._frames_votar  = 5
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
            self.tolerancia = 75.0
            # Sin márgenes adicionales para ser estricto
            self._MARGEN_RECONOCIMIENTO_SUAVE = 0.0
            self._margen_recuperacion         = 0.0
            self._fast_accept_margin          = 0.0
            # Mantener frames_votar en 5 para estabilidad multi-frame (no forzar 1).
            self._frames_votar                = max(self._frames_votar, 5)
            self._desconocido_hold_seg        = max(self._desconocido_hold_seg, 0.7)

    @staticmethod
    def _crear_lbph_recognizer():
        """Crea el reconocedor LBPH con compatibilidad entre variantes de OpenCV."""
        face_mod = getattr(cv2, "face", None)
        if face_mod is None:
            raise RuntimeError(
                "OpenCV no incluye cv2.face. Instala solo opencv-contrib-python."
            )

        ctor = getattr(face_mod, "LBPHFaceRecognizer_create", None)
        if callable(ctor):
            return ctor()

        # Algunas compilaciones exponen la clase y su constructor .create()
        cls = getattr(face_mod, "LBPHFaceRecognizer", None)
        create_fn = getattr(cls, "create", None) if cls is not None else None
        if callable(create_fn):
            return create_fn()

        raise RuntimeError(
            "Tu OpenCV no trae LBPH. Reinstala con: pip uninstall -y opencv opencv-python opencv-contrib-python && pip install opencv-contrib-python==4.10.0.84"
        )

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
    # Base de datos
    # ─────────────────────────────────────────────────────────────────────────
    def get_db(self):
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            return conn
        except sqlite3.Error as e:
            print(f"❌ Error conectando a DB: {e}")
            return None

    def _usuario_activo(self, user_id: int) -> bool:
        """Retorna True si el usuario está activo en la BD."""
        if user_id is None:
            return False
        conn = self.get_db()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT estadoUsuario FROM usuarios WHERE idUsuario = ? LIMIT 1",
                (int(user_id),)
            )
            row = cur.fetchone()
            if not row:
                return False
            estado = row[0]
            return str(estado).lower() == "activo"
        except Exception:
            return False
        finally:
            conn.close()

    def _frame_a_bytes(self, frame):
        """Convierte un frame BGR de OpenCV a bytes JPEG comprimidos."""
        if frame is None:
            return None
        try:
            ok, buf = cv2.imencode(
                '.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 75]
            )
            if ok:
                return buf.tobytes()
        except Exception as e:
            print(f"⚠️ Error al codificar foto de acceso: {e}")
        return None

    # ─────────────────────────────────────────────────────────────────────────
    # Detección de caras — Haar Cascade
    # ─────────────────────────────────────────────────────────────────────────
    def _detectar_caras(self, frame_bgr, frame_gray):
        """
        Detecta caras usando Haar Cascade frontal + alt2.
        Devuelve lista de (x, y, w, h) filtradas por tamaño y posición central.
        """
        h_f, w_f = frame_gray.shape[:2]
        margen_x = int(w_f * 0.10)
        margen_y = int(h_f * 0.08)

        candidatos = []

        for detector, params, flipped in [
            (self._haar_frontal, dict(scaleFactor=1.1, minNeighbors=4, minSize=(80, 80)), False),
            (self._haar_alt,     dict(scaleFactor=1.1, minNeighbors=4, minSize=(70, 70)), False),
            (self._haar_perfil,  dict(scaleFactor=1.1, minNeighbors=4, minSize=(70, 70)), False),
            (self._haar_perfil,  dict(scaleFactor=1.1, minNeighbors=4, minSize=(70, 70)), True),
        ]:
            gray_search = cv2.flip(frame_gray, 1) if flipped else frame_gray
            caras = detector.detectMultiScale(gray_search, **params)
            if len(caras) == 0:
                continue
            for (x, y, w, h) in caras:
                if flipped:
                    x = w_f - (x + w)
                cx = x + w // 2
                cy = y + h // 2
                if not (margen_x < cx < w_f - margen_x
                        and margen_y < cy < h_f - margen_y):
                    continue
                ratio = w / h
                if not (0.5 < ratio < 1.8):
                    continue

                roi_gray  = frame_gray[y:y+h, x:x+w]
                ojos_en_roi = []
                try:
                    if not self._haar_eyes.empty():
                        ojos_en_roi = self._haar_eyes.detectMultiScale(
                            roi_gray, scaleFactor=1.1, minNeighbors=5, minSize=(20, 20)
                        )
                except Exception:
                    ojos_en_roi = []

                area        = w * h
                dist_centro = abs(cx - (w_f / 2.0)) + abs(cy - (h_f / 2.0)) * 0.5
                score       = area - (dist_centro * 2.5)
                has_eyes    = 1 if len(ojos_en_roi) >= 1 else 0
                candidatos.append((has_eyes, score, x, y, w, h))

            if candidatos:
                break

        if not candidatos:
            return []

        candidatos.sort(key=lambda it: (it[0], it[1]), reverse=True)
        _, _, x, y, w, h = candidatos[0]
        return [(x, y, w, h)]

    def _preprocess_gray(self, frame_bgr):
        """
        Preprocesado para detección: convierte a gris, aplica CLAHE y
        un ligero ajuste de contraste/brillo si la imagen está muy oscura.
        """
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        try:
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            gray  = clahe.apply(gray)
        except Exception:
            try:
                gray = cv2.equalizeHist(gray)
            except Exception:
                pass

        med = float(np.median(gray))
        if med < 70.0:
            gray = cv2.convertScaleAbs(gray, alpha=1.3, beta=15)
        elif med > 185.0:
            gray = cv2.convertScaleAbs(gray, alpha=0.82, beta=-12)

        return gray

    def _normalizar_rostro_gray(self, gray):
        """Normaliza un recorte de rostro para reducir sensibilidad a cambios de luz."""
        if gray is None or gray.size == 0:
            return gray

        out = gray
        try:
            clahe = cv2.createCLAHE(clipLimit=2.2, tileGridSize=(8, 8))
            out   = clahe.apply(out)
        except Exception:
            pass

        med = float(np.median(out))
        if med < 65.0:
            out = cv2.convertScaleAbs(out, alpha=1.25, beta=18)
        elif med > 190.0:
            out = cv2.convertScaleAbs(out, alpha=0.85, beta=-14)

        try:
            eq  = cv2.equalizeHist(out)
            out = cv2.addWeighted(out, 0.65, eq, 0.35, 0)
        except Exception:
            pass

        return out

    # ─────────────────────────────────────────────────────────────────────────
    # Gestión de IDs y persistencia
    # ─────────────────────────────────────────────────────────────────────────
    def _ids_en_bd(self):
        conn = self.get_db()
        if not conn:
            return set()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT DISTINCT b.fkIdUsuario
                FROM biometria b
                INNER JOIN usuarios u ON u.idUsuario = b.fkIdUsuario
                WHERE b.encodeBiometria IS NOT NULL
                AND LOWER(TRIM(u.estadoUsuario)) = 'activo'
            """)
            return {row[0] for row in cur.fetchall()}
        except Exception:
            return set()
        finally:
            conn.close()

    def _ids_en_modelo(self):
        if not os.path.exists(self.ids_hash_path):
            return set(), None
        try:
            with open(self.ids_hash_path, 'rb') as f:
                data = pickle.load(f)
            if isinstance(data, set):
                return data, None
            if isinstance(data, dict):
                return data.get('ids', set()), data.get('fingerprint')
        except Exception:
            pass
        return set(), None

    def _fingerprint_en_bd(self):
        conn = self.get_db()
        if not conn:
            return None
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT b.fkIdUsuario, b.encodeBiometria
                FROM biometria b
                INNER JOIN usuarios u ON u.idUsuario = b.fkIdUsuario
                WHERE b.encodeBiometria IS NOT NULL
                AND LOWER(TRIM(u.estadoUsuario)) = 'activo'
            """)
            items = []
            for user_id, imagen_bytes in cur.fetchall():
                if imagen_bytes is None:
                    continue
                digest = hashlib.md5(imagen_bytes).hexdigest()
                items.append((user_id, digest))
            return tuple(sorted(items))
        except Exception:
            return None
        finally:
            conn.close()

    def _guardar_ids_hash(self, ids_set, fingerprint=None):
        os.makedirs(self.artifacts_dir, exist_ok=True)
        data = {'ids': ids_set, 'fingerprint': fingerprint}
        with open(self.ids_hash_path, 'wb') as f:
            pickle.dump(data, f)

    def _borrar_archivos_modelo(self):
        for p in (self.model_path, self.data_path, self.ids_hash_path):
            try:
                os.remove(p)
            except Exception:
                pass

    def _cargar_modelo_lbph(self):
        if hasattr(self.recognizer, 'read'):
            self.recognizer.read(self.model_path)
            return
        if hasattr(self.recognizer, 'load'):
            self.recognizer.load(self.model_path)
            return
        raise AttributeError("LBPHFaceRecognizer no soporta read/load en este build")

    def _guardar_modelo_lbph(self):
        if hasattr(self.recognizer, 'write'):
            self.recognizer.write(self.model_path)
            return
        if hasattr(self.recognizer, 'save'):
            self.recognizer.save(self.model_path)
            return
        raise AttributeError("LBPHFaceRecognizer no soporta write/save en este build")

    # ─────────────────────────────────────────────────────────────────────────
    # Construcción de datos para LBPH desde la BD
    # ─────────────────────────────────────────────────────────────────────────
    def preparar_datos(self):
        conn = self.get_db()
        if not conn:
            return False

        cur = conn.cursor()
        cur.execute("""
            SELECT u.idUsuario,
                u.nombreUsuario, u.apellidoPaternoUsuario, u.apellidoMaternoUsuario,
                b.encodeBiometria
            FROM usuarios u
            INNER JOIN biometria b ON u.idUsuario = b.fkIdUsuario
            WHERE b.encodeBiometria IS NOT NULL
            AND LOWER(TRIM(u.estadoUsuario)) = 'activo'
        """)
        filas = cur.fetchall()
        conn.close()

        faces_tmp    = []
        labels_tmp   = []
        nombres_tmp  = {}
        fallback_directo = 0

        print(t("procesando_imagenes"))

        for fila in filas:
            user_id        = fila[0]
            nombre_completo = f"{fila[1]} {fila[2] or ''} {fila[3] or ''}".strip()
            nombres_tmp[user_id] = nombre_completo

            imagen_bytes = fila[4]
            if not imagen_bytes:
                continue

            try:
                nparr = np.frombuffer(imagen_bytes, np.uint8)
                img   = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                if img is None:
                    continue

                gray  = self._preprocess_gray(img)
                caras = self._detectar_caras(img, gray)

                if len(caras) > 0:
                    x, y, w, h = max(caras, key=lambda c: c[2] * c[3])
                    fh, fw = gray.shape[:2]
                    pad = int(min(w, h) * 0.08)
                    x1  = max(0,  x - pad)
                    y1  = max(0,  y - pad)
                    x2  = min(fw, x + w + pad)
                    y2  = min(fh, y + h + pad)
                    rostro_gray = gray[y1:y2, x1:x2]
                    if rostro_gray.size == 0:
                        continue
                else:
                    fallback_directo += 1
                    rostro_gray = gray

                rostro_gray = cv2.resize(rostro_gray, (100, 100))
                rostro_gray = self._normalizar_rostro_gray(rostro_gray)

                faces_tmp.append(rostro_gray)
                labels_tmp.append(user_id)

            except Exception as e:
                print(f"  ⚠️  Error procesando imagen user {user_id}: {e}")
                continue

        if not faces_tmp:
            print(t("sin_rostros"))
            return False

        self.faces   = faces_tmp
        self.labels  = labels_tmp
        self.nombres = nombres_tmp

        ids_usados = set(labels_tmp)
        print(f"  ✅ {len(ids_usados)} usuarios · {len(faces_tmp)} rostros")
        if fallback_directo > 0:
            print(f"  ℹ️  {fallback_directo} muestra(s) usadas sin redetección Haar")
        return True

    # ─────────────────────────────────────────────────────────────────────────
    # Carga / entrenamiento
    # ─────────────────────────────────────────────────────────────────────────
    def cargar_o_reentrenar(self):
        ids_bd             = self._ids_en_bd()
        ids_modelo, fp_mod = self._ids_en_modelo()
        fp_bd              = self._fingerprint_en_bd()

        if not ids_bd:
            print(t("sin_usuarios"))
            if self.on_status:
                self.on_status(t("sin_datos"))
            return False

        archivo_ok = os.path.exists(self.model_path) and os.path.exists(self.data_path)

        if archivo_ok and (ids_bd != ids_modelo or fp_bd != fp_mod):
            nuevos     = ids_bd - ids_modelo
            eliminados = ids_modelo - ids_bd
            if nuevos:
                print(f"🔄 {len(nuevos)} usuario(s) nuevo(s) — regenerando modelo")
            if eliminados:
                print(f"🔄 {len(eliminados)} usuario(s) eliminado(s) — regenerando modelo")
            elif fp_bd != fp_mod:
                print("🔄 Imagen(es) biométrica(s) actualizada(s) — regenerando modelo")
            self._borrar_archivos_modelo()
            archivo_ok = False

        if archivo_ok:
            try:
                self._cargar_modelo_lbph()
                with open(self.data_path, 'rb') as f:
                    data = pickle.load(f)

                self.nombres             = data['nombres']
                ids_archivo              = data['ids']
                self.tolerancia          = float(data.get('tolerancia', self.tolerancia))
                modelo_version_archivo   = int(data.get('modelo_version', 1))

                if modelo_version_archivo != self._modelo_version:
                    print("🔄 Versión de preprocesado/lógica cambiada — regenerando modelo...")
                    self._borrar_archivos_modelo()
                    return self._generar_y_guardar()

                if ids_archivo != ids_bd:
                    print("🔄 Modelo desincronizado con BD — regenerando...")
                    self._borrar_archivos_modelo()
                    return self._generar_y_guardar()

                print(f"✅ Modelo LBPH cargado · {len(self.nombres)} usuarios")
                if self.on_status:
                    self.on_status(t("modelo_listo"))

                # ── CORRECCIÓN 2: marcar modelo como listo tras carga exitosa ──
                self._modelo_listo = True
                return True

            except Exception as e:
                print(t("modelo_corrupto"))
                self._borrar_archivos_modelo()

        return self._generar_y_guardar()

    def _generar_y_guardar(self):
        if self.on_status:
            self.on_status(t("generando_modelo"))
        print(t("generando_modelo"))

        ok = self.preparar_datos()
        if not ok:
            return False

        self.recognizer.train(self.faces, np.array(self.labels, dtype=np.int32))

        os.makedirs(self.artifacts_dir, exist_ok=True)
        self._guardar_modelo_lbph()

        self._ajustar_tolerancia_post_entreno()

        data = {
            'nombres':        self.nombres,
            'ids':            set(self.labels),
            'tolerancia':     self.tolerancia,
            'modelo_version': self._modelo_version,
        }
        with open(self.data_path, 'wb') as f:
            pickle.dump(data, f)

        self._guardar_ids_hash(set(self.labels), self._fingerprint_en_bd())

        print(f"✅ Modelo LBPH guardado · {len(self.nombres)} usuarios")
        if self.on_status:
            self.on_status(f"Modelo listo · {len(self.nombres)} usuarios")

        # ── CORRECCIÓN 3: marcar modelo como listo tras entrenamiento exitoso ──
        self._modelo_listo = True
        return True

    def _ajustar_tolerancia_post_entreno(self):
        """Ajusta la tolerancia automáticamente según los datos entrenados."""
        if not getattr(self, 'faces', None):
            return
        distancias = []
        for rostro in self.faces:
            try:
                _, conf = self.recognizer.predict(rostro)
                distancias.append(float(conf))
            except Exception:
                continue
        if not distancias:
            return

        umbral = float(np.percentile(distancias, 90)) + 4.0

        # Con 2 usuarios y mismatch de captura, permitir tolerancia más alta
        if len(self.nombres) <= 2:
            umbral = min(umbral, 125.0)

        self.tolerancia = min(self._TOLERANCIA_MAX,
                              max(self._TOLERANCIA_MIN, umbral))
        print(f"🔧 Tolerancia ajustada a {self.tolerancia:.1f} según datos de entrenamiento")

    # ─────────────────────────────────────────────────────────────────────────
    # Reconocimiento
    # ─────────────────────────────────────────────────────────────────────────
    def _reconocer_rostro(self, rostro_bgr):
        """Retorna (user_id|'Desconocido', distancia)."""
        # ── CORRECCIÓN 4: guard con _modelo_listo (seguro en Raspberry Pi) ──
        if not self._modelo_listo:
            return "Desconocido", 100.0

        try:
            gray_base = cv2.cvtColor(rostro_bgr, cv2.COLOR_BGR2GRAY)
            gray_base = cv2.resize(gray_base, (100, 100))
            gray_base = self._normalizar_rostro_gray(gray_base)

            # Un recorte central un poco más estricto suele estabilizar
            # rostros frontales cuando el borde del detector trae mucho fondo.
            margen = 10
            centro = gray_base[margen:100 - margen, margen:100 - margen]
            if centro.size != 0:
                centro = cv2.resize(centro, (100, 100))
                centro = self._normalizar_rostro_gray(centro)
            else:
                centro = gray_base

            variantes = [
                gray_base,
                centro,
                cv2.equalizeHist(gray_base),
                cv2.equalizeHist(centro),
                cv2.GaussianBlur(gray_base, (3, 3), 0),
                cv2.GaussianBlur(centro, (3, 3), 0),
                cv2.convertScaleAbs(gray_base, alpha=1.10, beta=8),
                cv2.convertScaleAbs(gray_base, alpha=0.90, beta=-8),
            ]

            predicciones = []
            for variante in variantes:
                label_i, conf_i = self.recognizer.predict(variante)
                predicciones.append((int(label_i), float(conf_i)))

            mejor_label, mejor_conf = min(predicciones, key=lambda it: it[1])

            labels       = [l for l, _ in predicciones]
            label        = Counter(labels).most_common(1)[0][0]
            dists_label  = [c for l, c in predicciones if l == label]
            conf         = float(np.median(dists_label))

            # VALORIZACIÓN ESTRICTA: Rechazar -1 (desconocido según OpenCV LBPH)
            if label == -1:
                return "Desconocido", conf

            # Solo aceptar si confianza está dentro del umbral
            if conf <= self.tolerancia:
                return label, conf

            # Todo lo demás es rechazado
            return "Desconocido", conf

        except Exception as e:
            print(f"⚠️  Error en reconocimiento: {e}")
            return "Desconocido", 100.0

    # ─────────────────────────────────────────────────────────────────────────
    # Votación por mayoría
    # ─────────────────────────────────────────────────────────────────────────
    def _votar(self, labels, distancias):
        """
        Votación por mayoría para determinar identidad.

        Args:
            labels:    lista de IDs (int) o 'Desconocido'
            distancias: lista de distancias/confianzas (float)

        Returns:
            (label_ganador, distancia_minima) o ('Desconocido', inf)
        """
        if not isinstance(labels, (list, tuple)):
            return "Desconocido", float("inf")
        if not isinstance(distancias, (list, tuple)):
            return "Desconocido", float("inf")
        if not labels or not distancias:
            return "Desconocido", float("inf")
        if len(labels) != len(distancias):
            return "Desconocido", float("inf")

        pares_validos = [
            (label, dist) for label, dist in zip(labels, distancias)
            if isinstance(label, int) and label > 0  # Solo IDs de usuarios positivos
            and isinstance(dist, (int, float))
        ]

        if not pares_validos:
            return "Desconocido", float("inf")

        labels_validos = [label for label, _ in pares_validos]
        label_ganador  = Counter(labels_validos).most_common(1)[0][0]

        distancias_ganadoras = [d for l, d in pares_validos if l == label_ganador]
        distancia = min(distancias_ganadoras) if distancias_ganadoras else float("inf")

        return label_ganador, distancia

    # ─────────────────────────────────────────────────────────────────────────
    # Registro de acceso en BD (con cooldown real)
    # ─────────────────────────────────────────────────────────────────────────
    def _puede_registrar(self, user_id):
        ahora  = datetime.now()
        key    = user_id if user_id is not None else "desconocido"
        ultimo = self._ultimo_registro.get(key)
        if ultimo is None:
            return True
        return (ahora - ultimo).total_seconds() >= self._cooldown_segundos

    def registrar_acceso(self, user_id, estado, distancia, frame_limpio=None):
        confianza          = round(max(0.0, 100 - float(distancia)), 2)
        hubo_cambio_estado = (self._ultimo_tipo != estado)

        if not self._puede_registrar(user_id):
            self._ultimo_tipo = estado
            if hubo_cambio_estado and self.on_resultado:
                nombre = self.nombres.get(user_id, t("desconocido"))
                self.on_resultado(nombre, confianza, estado, float(distancia))
            return

        conn = self.get_db()
        if not conn:
            return

        cur = conn.cursor()

        try:
            foto_bytes = None
            if estado == "denegado" and frame_limpio is not None:
                foto_bytes = self._frame_a_bytes(frame_limpio)

            cur.execute("""
                INSERT INTO accesos
                    (fkIdUsuario, estado_acceso, confianzaAcceso,
                     umbralConfianzaUsado, fechaHoraIntentoAcceso, fotoAcceso)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                estado,
                confianza,
                round(self.tolerancia, 2),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                foto_bytes
            ))
            conn.commit()

            key = user_id if user_id is not None else "desconocido"
            self._ultimo_registro[key] = datetime.now()
            self._ultimo_tipo = estado

            if estado == "aceptado":
                self.total_aceptados += 1
                if AccessCounter is not None:
                    try:
                        AccessCounter.increment(1)
                    except Exception:
                        pass
                self._overlay_texto  = t("acceso_permitido")
                self._overlay_color  = (30, 200, 60)
                self._overlay_frames = self._overlay_duracion
                self._ultimo_registro.pop("desconocido", None)
                self._ultimo_usuario_aceptado = user_id
                self._ultimo_aceptado_ts      = datetime.now()
                self._abrir_cerradura()
                if ejecutar_buzzer_concedido:
                    threading.Thread(target=ejecutar_buzzer_concedido, daemon=True).start()
            else:
                self.total_denegados += 1
                self._overlay_texto  = t("acceso_denegado")
                self._overlay_color  = (40, 40, 220)
                self._overlay_frames = 8
                self._votos = []
                if ejecutar_buzzer_denegado:
                    threading.Thread(target=ejecutar_buzzer_denegado, daemon=True).start()

            if self.on_resultado:
                nombre = self.nombres.get(user_id, t("desconocido"))
                self.on_resultado(nombre, confianza, estado, float(distancia))

        except Exception as e:
            print(f"❌ Error registrando acceso: {e}")
        finally:
            conn.close()

    def _abrir_cerradura(self):
        if self._cerradura_en_proceso or ejecutar_test_cerradura is None:
            return
        self._cerradura_en_proceso = True

        def _run():
            try:
                ejecutar_test_cerradura(1)
            except Exception as e:
                print(f"⚠️  Error en cerradura: {e}")
            finally:
                self._cerradura_en_proceso = False

        threading.Thread(target=_run, daemon=True).start()

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
            else:
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

    def _dibujar_overlay(self, frame):
        h, w  = frame.shape[:2]
        texto = self._overlay_texto
        color = self._overlay_color
        alpha = min(1.0, self._overlay_frames / 8)

        overlay = frame.copy()
        bar_h   = 56
        cv2.rectangle(overlay, (0, h - bar_h), (w, h), color, -1)
        cv2.addWeighted(overlay, alpha * 0.55, frame, 1 - alpha * 0.55, 0, frame)

        font  = cv2.FONT_HERSHEY_DUPLEX
        scale = 1.1
        thick = 2
        (tw, th), _ = cv2.getTextSize(texto, font, scale, thick)
        tx = (w - tw) // 2
        ty = h - bar_h + th + (bar_h - th) // 2
        cv2.putText(frame, texto, (tx, ty), font, scale,
                    (255, 255, 255), thick, cv2.LINE_AA)

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