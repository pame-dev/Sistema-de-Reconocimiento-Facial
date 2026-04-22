import cv2
import numpy as np
import sqlite3
import os
import sys
import threading
from datetime import datetime, timedelta
import pickle
from collections import Counter
import time
import face_recognition

_PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from camera import Camera

try:
    from test_cerradura import ejecutar_cerradura as ejecutar_test_cerradura
except Exception:
    ejecutar_test_cerradura = None


class ReconocerFacial:
    """
    Motor de reconocimiento facial.

    Detección:       Haar Cascade (rápido, sin dependencias extra)
    Reconocimiento:  face_recognition (dlib) — encodings de 128 dimensiones
    Persistencia:    encodings guardados en .pkl, sin reentrenar si no hay cambios
    """

    def __init__(self, db_path='database/sistema_biometrico.db'):
        self.db_path       = db_path
        self.project_root  = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.artifacts_dir = os.path.join(self.project_root, 'database')

        # Archivos de persistencia
        self.encodings_path = os.path.join(self.artifacts_dir, 'encodings.pkl')
        self.ids_hash_path  = os.path.join(self.artifacts_dir, 'ids_hash.pkl')

        # ── Detectores Haar ────────────────────────────────────────────────────
        self._haar_frontal = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        self._haar_alt = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_alt2.xml'
        )
        self._haar_perfil = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_profileface.xml'
        )

        # ── Datos de reconocimiento ────────────────────────────────────────────
        # Lista de encodings conocidos y sus IDs/nombres correspondientes
        self.encodings_conocidos = []   # list[np.ndarray]  — un encoding por muestra
        self.ids_conocidos       = []   # list[int]         — user_id por muestra
        self.nombres             = {}   # dict[int, str]    — user_id → nombre completo

        # ── Parámetros de reconocimiento ───────────────────────────────────────
        self.tolerancia           = 0.42   # distancia máxima para considerar match
        self._TOLERANCIA_MIN      = 0.30
        self._TOLERANCIA_MAX      = 0.65

        # ── Votación ──────────────────────────────────────────────────────────
        self._votos         = []   # list[(user_id|"Desconocido", distancia)]
        self._frames_votar  = 7
        self._procesar_cada = 2
        self._frame_counter = 0
        self._ultimo_resultado = []

        # ── Cooldown de registros en BD ────────────────────────────────────────
        self._ultimo_registro   = {}
        self._cooldown_segundos = 15

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
        self._ultimo_tipo         = None   # None | "aceptado" | "denegado"
        self._desconocido_desde   = None
        self._tolerancia_segundos = 5.0

        # ── Callbacks ─────────────────────────────────────────────────────────
        self.on_resultado = None
        self.on_status    = None
        self.on_sin_cara  = None

        # ── Estadísticas ──────────────────────────────────────────────────────
        self.total_aceptados       = 0
        self.total_denegados       = 0
        self._cerradura_en_proceso = False

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

        resultado = []

        for detector, params in [
            (self._haar_frontal, dict(scaleFactor=1.1, minNeighbors=6, minSize=(80, 80))),
            (self._haar_alt,     dict(scaleFactor=1.1, minNeighbors=5, minSize=(70, 70))),
        ]:
            caras = detector.detectMultiScale(frame_gray, **params)
            if len(caras) == 0:
                continue
            for (x, y, w, h) in caras:
                cx = x + w // 2
                cy = y + h // 2
                # Filtrar caras en los bordes
                if not (margen_x < cx < w_f - margen_x
                        and margen_y < cy < h_f - margen_y):
                    continue
                # Filtrar relaciones de aspecto poco realistas
                ratio = w / h
                if not (0.5 < ratio < 1.8):
                    continue
                resultado.append((x, y, w, h))

            if resultado:
                break  # Con el frontal ya basta; alt2 solo si frontal falla

        return resultado

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
                  AND u.estadoUsuario = 'activo'
            """)
            return {row[0] for row in cur.fetchall()}
        except Exception:
            return set()
        finally:
            conn.close()

    def _ids_en_modelo(self):
        if not os.path.exists(self.ids_hash_path):
            return set()
        try:
            with open(self.ids_hash_path, 'rb') as f:
                return pickle.load(f)
        except Exception:
            return set()

    def _guardar_ids_hash(self, ids_set):
        os.makedirs(self.artifacts_dir, exist_ok=True)
        with open(self.ids_hash_path, 'wb') as f:
            pickle.dump(ids_set, f)

    def _borrar_archivos_modelo(self):
        for p in (self.encodings_path, self.ids_hash_path):
            try:
                os.remove(p)
            except Exception:
                pass

    # ─────────────────────────────────────────────────────────────────────────
    # Construcción de encodings desde la BD
    # ─────────────────────────────────────────────────────────────────────────
    def preparar_encodings(self):
        """
        Lee imágenes de la BD, extrae encodings con face_recognition
        y los guarda en self.encodings_conocidos / self.ids_conocidos.
        Retorna True si hay al menos un encoding válido.
        """
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
              AND u.estadoUsuario = 'activo'
        """)
        filas = cur.fetchall()
        conn.close()

        encodings_tmp = []
        ids_tmp       = []
        nombres_tmp   = {}

        print(f"📸 Procesando {len(filas)} imágenes biométricas...")

        for fila in filas:
            user_id         = fila[0]
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

                # face_recognition espera RGB
                img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

                # Detectar ubicaciones de caras con HOG (más rápido que CNN)
                ubicaciones = face_recognition.face_locations(img_rgb, model="hog")
                if not ubicaciones:
                    continue

                encs = face_recognition.face_encodings(img_rgb, ubicaciones)
                if not encs:
                    continue

                # Usar el encoding de la cara más grande
                enc = encs[0]
                encodings_tmp.append(enc)
                ids_tmp.append(user_id)

            except Exception as e:
                print(f"  ⚠️  Error procesando imagen user {user_id}: {e}")
                continue

        if not encodings_tmp:
            print("❌ No se pudieron extraer encodings.")
            return False

        self.encodings_conocidos = encodings_tmp
        self.ids_conocidos       = ids_tmp
        self.nombres             = nombres_tmp

        ids_usados = set(ids_tmp)
        print(f"  ✅ {len(ids_usados)} usuarios · {len(encodings_tmp)} encodings")
        return True

    # ─────────────────────────────────────────────────────────────────────────
    # Carga / entrenamiento
    # ─────────────────────────────────────────────────────────────────────────
    def cargar_o_reentrenar(self):
        """
        Carga encodings desde disco si el conjunto de IDs no cambió.
        Si cambió (nuevo usuario, eliminado), regenera desde la BD.
        """
        ids_bd     = self._ids_en_bd()
        ids_modelo = self._ids_en_modelo()

        if not ids_bd:
            print("⚠️  No hay usuarios activos con biometría en la BD")
            if self.on_status:
                self.on_status("Sin datos — registra usuarios primero")
            return False

        archivo_ok = os.path.exists(self.encodings_path)

        # Detectar cambios
        if archivo_ok and ids_bd != ids_modelo:
            nuevos     = ids_bd - ids_modelo
            eliminados = ids_modelo - ids_bd
            if nuevos:
                print(f"🔄 {len(nuevos)} usuario(s) nuevo(s) — regenerando encodings")
            if eliminados:
                print(f"🔄 {len(eliminados)} usuario(s) eliminado(s) — regenerando encodings")
            self._borrar_archivos_modelo()
            archivo_ok = False

        if archivo_ok:
            try:
                with open(self.encodings_path, 'rb') as f:
                    datos = pickle.load(f)
                self.encodings_conocidos = datos['encodings']
                self.ids_conocidos       = datos['ids']
                self.nombres             = datos['nombres']

                # Doble verificación: IDs en el archivo vs BD
                ids_archivo = set(self.ids_conocidos)
                if ids_archivo != ids_bd:
                    print("🔄 Encodings desincronizados con BD — regenerando...")
                    self._borrar_archivos_modelo()
                    return self._generar_y_guardar()

                print(f"✅ Encodings cargados · {len(self.nombres)} usuarios")
                if self.on_status:
                    self.on_status(f"Modelo listo · {len(self.nombres)} usuarios")
                return True

            except Exception as e:
                print(f"⚠️  Encodings corruptos ({e}) — regenerando...")
                self._borrar_archivos_modelo()

        return self._generar_y_guardar()

    def _generar_y_guardar(self):
        """Genera encodings desde la BD y los persiste en disco."""
        if self.on_status:
            self.on_status("Generando encodings...")
        print("🔄 Generando encodings desde cero...")

        ok = self.preparar_encodings()
        if not ok:
            return False

        os.makedirs(self.artifacts_dir, exist_ok=True)
        datos = {
            'encodings': self.encodings_conocidos,
            'ids':       self.ids_conocidos,
            'nombres':   self.nombres,
        }
        with open(self.encodings_path, 'wb') as f:
            pickle.dump(datos, f)

        self._guardar_ids_hash(set(self.ids_conocidos))

        print(f"✅ Encodings guardados · {len(self.nombres)} usuarios")
        if self.on_status:
            self.on_status(f"Modelo listo · {len(self.nombres)} usuarios")
        return True

    # ─────────────────────────────────────────────────────────────────────────
    # Reconocimiento
    # ─────────────────────────────────────────────────────────────────────────
    def _reconocer_rostro(self, rostro_bgr):
        """
        Dado un recorte BGR del rostro detectado por Haar,
        extrae el encoding y lo compara con los conocidos.
        Retorna (user_id|"Desconocido", distancia).
        """
        try:
            rostro_rgb = cv2.cvtColor(rostro_bgr, cv2.COLOR_BGR2RGB)

            # Usar whole-image location para que face_recognition no tenga
            # que detectar de nuevo (ya lo hizo Haar)
            h, w = rostro_rgb.shape[:2]
            ubicacion = [(0, w, h, 0)]   # top, right, bottom, left

            encs = face_recognition.face_encodings(rostro_rgb, ubicacion)
            if not encs:
                return "Desconocido", 1.0

            enc_actual = encs[0]

            if not self.encodings_conocidos:
                return "Desconocido", 1.0

            distancias = face_recognition.face_distance(
                self.encodings_conocidos, enc_actual
            )
            idx_min  = int(np.argmin(distancias))
            dist_min = float(distancias[idx_min])

            if dist_min <= self.tolerancia:
                return self.ids_conocidos[idx_min], dist_min
            else:
                return "Desconocido", dist_min

        except Exception as e:
            print(f"⚠️  Error en reconocimiento: {e}")
            return "Desconocido", 1.0

    # ─────────────────────────────────────────────────────────────────────────
    # Votación por mayoría
    # ─────────────────────────────────────────────────────────────────────────
    def _votar(self, label, distancia):
        self._votos.append((label, distancia))
        if len(self._votos) > self._frames_votar:
            self._votos = self._votos[-self._frames_votar:]
        if len(self._votos) < self._frames_votar:
            return None, None

        labels_validos = [l for l, d in self._votos
                          if l != "Desconocido"]
        if len(labels_validos) < int(self._frames_votar * 0.55):
            return "Desconocido", None

        label_ganador = Counter(labels_validos).most_common(1)[0][0]
        dist_media    = float(np.mean(
            [d for l, d in self._votos if l == label_ganador]
        ))
        return label_ganador, dist_media

    # ─────────────────────────────────────────────────────────────────────────
    # Registro de acceso en BD
    # ─────────────────────────────────────────────────────────────────────────
    def _puede_registrar(self, user_id):
        ahora  = datetime.now()
        key    = user_id if user_id is not None else "desconocido"
        ultimo = self._ultimo_registro.get(key)
        if ultimo is None:
            return True
        return (ahora - ultimo).total_seconds() >= self._cooldown_segundos

    def registrar_acceso(self, user_id, estado, distancia):
        if not self._puede_registrar(user_id):
            return

        conn = self.get_db()
        if not conn:
            return

        # Convertir distancia a "confianza" (0-100, mayor = mejor)
        confianza = round(max(0.0, (1.0 - distancia) * 100), 2)

        cur = conn.cursor()
        try:
            cur.execute("""
                INSERT INTO accesos
                    (fkIdUsuario, estado_acceso, confianzaAcceso,
                     umbralConfianzaUsado, fechaHoraIntentoAcceso)
                VALUES (?, ?, ?, ?, ?)
            """, (
                user_id, estado, confianza,
                round((1.0 - self.tolerancia) * 100, 2),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))
            conn.commit()

            key = user_id if user_id is not None else "desconocido"
            self._ultimo_registro[key] = datetime.now()
            self._ultimo_tipo = estado

            if estado == "aceptado":
                self.total_aceptados  += 1
                self._overlay_texto    = "ACCESO PERMITIDO"
                self._overlay_color    = (30, 200, 60)
                self._overlay_frames   = self._overlay_duracion
                self._ultimo_registro.pop("desconocido", None)
                self._abrir_cerradura()
            else:
                self.total_denegados += 1
                self._overlay_texto   = "ACCESO DENEGADO"
                self._overlay_color   = (40, 40, 220)
                self._overlay_frames  = 8
                self._votos = []
                # Acelerar siguiente intento de denegado
                self._ultimo_registro["desconocido"] = (
                    datetime.now() - timedelta(seconds=13)
                )

            if self.on_resultado:
                nombre = self.nombres.get(user_id, "Desconocido")
                self.on_resultado(nombre, confianza, estado)

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
                ejecutar_test_cerradura(8)
            except Exception as e:
                print(f"⚠️  Error en cerradura: {e}")
            finally:
                self._cerradura_en_proceso = False

        threading.Thread(target=_run, daemon=True).start()

    # ─────────────────────────────────────────────────────────────────────────
    # Procesamiento de frame
    # ─────────────────────────────────────────────────────────────────────────
    def procesar_frame(self, frame):
        self._frame_counter += 1

        if self._frame_counter % self._procesar_cada == 0:
            gray      = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces_det = self._detectar_caras(frame, gray)
            self._ultimo_resultado = []

            if faces_det:
                self._frames_sin_cara  = 0
                self._cara_presente    = True
                self._desconocido_desde = None if not faces_det else self._desconocido_desde

                for (x, y, w, h) in faces_det:
                    # Recortar con pequeño margen
                    fh, fw = frame.shape[:2]
                    pad    = int(min(w, h) * 0.08)
                    x1 = max(0, x - pad)
                    y1 = max(0, y - pad)
                    x2 = min(fw, x + w + pad)
                    y2 = min(fh, y + h + pad)

                    rostro_bgr = frame[y1:y2, x1:x2]
                    if rostro_bgr.size == 0:
                        continue

                    label_anterior = self._votos[-1][0] if self._votos else None

                    label_raw, dist_raw = self._reconocer_rostro(rostro_bgr)

                    # Limpiar votos si cambió la cara
                    if label_anterior is not None and label_raw != label_anterior:
                        self._votos = []

                    label, distancia = self._votar(label_raw, dist_raw)

                    if label is None:
                        # Aún acumulando votos — naranja
                        self._ultimo_resultado.append(
                            (x, y, w, h, None, 0, (0, 165, 255)))
                        continue

                    if label == "Desconocido":
                        ahora = datetime.now()
                        if self._ultimo_tipo == "aceptado":
                            if self._desconocido_desde is None:
                                self._desconocido_desde = ahora
                            transcurrido = (ahora - self._desconocido_desde).total_seconds()
                            if transcurrido >= self._tolerancia_segundos:
                                self._desconocido_desde = None
                                self._ultimo_tipo = None
                                self._votos = []
                                self.registrar_acceso(None, "denegado", dist_raw)
                                self._ultimo_resultado.append(
                                    (x, y, w, h, "Desconocido", dist_raw, (40, 40, 220)))
                            else:
                                # Borde amarillo de advertencia durante tolerancia
                                self._ultimo_resultado.append(
                                    (x, y, w, h, None, 0, (0, 200, 255)))
                        else:
                            self._desconocido_desde = None
                            self.registrar_acceso(None, "denegado", dist_raw)
                            self._ultimo_resultado.append(
                                (x, y, w, h, "Desconocido", dist_raw, (40, 40, 220)))
                    else:
                        self._desconocido_desde = None
                        nombre = self.nombres.get(label, "Desconocido")
                        self.registrar_acceso(label, "aceptado", distancia)
                        self._ultimo_resultado.append(
                            (x, y, w, h, nombre, distancia or 0, (30, 200, 60)))

            else:
                self._cara_presente    = False
                self._frames_sin_cara += 1
                self._votos            = []
                self._desconocido_desde = None

                if (self._frames_sin_cara >= self._umbral_sin_cara
                        and self.on_sin_cara):
                    self._ultimo_tipo = None
                    self.on_sin_cara()
                    self._frames_sin_cara = 0

        # ── Dibujar rectángulos con esquinas estilizadas ──────────────────────
        for (x, y, w, h, nombre, dist, color) in self._ultimo_resultado:
            cv2.rectangle(frame, (x, y), (x+w, y+h), color, 1)
            sz = 16
            grosor = 3
            # Esquinas
            for (px, py), (dx, dy) in [
                ((x,   y),   ( 1,  1)),
                ((x+w, y),   (-1,  1)),
                ((x,   y+h), ( 1, -1)),
                ((x+w, y+h), (-1, -1)),
            ]:
                cv2.line(frame, (px, py), (px + dx*sz, py),       color, grosor)
                cv2.line(frame, (px, py), (px,         py + dy*sz), color, grosor)

        # ── Overlay ACEPTADO / DENEGADO ───────────────────────────────────────
        if self._overlay_frames > 0:
            self._dibujar_overlay(frame)
            self._overlay_frames -= 1

        return frame

    def _dibujar_overlay(self, frame):
        h, w   = frame.shape[:2]
        texto  = self._overlay_texto
        color  = self._overlay_color
        alpha  = min(1.0, self._overlay_frames / 8)

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
    # Modo standalone (sin GUI)
    # ─────────────────────────────────────────────────────────────────────────
    def iniciar(self):
        print("=" * 55)
        print("🚀 SISTEMA DE RECONOCIMIENTO FACIAL — Sentinel System")
        print("=" * 55)

        try:
            self.camara = Camera()
            self.camara.start()
            time.sleep(1)
            print("📷 Cámara iniciada")
        except Exception as e:
            print(f"❌ No se pudo abrir la cámara: {e}")
            return

        if not self.cargar_o_reentrenar():
            print("❌ No se pudieron cargar los encodings")
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
                    f"Tolerancia: {self.tolerancia:.2f}  |  +/- ajustar  |  q salir",
                    (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 0), 2
                )
                cv2.imshow("Reconocimiento Facial — Sentinel System", frame)

                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                elif key in (ord('+'), ord('='), 43, 61):
                    self.tolerancia = min(self._TOLERANCIA_MAX,
                                         round(self.tolerancia + 0.02, 2))
                    self._votos = []
                    print(f"🎯 Tolerancia subida → {self.tolerancia}")
                elif key in (ord('-'), ord('_'), 45, 95):
                    self.tolerancia = max(self._TOLERANCIA_MIN,
                                         round(self.tolerancia - 0.02, 2))
                    self._votos = []
                    print(f"🎯 Tolerancia bajada → {self.tolerancia}")

        finally:
            if self.camara:
                try:
                    self.camara.stop()
                except Exception:
                    pass
            cv2.destroyAllWindows()
            print("👋 Sistema cerrado")


if __name__ == "__main__":
    reconocedor = ReconocerFacial()
    reconocedor.iniciar()