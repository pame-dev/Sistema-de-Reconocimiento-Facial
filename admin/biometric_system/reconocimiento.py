import cv2
import numpy as np
import sqlite3
import os
from datetime import datetime
import pickle
from collections import Counter


class ReconocerFacial:
    def __init__(self, db_path='database/sistema_biometrico.db'):
        self.db_path = db_path
        self.project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.artifacts_dir = os.path.join(self.project_root, 'database')
        self.model_path = os.path.join(self.artifacts_dir, 'modelo_entrenado.yml')
        self.names_path = os.path.join(self.artifacts_dir, 'nombres.pkl')

        self.recognizer = cv2.face.LBPHFaceRecognizer_create(
            radius=1,
            neighbors=8,
            grid_x=8,
            grid_y=8
        )

        self.detector = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )

        self.nombres = {}

        # ✅ CORRECCIÓN 1: Umbral subido a 95
        # Tus valores reales según el DEBUG son ~89-93
        # El umbral debe ser MAYOR que tu confianza para reconocerte
        self.umbral_confianza = 95

        self._votos = []
        self._frames_votar = 10
        self._ultimo_registro = {}
        self._cooldown_segundos = 5
        self._frame_counter = 0
        self._procesar_cada = 2
        self._ultimo_resultado = []
        self._ultimo_usuario_registrado = None

    def get_db(self):
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            return conn
        except sqlite3.Error as e:
            print(f"❌ Error conectando a DB: {e}")
            return None

    def preprocesar(self, img_gris):
        img = cv2.equalizeHist(img_gris)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        img = clahe.apply(img)
        img = cv2.bilateralFilter(img, d=9, sigmaColor=75, sigmaSpace=75)
        return img

    def preparar_datos(self):
        conn = self.get_db()
        if not conn:
            return [], []

        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                u.idUsuario,
                u.nombreUsuario,
                u.apellidoPaternoUsuario,
                u.apellidoMaternoUsuario,
                b.encodeBiometria
            FROM usuarios u
            INNER JOIN biometria b ON u.idUsuario = b.fkIdUsuario
            WHERE b.encodeBiometria IS NOT NULL
        """)
        resultados = cursor.fetchall()
        conn.close()

        faces, labels = [], []
        self.nombres = {}

        os.makedirs("debug_fotos", exist_ok=True)
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
                print(f"  ⚠️  idx {idx}: imdecode devolvió None")
                continue

            if idx < 5:
                ruta = f"debug_fotos/foto_{idx}_user{user_id}_ORIGINAL.jpg"
                cv2.imwrite(ruta, img)
                print(f"  💾 {ruta} — shape: {img.shape}, min: {img.min()}, max: {img.max()}")

            img = cv2.resize(img, (200, 200))
            img = self.preprocesar(img)

            if idx < 5:
                cv2.imwrite(f"debug_fotos/foto_{idx}_user{user_id}_PROCESADA.jpg", img)

            faces.append(img)
            labels.append(user_id)
            if idx < 10:
                print(f"  ✓ {nombre_completo}")

        print(f"  Total: {len(set(labels))} usuarios, {len(faces)} imágenes")
        return faces, labels

    def entrenar(self):
        print("🔄 Cargando datos desde la base de datos...")
        faces, labels = self.preparar_datos()

        if len(faces) == 0:
            print("❌ No hay datos para entrenar.")
            return False

        print(f"🔄 Entrenando con {len(faces)} imágenes de {len(set(labels))} usuarios...")
        self.recognizer.train(faces, np.array(labels))
        os.makedirs(self.artifacts_dir, exist_ok=True)
        self.recognizer.save(self.model_path)

        with open(self.names_path, 'wb') as f:
            pickle.dump(self.nombres, f)

        print(f"✅ Modelo entrenado con {len(set(labels))} usuarios")
        return True

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
        if user_id == self._ultimo_usuario_registrado:
            return

        conn = self.get_db()
        if not conn:
            return

        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO accesos (fkIdUsuario, estado_acceso, confianzaAcceso, umbralConfianzaUsado)
                VALUES (?, ?, ?, ?)
            """, (user_id, estado, confianza, self.umbral_confianza))
            conn.commit()
            self._ultimo_usuario_registrado = user_id
            print(f"📝 Acceso registrado: {estado} — Confianza: {confianza:.1f}")
        except Exception as e:
            print(f"❌ Error registrando acceso: {e}")
        finally:
            conn.close()

    def iniciar(self):
        print("="*55)
        print("🚀 SISTEMA DE RECONOCIMIENTO FACIAL — Sentinel System")
        print("="*55)

        print("🔄 Entrenando modelo...")
        if not self.entrenar():
            return

        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("❌ No se pudo abrir la cámara")
            return

        cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        print(f"🎥 Cámara iniciada")
        print(f"🎯 Umbral inicial: {self.umbral_confianza}")
        print("="*55)
        print("⌨️  CONTROLES — HAZ CLIC EN LA VENTANA DE LA CÁMARA PRIMERO:")
        print("   q     → salir")
        print("   +     → subir umbral (+5)")
        print("   -     → bajar umbral (-5)")
        print("="*55)
        print("📊 Tus valores de confianza vistos son ~89-93")
        print("   Umbral en 95 → deberías aparecer reconocida ahora.")
        print("   Si tus compañeras también pasan, baja el umbral con '-'")
        print("   hasta que solo tú seas reconocida.")
        print("="*55)

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            self._frame_counter += 1

            if self._frame_counter % self._procesar_cada == 0:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

                faces_det = self.detector.detectMultiScale(
                    gray,
                    scaleFactor=1.1,
                    minNeighbors=5,
                    minSize=(80, 80)
                )

                self._ultimo_resultado = []

                for (x, y, w, h) in faces_det:
                    rostro = gray[y:y+h, x:x+w]
                    rostro = cv2.resize(rostro, (200, 200))
                    rostro = self.preprocesar(rostro)

                    label_raw, conf_raw = self.recognizer.predict(rostro)

                    nombre_debug = self.nombres.get(label_raw, f"ID:{label_raw}")
                    pasa = conf_raw < self.umbral_confianza
                    estado_debug = "✅ PASA" if pasa else "❌ NO pasa"
                    print(f"🔍 {estado_debug} | {nombre_debug} | confianza: {conf_raw:.1f} | umbral: {self.umbral_confianza}")

                    label, confianza = self._votar(label_raw, conf_raw)

                    if label is None:
                        self._ultimo_resultado.append(
                            (x, y, w, h, "Analizando...", 0, (255, 165, 0)))
                        continue

                    if label == "Desconocido":
                        nombre = "Desconocido"
                        color  = (0, 0, 255)
                        self.registrar_acceso(None, "denegado", conf_raw)
                        print(f"🚫 Resultado final: Desconocido ({conf_raw:.1f})")
                    else:
                        nombre = self.nombres.get(label, "Desconocido")
                        color  = (0, 255, 0)
                        self.registrar_acceso(label, "aceptado", confianza)
                        print(f"✅ Resultado final: {nombre} ({confianza:.1f})")

                    self._ultimo_resultado.append(
                        (x, y, w, h, nombre, confianza or 0, color))

            for (x, y, w, h, nombre, confianza, color) in self._ultimo_resultado:
                cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
                texto = f"{nombre} ({confianza:.1f})" if confianza else nombre
                cv2.putText(frame, texto, (x, y - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.75, color, 2)

            # ✅ CORRECCIÓN 2: Aviso de foco en pantalla
            cv2.putText(frame, f"Umbral: {self.umbral_confianza}  |  Clic aqui, luego +/-",
                        (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 0), 2)
            cv2.putText(frame, f"Votos: {len(self._votos)}/{self._frames_votar}",
                        (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1)

            cv2.imshow('Reconocimiento Facial — Sentinel System', frame)

            # ✅ CORRECCIÓN 3: Capturar tanto caracteres ASCII como keycodes directos
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key in (ord('+'), ord('='), 43, 61):
                self.umbral_confianza += 5
                self._votos = []  # resetear votos para recalcular con nuevo umbral
                print(f"🎯 Umbral subido → {self.umbral_confianza}")
            elif key in (ord('-'), ord('_'), 45, 95):
                self.umbral_confianza = max(0, self.umbral_confianza - 5)
                self._votos = []  # resetear votos para recalcular con nuevo umbral
                print(f"🎯 Umbral bajado → {self.umbral_confianza}")

        cap.release()
        cv2.destroyAllWindows()
        print("👋 Sistema cerrado")


if __name__ == "__main__":
    reconocedor = ReconocerFacial()
    reconocedor.iniciar()
