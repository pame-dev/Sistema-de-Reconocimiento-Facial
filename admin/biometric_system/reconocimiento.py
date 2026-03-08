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

        self.recognizer = cv2.face.LBPHFaceRecognizer_create(
            radius=1,
            neighbors=8,
            grid_x=8,
            grid_y=8
        )

        self.detector = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )

        self.nombres          = {}
        self.umbral_confianza = 110  # arrancamos muy permisivo, ajustamos después

        self._votos           = []
        self._frames_votar    = 5
        self._ultimo_registro = {}
        self._cooldown_segundos = 5
        self._frame_counter   = 0
        self._procesar_cada   = 2
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
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        img = clahe.apply(img_gris)
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

        # Guardar primeras 5 fotos para diagnóstico
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

            # DEBUG: guardar las primeras 5 sin modificar
            if idx < 5:
                ruta = f"debug_fotos/foto_{idx}_user{user_id}_ORIGINAL.jpg"
                cv2.imwrite(ruta, img)
                print(f"  💾 {ruta} — shape: {img.shape}, min: {img.min()}, max: {img.max()}")

            img = cv2.resize(img, (200, 200))
            img = self.preprocesar(img)

            # DEBUG: guardar las primeras 5 ya procesadas
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
        self.recognizer.save('modelo_entrenado.yml')

        with open('nombres.pkl', 'wb') as f:
            pickle.dump(self.nombres, f)

        print(f"✅ Modelo entrenado con {len(set(labels))} usuarios")
        return True

    def _votar(self, label, confianza):
        self._votos.append((label, confianza))

        # Mantener solo los últimos N votos (ventana deslizante, NO resetear)
        if len(self._votos) > self._frames_votar:
            self._votos = self._votos[-self._frames_votar:]

        if len(self._votos) < self._frames_votar:
            return None, None  # Aún calentando

        labels_validos = [l for l, c in self._votos if c < self.umbral_confianza]

        if len(labels_validos) < self._frames_votar // 2:
            return "Desconocido", None

        label_ganador   = Counter(labels_validos).most_common(1)[0][0]
        confianza_media = np.mean([c for l, c in self._votos if l == label_ganador])

        # NO resetear self._votos — ventana deslizante mantiene el estado
        return label_ganador, confianza_media

    def _puede_registrar(self, user_id):
        ahora  = datetime.now()
        key    = user_id if user_id is not None else "desconocido"
        ultimo = self._ultimo_registro.get(key)
        if ultimo is None:
            return True
        return (ahora - ultimo).total_seconds() >= self._cooldown_segundos

    def registrar_acceso(self, user_id, estado, confianza):
        # Solo registrar si es un usuario diferente al último registrado
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
        print("="*50)
        print("🚀 SISTEMA DE RECONOCIMIENTO FACIAL")
        print("="*50)

        # Siempre reentrenar para forzar debug_fotos
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
        print(f"🎯 Umbral: {self.umbral_confianza} | Votos: {self._frames_votar} frames")
        print("   q → salir | + → umbral mayor | - → umbral menor")
        print("="*50)

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            self._frame_counter += 1

            if self._frame_counter % self._procesar_cada == 0:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                # NO preprocesar el frame completo — solo el recorte del rostro

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
                    rostro = self.preprocesar(rostro)  # solo aquí, una vez

                    label_raw, conf_raw = self.recognizer.predict(rostro)
                    print(f"🔍 DEBUG — label: {label_raw}, confianza: {conf_raw:.1f}")

                    label, confianza = self._votar(label_raw, conf_raw)

                    if label is None:
                        self._ultimo_resultado.append(
                            (x, y, w, h, "Analizando...", 0, (255, 165, 0)))
                        continue

                    if label == "Desconocido":
                        nombre = "Desconocido"
                        color  = (0, 0, 255)
                        self.registrar_acceso(None, "denegado", conf_raw)
                        print(f"❌ Desconocido ({conf_raw:.1f})")
                    else:
                        nombre = self.nombres.get(label, "Desconocido")
                        color  = (0, 255, 0)
                        self.registrar_acceso(label, "aceptado", confianza)
                        print(f"✅ {nombre} ({confianza:.1f})")

                    self._ultimo_resultado.append(
                        (x, y, w, h, nombre, confianza or 0, color))

            for (x, y, w, h, nombre, confianza, color) in self._ultimo_resultado:
                cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
                texto = f"{nombre} ({confianza:.1f})" if confianza else nombre
                cv2.putText(frame, texto, (x, y - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.75, color, 2)

            cv2.putText(frame, f"Umbral: {self.umbral_confianza}", (10, 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)
            cv2.putText(frame, f"Votos: {len(self._votos)}/{self._frames_votar}", (10, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, (200, 200, 200), 1)

            cv2.imshow('Reconocimiento Facial — Sentinel System', frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key in (ord('+'), ord('=')):
                self.umbral_confianza += 10
                print(f"🎯 Umbral → {self.umbral_confianza}")
            elif key in (ord('-'), ord('_')):
                self.umbral_confianza = max(0, self.umbral_confianza - 10)
                print(f"🎯 Umbral → {self.umbral_confianza}")

        cap.release()
        cv2.destroyAllWindows()
        print("👋 Sistema cerrado")


if __name__ == "__main__":
    reconocedor = ReconocerFacial()
    reconocedor.iniciar()