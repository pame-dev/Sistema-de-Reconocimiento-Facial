import cv2
import numpy as np
import sqlite3
import os
from datetime import datetime, timedelta
import pickle
from collections import Counter

try:
    import mediapipe as mp
    _mp_face = getattr(mp, "solutions", None)
    _MP_DISPONIBLE = _mp_face is not None
except Exception:
    _MP_DISPONIBLE = False
    print("⚠️  mediapipe no instalado. Usando solo Haar Cascade.")
    print("   Instala con: pip install mediapipe")


class ReconocerFacial:

    def __init__(self, db_path='database/sistema_biometrico.db',
                 usar_mediapipe=True):
        self.db_path       = db_path
        self.project_root  = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.artifacts_dir = os.path.join(self.project_root, 'database')
        self.model_path    = os.path.join(self.artifacts_dir, 'modelo_entrenado.yml')
        self.names_path    = os.path.join(self.artifacts_dir, 'nombres.pkl')
        self.ids_hash_path = os.path.join(self.artifacts_dir, 'ids_hash.pkl')

        self.recognizer = cv2.face.LBPHFaceRecognizer_create(
            radius=2, neighbors=8, grid_x=8, grid_y=8
        )
        self._haar = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )

        self._usar_mp     = usar_mediapipe and _MP_DISPONIBLE
        self._mp_detector = None
        if self._usar_mp:
            self._mp_detector = _mp_face.FaceDetection(
                model_selection=0, min_detection_confidence=0.6
            )
            print("✅ MediaPipe FaceDetection activado")
        else:
            print("ℹ️  Usando Haar Cascade como único detector")

        self.nombres            = {}
        self.umbral_confianza   = 80
        self._UMBRAL_MIN        = 10
        self._votos             = []
        self._frames_votar      = 7
        self._ultimo_registro   = {}
        self._cooldown_segundos = 15
        self._frame_counter     = 0
        self._procesar_cada     = 2
        self._ultimo_resultado  = []

        self._overlay_texto    = ""
        self._overlay_color    = (0, 0, 0)
        self._overlay_frames   = 0
        self._overlay_duracion = 40

        self._frames_sin_cara = 0
        self._umbral_sin_cara = 150
        self._cara_presente   = False

        # Estado explícito: None | "aceptado" | "denegado"
        self._ultimo_tipo = None

        # ── Tolerancia para pasar de "aceptado" → "denegado" ─────────────────
        # Cuando estando aceptado el sistema vota "Desconocido", se inicia un
        # temporizador. Solo se deniega si pasan _tolerancia_segundos continuos
        # sin reconocer al usuario. Si en ese lapso vuelve a reconocerlo,
        # el temporizador se cancela y sigue aceptado.
        # En sentido contrario (denegado → reconocido) el cambio es inmediato.
        self._desconocido_desde   = None  # datetime de inicio de la racha sin reconocer
        self._tolerancia_segundos = 5.0   # segundos antes de forzar denegación

        self.on_resultado = None
        self.on_status    = None
        self.on_sin_cara  = None

        self.total_aceptados = 0
        self.total_denegados = 0

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
    # Detección
    # ─────────────────────────────────────────────────────────────────────────
    def _detectar_caras(self, frame_bgr, frame_gray):
        if self._usar_mp and self._mp_detector is not None:
            caras = self._detectar_mp(frame_bgr)
            if caras:
                return caras
        return self._detectar_haar(frame_gray)

    def _detectar_mp(self, frame_bgr):
        h_f, w_f = frame_bgr.shape[:2]
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        frame_rgb.flags.writeable = False
        resultados = self._mp_detector.process(frame_rgb)
        frame_rgb.flags.writeable = True

        caras = []
        if not resultados.detections:
            return caras

        margen_x = int(w_f * 0.20)
        margen_y = int(h_f * 0.15)
        zona_x1, zona_x2 = margen_x, w_f - margen_x
        zona_y1, zona_y2 = margen_y, h_f - margen_y

        for det in resultados.detections:
            bb  = det.location_data.relative_bounding_box
            x   = max(0, int(bb.xmin  * w_f))
            y   = max(0, int(bb.ymin  * h_f))
            w   = min(int(bb.width    * w_f), w_f - x)
            h_b = min(int(bb.height   * h_f), h_f - y)

            if w < 60 or h_b < 60:
                continue
            cx = x + w // 2
            cy = y + h_b // 2
            if not (zona_x1 < cx < zona_x2 and zona_y1 < cy < zona_y2):
                continue
            ratio = w / h_b
            if not (0.5 < ratio < 1.6):
                continue
            caras.append((x, y, w, h_b))

        return caras

    def _detectar_haar(self, frame_gray):
        h_f, w_f = frame_gray.shape[:2]
        margen_x = int(w_f * 0.20)
        margen_y = int(h_f * 0.15)

        caras = self._haar.detectMultiScale(
            frame_gray, scaleFactor=1.1, minNeighbors=6, minSize=(90, 90)
        )
        if len(caras) == 0:
            return []

        resultado = []
        for (x, y, w, h) in caras:
            cx = x + w // 2
            cy = y + h // 2
            if not (margen_x < cx < w_f - margen_x and margen_y < cy < h_f - margen_y):
                continue
            ratio = w / h
            if not (0.5 < ratio < 1.6):
                continue
            resultado.append((x, y, w, h))
        return resultado

    # ─────────────────────────────────────────────────────────────────────────
    # Preprocesado
    # ─────────────────────────────────────────────────────────────────────────
    def preprocesar(self, img_gris):
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        img   = clahe.apply(img_gris)
        img   = cv2.bilateralFilter(img, d=9, sigmaColor=75, sigmaSpace=75)
        return img

    def _recortar_rostro_seguro(self, img_gris, x, y, w, h):
        fh, fw = img_gris.shape[:2]
        pad_x = int(w * 0.10)
        pad_y = int(h * 0.10)
        x1 = max(0, x - pad_x)
        y1 = max(0, y - pad_y)
        x2 = min(fw, x + w + pad_x)
        y2 = min(fh, y + h + pad_y)

        if x2 <= x1 or y2 <= y1:
            return None

        rostro = img_gris[y1:y2, x1:x2]
        if rostro.size == 0 or rostro.shape[0] < 10 or rostro.shape[1] < 10:
            return None

        rostro = cv2.resize(rostro, (200, 200))
        rostro = np.uint8(rostro)

        if rostro.shape != (200, 200):
            return None

        return rostro

    def _es_cara_real(self, rostro_gray):
        laplacian = cv2.Laplacian(rostro_gray, cv2.CV_64F)
        varianza  = laplacian.var()
        return varianza > 18.0

    # ─────────────────────────────────────────────────────────────────────────
    # Entrenamiento
    # ─────────────────────────────────────────────────────────────────────────
    def _ids_en_bd(self):
        conn = self.get_db()
        if not conn:
            return set()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT b.fkIdUsuario
                FROM biometria b
                INNER JOIN usuarios u ON u.idUsuario = b.fkIdUsuario
                WHERE b.encodeBiometria IS NOT NULL
                  AND u.estadoUsuario = 'activo'
            """)
            return {row[0] for row in cursor.fetchall()}
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

    def preparar_datos(self):
        conn = self.get_db()
        if not conn:
            return [], []

        cursor = conn.cursor()
        cursor.execute("""
            SELECT u.idUsuario,
                   u.nombreUsuario, u.apellidoPaternoUsuario, u.apellidoMaternoUsuario,
                   b.encodeBiometria
            FROM usuarios u
            INNER JOIN biometria b ON u.idUsuario = b.fkIdUsuario
            WHERE b.encodeBiometria IS NOT NULL
              AND u.estadoUsuario = 'activo'
        """)
        resultados = cursor.fetchall()
        conn.close()

        faces, labels = [], []
        self.nombres  = {}
        print(f"📸 Procesando {len(resultados)} registros biométricos...")

        for row in resultados:
            user_id         = row[0]
            nombre_completo = f"{row[1]} {row[2] or ''} {row[3] or ''}".strip()
            self.nombres[user_id] = nombre_completo

            imagen_bytes = row[4]
            if not imagen_bytes:
                continue

            nparr = np.frombuffer(imagen_bytes, np.uint8)
            img   = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
            if img is None:
                continue

            img = cv2.resize(img, (200, 200))
            img = np.uint8(img)

            faces.append(img)
            labels.append(user_id)

        print(f"  Total: {len(set(labels))} usuarios, {len(faces)} imágenes")
        return faces, labels

    def cargar_o_reentrenar(self):
        ids_bd     = self._ids_en_bd()
        ids_modelo = self._ids_en_modelo()

        archivos_ok = (os.path.exists(self.model_path)
                       and os.path.exists(self.names_path))

        if not ids_bd:
            print("⚠️  No hay usuarios activos con biometría en la BD")
            if self.on_status:
                self.on_status("Sin datos — registra usuarios primero")
            return False

        if archivos_ok and ids_bd != ids_modelo:
            nuevos     = ids_bd - ids_modelo
            eliminados = ids_modelo - ids_bd
            if nuevos:
                print(f"🔄 Reentrenando — {len(nuevos)} usuario(s) nuevo(s)")
            if eliminados:
                print(f"🔄 Reentrenando — {len(eliminados)} usuario(s) eliminado(s)")
            for p in (self.model_path, self.names_path, self.ids_hash_path):
                try:
                    os.remove(p)
                except Exception:
                    pass
            archivos_ok = False

        if archivos_ok:
            try:
                self.recognizer.read(self.model_path)
                with open(self.names_path, 'rb') as f:
                    self.nombres = pickle.load(f)

                ids_nombres = set(self.nombres.keys())
                if ids_nombres != ids_bd:
                    print("🔄 Modelo desincronizado con BD — reentrenando...")
                    for p in (self.model_path, self.names_path, self.ids_hash_path):
                        try:
                            os.remove(p)
                        except Exception:
                            pass
                    return self.entrenar()

                print(f"✅ Modelo cargado · {len(self.nombres)} usuarios")
                if self.on_status:
                    self.on_status(f"Modelo listo · {len(self.nombres)} usuarios")
                return True
            except Exception as e:
                print(f"⚠️  Modelo corrupto ({e}) — reentrenando...")
                for p in (self.model_path, self.names_path, self.ids_hash_path):
                    try:
                        os.remove(p)
                    except Exception:
                        pass

        print("🔄 Entrenando modelo desde cero...")
        if self.on_status:
            self.on_status("Entrenando modelo...")
        return self.entrenar()

    def entrenar(self):
        if self.on_status:
            self.on_status("Cargando datos...")
        faces, labels = self.preparar_datos()
        if len(faces) == 0:
            print("❌ No hay datos para entrenar.")
            return False

        if self.on_status:
            self.on_status(f"Entrenando {len(set(labels))} usuarios...")
        self.recognizer.train(faces, np.array(labels))
        os.makedirs(self.artifacts_dir, exist_ok=True)
        self.recognizer.save(self.model_path)
        with open(self.names_path, 'wb') as f:
            pickle.dump(self.nombres, f)
        self._guardar_ids_hash(set(labels))

        print(f"✅ Modelo entrenado con {len(set(labels))} usuarios")
        return True

    def cargar_modelo(self):
        if (os.path.exists(self.model_path)
                and os.path.exists(self.names_path)):
            self.recognizer.read(self.model_path)
            with open(self.names_path, 'rb') as f:
                self.nombres = pickle.load(f)
            print(f"✅ Modelo cargado · {len(self.nombres)} usuarios")
            return True
        print("⚠️  No se encontró modelo guardado")
        return False

    # ─────────────────────────────────────────────────────────────────────────
    # Votación
    # ─────────────────────────────────────────────────────────────────────────
    def _votar(self, label, confianza):
        self._votos.append((label, confianza))
        if len(self._votos) > self._frames_votar:
            self._votos = self._votos[-self._frames_votar:]
        if len(self._votos) < self._frames_votar:
            return None, None

        labels_validos = [l for l, c in self._votos if c < self.umbral_confianza]
        if len(labels_validos) < int(self._frames_votar * 0.55):
            return "Desconocido", None

        label_ganador   = Counter(labels_validos).most_common(1)[0][0]
        confianza_media = np.mean([c for l, c in self._votos if l == label_ganador])
        return label_ganador, confianza_media

    def _puede_registrar(self, user_id):
        ahora  = datetime.now()
        key    = user_id if user_id is not None else "desconocido"
        ultimo = self._ultimo_registro.get(key)
        if ultimo is None:
            return True
        return (ahora - ultimo).total_seconds() >= self._cooldown_segundos

    def registrar_acceso(self, user_id, estado, confianza):
        if not self._puede_registrar(user_id):
            return

        conn = self.get_db()
        if not conn:
            return

        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO accesos
                    (fkIdUsuario, estado_acceso, confianzaAcceso,
                     umbralConfianzaUsado, fechaHoraIntentoAcceso)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, estado, confianza, self.umbral_confianza,
                  datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()

            key = user_id if user_id is not None else "desconocido"
            self._ultimo_registro[key] = datetime.now()
            self._ultimo_tipo = estado

            if estado == "aceptado":
                self.total_aceptados += 1
                self._overlay_texto   = "ACCESO PERMITIDO"
                self._overlay_color   = (30, 200, 60)
                self._overlay_frames  = self._overlay_duracion
                self._ultimo_registro.pop("desconocido", None)
            else:
                self.total_denegados += 1
                self._overlay_texto   = "ACCESO DENEGADO"
                self._overlay_color   = (40, 40, 220)
                self._overlay_frames  = 8
                self._votos = []
                self._ultimo_registro["desconocido"] = datetime.now() - timedelta(seconds=13)

            if self.on_resultado:
                nombre = self.nombres.get(user_id, "Desconocido")
                self.on_resultado(nombre, confianza, estado)

        except Exception as e:
            print(f"❌ Error registrando acceso: {e}")
        finally:
            conn.close()

    # ─────────────────────────────────────────────────────────────────────────
    # Loop principal
    # ─────────────────────────────────────────────────────────────────────────
    def procesar_frame(self, frame):
        self._frame_counter += 1

        if self._frame_counter % self._procesar_cada == 0:
            gray      = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces_det = self._detectar_caras(frame, gray)
            self._ultimo_resultado = []

            if faces_det:
                self._frames_sin_cara = 0
                self._cara_presente   = True

                for (x, y, w, h) in faces_det:
                    rostro = self._recortar_rostro_seguro(gray, x, y, w, h)
                    if rostro is None:
                        continue

                    if not self._es_cara_real(rostro):
                        self._ultimo_resultado.append(
                            (x, y, w, h, None, 0, (128, 128, 128)))
                        continue

                    label_anterior = self._votos[-1][0] if self._votos else None

                    try:
                        label_raw, conf_raw = self.recognizer.predict(rostro)
                    except cv2.error as e:
                        print(f"⚠️  predict falló (frame ignorado): {e}")
                        continue
                    except Exception as e:
                        print(f"⚠️  predict error inesperado: {e}")
                        continue

                    if label_anterior is not None and label_raw != label_anterior:
                        self._votos = []

                    label, confianza = self._votar(label_raw, conf_raw)

                    if label is None:
                        # Aún acumulando votos — naranja, sin cambiar panel
                        self._ultimo_resultado.append(
                            (x, y, w, h, None, 0, (0, 165, 255)))
                        continue

                    if label == "Desconocido":
                        if self._ultimo_tipo == "aceptado":
                            # ── Tolerancia de 5 s antes de denegar ──────────────
                            ahora = datetime.now()
                            if self._desconocido_desde is None:
                                # Primera vez que no lo reconoce — arrancar temporizador
                                self._desconocido_desde = ahora

                            transcurrido = (ahora - self._desconocido_desde).total_seconds()

                            if transcurrido >= self._tolerancia_segundos:
                                # Se agotó la tolerancia — denegar
                                self._desconocido_desde = None
                                self._ultimo_tipo = None
                                self._votos = []
                                self.registrar_acceso(None, "denegado", conf_raw)
                                self._ultimo_resultado.append(
                                    (x, y, w, h, "Desconocido", conf_raw, (40, 40, 220)))
                            else:
                                # Aún dentro de la tolerancia — borde amarillo de advertencia
                                self._ultimo_resultado.append(
                                    (x, y, w, h, None, 0, (0, 200, 255)))
                        else:
                            # Sin estado aceptado previo — denegar directamente
                            self._desconocido_desde = None
                            self.registrar_acceso(None, "denegado", conf_raw)
                            self._ultimo_resultado.append(
                                (x, y, w, h, "Desconocido", conf_raw, (40, 40, 220)))

                    else:
                        # ── Reconocido: aceptar siempre de forma inmediata ──────
                        # Esto aplica también cuando venía de estado "denegado",
                        # el cambio a permitido es instantáneo sin esperas.
                        self._desconocido_desde = None
                        nombre = self.nombres.get(label, "Desconocido")
                        self.registrar_acceso(label, "aceptado", confianza)
                        self._ultimo_resultado.append(
                            (x, y, w, h, nombre, confianza or 0, (30, 200, 60)))

            else:
                self._cara_presente    = False
                self._frames_sin_cara += 1
                self._votos = []
                # Al perder la cara se cancela el temporizador de tolerancia
                self._desconocido_desde = None

                if (self._frames_sin_cara >= self._umbral_sin_cara
                        and self.on_sin_cara):
                    self._ultimo_tipo = None
                    self.on_sin_cara()
                    self._frames_sin_cara = 0

        # ── Dibujar rectángulos ───────────────────────────────────────────────
        for (x, y, w, h, nombre, conf, color) in self._ultimo_resultado:
            cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
            sz = 14
            cv2.line(frame, (x,     y),    (x+sz,   y),    color, 3)
            cv2.line(frame, (x,     y),    (x,      y+sz), color, 3)
            cv2.line(frame, (x+w,   y),    (x+w-sz, y),    color, 3)
            cv2.line(frame, (x+w,   y),    (x+w,    y+sz), color, 3)
            cv2.line(frame, (x,     y+h),  (x+sz,   y+h),  color, 3)
            cv2.line(frame, (x,     y+h),  (x,      y+h-sz), color, 3)
            cv2.line(frame, (x+w,   y+h),  (x+w-sz, y+h),  color, 3)
            cv2.line(frame, (x+w,   y+h),  (x+w,    y+h-sz), color, 3)

        # ── Overlay ───────────────────────────────────────────────────────────
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
    # Modo standalone
    # ─────────────────────────────────────────────────────────────────────────
    def iniciar(self):
        print("="*55)
        print("🚀 SISTEMA DE RECONOCIMIENTO FACIAL — Sentinel System")
        print("="*55)

        if not self.cargar_o_reentrenar():
            print("❌ No se pudo cargar ni reentrenar el modelo")
            return

        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("❌ No se pudo abrir la cámara")
            return

        cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        detector_str = "MediaPipe+Haar" if self._usar_mp else "Haar"
        print(f"🎥 Cámara iniciada · Umbral: {self.umbral_confianza} · Detector: {detector_str}")
        print("q → salir  |  + → subir umbral  |  - → bajar umbral  |  m → toggle MediaPipe")
        print("="*55)

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame = self.procesar_frame(frame)
            cv2.putText(frame,
                        f"Umbral: {self.umbral_confianza}  [{detector_str}]  +/- ajustar",
                        (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 0), 2)
            cv2.imshow('Reconocimiento Facial — Sentinel System', frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key in (ord('+'), ord('='), 43, 61):
                self.umbral_confianza += 5
                self._votos = []
                print(f"🎯 Umbral subido → {self.umbral_confianza}")
            elif key in (ord('-'), ord('_'), 45, 95):
                self.umbral_confianza = max(self._UMBRAL_MIN,
                                            self.umbral_confianza - 5)
                self._votos = []
                print(f"🎯 Umbral bajado → {self.umbral_confianza}")
            elif key == ord('m'):
                if _MP_DISPONIBLE:
                    self._usar_mp = not self._usar_mp
                    print(f"🔄 MediaPipe → {'ON' if self._usar_mp else 'OFF (solo Haar)'}")

        cap.release()
        cv2.destroyAllWindows()
        print("👋 Sistema cerrado")


if __name__ == "__main__":
    reconocedor = ReconocerFacial()
    reconocedor.iniciar()