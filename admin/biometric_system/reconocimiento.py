import cv2
import numpy as np
import sqlite3
import os
from datetime import datetime
import pickle
from collections import Counter


class ReconocerFacial:
    def __init__(self, db_path='database/sistema_biometrico.db'):
        self.db_path       = db_path
        self.project_root  = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.artifacts_dir = os.path.join(self.project_root, 'database')
        self.model_path    = os.path.join(self.artifacts_dir, 'modelo_entrenado.yml')
        self.names_path    = os.path.join(self.artifacts_dir, 'nombres.pkl')

        self.recognizer = cv2.face.LBPHFaceRecognizer_create(
            radius=2, neighbors=8, grid_x=8, grid_y=8
        )
        self.detector = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )

        self.nombres            = {}
        self.umbral_confianza   = 80
        self._votos             = []
        self._frames_votar      = 10
        self._ultimo_registro   = {}
        self._cooldown_segundos = 30
        self._frame_counter     = 0
        self._procesar_cada     = 2
        self._ultimo_resultado  = []

        # Estado del overlay en el frame
        self._overlay_texto     = ""       # "ACEPTADO" / "DENEGADO" / ""
        self._overlay_color     = (0, 0, 0)
        self._overlay_frames    = 0        # cuántos frames mostrar el overlay
        self._overlay_duracion  = 40       # frames que dura el overlay (~1.3 s a 30 fps)

        # Detección de ausencia de cara
        self._frames_sin_cara   = 0
        self._umbral_sin_cara   = 90       # ~3 s a 30 fps antes de avisar ausencia
        self._cara_presente     = False

        # Callbacks
        self.on_resultado   = None   # (nombre, confianza, tipo)
        self.on_status      = None   # (texto)
        self.on_sin_cara    = None   # () — disparado cuando no hay cara N frames seguidos

        self.total_aceptados = 0
        self.total_denegados = 0

    # ─────────────────────────────────────────────────────────────────────────
    def get_db(self):
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            return conn
        except sqlite3.Error as e:
            print(f"❌ Error conectando a DB: {e}")
            return None

    def preprocesar(self, img_gris):
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        img   = clahe.apply(img_gris)
        img   = cv2.bilateralFilter(img, d=9, sigmaColor=75, sigmaSpace=75)
        return img

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
        """)
        resultados = cursor.fetchall()
        conn.close()

        faces, labels = [], []
        self.nombres  = {}
        print(f"📸 Procesando {len(resultados)} registros biométricos...")

        for idx, row in enumerate(resultados):
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
            img = self.preprocesar(img)
            img = np.uint8(img)

            faces.append(img)
            labels.append(user_id)

        print(f"  Total: {len(set(labels))} usuarios, {len(faces)} imágenes")
        return faces, labels

    def _contar_usuarios_bd(self):
        conn = self.get_db()
        if not conn:
            return 0
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(DISTINCT fkIdUsuario)
                FROM biometria
                WHERE encodeBiometria IS NOT NULL
            """)
            return cursor.fetchone()[0]
        except Exception:
            return 0
        finally:
            conn.close()

    def cargar_o_reentrenar(self):
        usuarios_bd   = self._contar_usuarios_bd()
        modelo_existe = (os.path.exists(self.model_path)
                         and os.path.exists(self.names_path))

        if modelo_existe:
            try:
                self.recognizer.read(self.model_path)
                with open(self.names_path, 'rb') as f:
                    self.nombres = pickle.load(f)
                usuarios_modelo = len(self.nombres)
                print(f"✅ Modelo cargado · {usuarios_modelo} usuarios en modelo · {usuarios_bd} en BD")

                if usuarios_bd <= usuarios_modelo:
                    if self.on_status:
                        self.on_status(f"Modelo listo · {usuarios_modelo} usuarios")
                    return True

                print(f"🔄 Reentrenando — {usuarios_bd - usuarios_modelo} usuario(s) nuevo(s)...")
                if self.on_status:
                    self.on_status("Actualizando modelo...")
                return self.entrenar()

            except Exception as e:
                print(f"⚠️  Modelo corrupto ({e}) — reentrenando...")
                for p in (self.model_path, self.names_path):
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

    def _votar(self, label, confianza):
        self._votos.append((label, confianza))
        if len(self._votos) > self._frames_votar:
            self._votos = self._votos[-self._frames_votar:]
        if len(self._votos) < self._frames_votar:
            return None, None

        labels_validos = [l for l, c in self._votos if c < self.umbral_confianza]
        if len(labels_validos) < int(self._frames_votar * 0.7):
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

            if estado == "aceptado":
                self.total_aceptados += 1
                self._overlay_texto  = "ACCESO PERMITIDO"
                self._overlay_color  = (30, 200, 60)    # BGR verde
            else:
                self.total_denegados += 1
                self._overlay_texto  = "ACCESO DENEGADO"
                self._overlay_color  = (40, 40, 220)    # BGR rojo

            self._overlay_frames = self._overlay_duracion

            if self.on_resultado:
                nombre = self.nombres.get(user_id, "Desconocido")
                self.on_resultado(nombre, confianza, estado)

        except Exception as e:
            print(f"❌ Error registrando acceso: {e}")
        finally:
            conn.close()

    def _recortar_rostro_seguro(self, img_gris, x, y, w, h):
        """Recorta con margen, valida y preprocesa. Devuelve array listo o None."""
        fh, fw = img_gris.shape[:2]

        # Añadir 10% de margen sin salirse del frame
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
        rostro = self.preprocesar(rostro)
        rostro = np.uint8(rostro)

        # Verificación final de shape y tipo
        if rostro.shape != (200, 200):
            return None
        if rostro.dtype != np.uint8:
            rostro = rostro.astype(np.uint8)

        return rostro

    def procesar_frame(self, frame):
        self._frame_counter += 1

        if self._frame_counter % self._procesar_cada == 0:
            gray      = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces_det = self.detector.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80)
            )
            self._ultimo_resultado = []

            if len(faces_det) > 0:
                # Hay cara — resetear contador de ausencia
                self._frames_sin_cara = 0
                self._cara_presente   = True

                for (x, y, w, h) in faces_det:
                    rostro = self._recortar_rostro_seguro(gray, x, y, w, h)

                    if rostro is None:
                        # Recorte inválido — ignorar esta cara
                        continue

                    try:
                        label_raw, conf_raw = self.recognizer.predict(rostro)
                    except cv2.error as e:
                        print(f"⚠️  predict falló (frame ignorado): {e}")
                        continue
                    except Exception as e:
                        print(f"⚠️  predict error inesperado: {e}")
                        continue

                    label, confianza = self._votar(label_raw, conf_raw)

                    if label is None:
                        # Aún acumulando votos — rectángulo naranja
                        self._ultimo_resultado.append(
                            (x, y, w, h, None, 0, (0, 165, 255)))
                        continue

                    if label == "Desconocido":
                        self.registrar_acceso(None, "denegado", conf_raw)
                        self._ultimo_resultado.append(
                            (x, y, w, h, "Desconocido", conf_raw, (40, 40, 220)))
                    else:
                        nombre = self.nombres.get(label, "Desconocido")
                        self.registrar_acceso(label, "aceptado", confianza)
                        self._ultimo_resultado.append(
                            (x, y, w, h, nombre, confianza or 0, (30, 200, 60)))

            else:
                # Sin cara
                self._cara_presente    = False
                self._frames_sin_cara += 1
                self._votos = []   # Limpiar votos acumulados

                if (self._frames_sin_cara >= self._umbral_sin_cara
                        and self.on_sin_cara):
                    self.on_sin_cara()
                    self._frames_sin_cara = 0   # reset para no disparar en loop

        # ── Dibujar rectángulos (sin nombre ni confianza) ─────────────────────
        for (x, y, w, h, nombre, conf, color) in self._ultimo_resultado:
            cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
            # Pequeños marcadores de esquina en lugar del borde completo
            sz = 14
            cv2.line(frame, (x, y),      (x+sz, y),      color, 3)
            cv2.line(frame, (x, y),      (x, y+sz),      color, 3)
            cv2.line(frame, (x+w, y),    (x+w-sz, y),    color, 3)
            cv2.line(frame, (x+w, y),    (x+w, y+sz),    color, 3)
            cv2.line(frame, (x, y+h),    (x+sz, y+h),    color, 3)
            cv2.line(frame, (x, y+h),    (x, y+h-sz),    color, 3)
            cv2.line(frame, (x+w, y+h),  (x+w-sz, y+h),  color, 3)
            cv2.line(frame, (x+w, y+h),  (x+w, y+h-sz),  color, 3)

        # ── Overlay ACEPTADO / DENEGADO ───────────────────────────────────────
        if self._overlay_frames > 0:
            self._dibujar_overlay(frame)
            self._overlay_frames -= 1

        return frame

    def _dibujar_overlay(self, frame):
        """Banner grande en la parte inferior del frame."""
        h, w = frame.shape[:2]
        texto  = self._overlay_texto
        color  = self._overlay_color   # BGR
        alpha  = min(1.0, self._overlay_frames / 8)   # fade-out suave al final

        # Fondo semitransparente
        overlay = frame.copy()
        bar_h   = 56
        cv2.rectangle(overlay, (0, h - bar_h), (w, h), color, -1)
        cv2.addWeighted(overlay, alpha * 0.55, frame, 1 - alpha * 0.55, 0, frame)

        # Texto centrado
        font  = cv2.FONT_HERSHEY_DUPLEX
        scale = 1.1
        thick = 2
        (tw, th), _ = cv2.getTextSize(texto, font, scale, thick)
        tx = (w - tw) // 2
        ty = h - bar_h + th + (bar_h - th) // 2
        cv2.putText(frame, texto, (tx, ty), font, scale, (255, 255, 255), thick, cv2.LINE_AA)

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

        print(f"🎥 Cámara iniciada · Umbral: {self.umbral_confianza}")
        print("q → salir  |  + → subir umbral  |  - → bajar umbral")
        print("="*55)

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame = self.procesar_frame(frame)

            cv2.putText(frame,
                        f"Umbral: {self.umbral_confianza}  |  +/- para ajustar",
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
                self.umbral_confianza = max(0, self.umbral_confianza - 5)
                self._votos = []
                print(f"🎯 Umbral bajado → {self.umbral_confianza}")

        cap.release()
        cv2.destroyAllWindows()
        print("👋 Sistema cerrado")


if __name__ == "__main__":
    reconocedor = ReconocerFacial()
    reconocedor.iniciar()