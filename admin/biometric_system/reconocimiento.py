# reconocimiento.py
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

        # Reconocedor LBPH con parámetros optimizados
        self.recognizer = cv2.face.LBPHFaceRecognizer_create(
            radius=2,       # Mayor radio = más contexto por píxel
            neighbors=12,   # Más vecinos = más robusto al ruido
            grid_x=10,      # Más celdas = más detalle espacial
            grid_y=10
        )

        # Detector Haar Cascade
        self.detector = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )

        self.nombres          = {}
        self.umbral_confianza = 80

        # ── Votación múltiple ──────────────────────────────────────────────
        # Acumula predicciones de varios frames antes de decidir
        self._votos           = []
        self._frames_votar    = 7   # cuántos frames se promedian
        self._ultimo_label    = None

        # ── Anti-spam de accesos ───────────────────────────────────────────
        # Evita registrar el mismo acceso 30 veces por segundo
        self._ultimo_registro      = {}   # {user_id: datetime}
        self._cooldown_segundos    = 5    # mínimo entre registros del mismo usuario

        # ── Rendimiento ───────────────────────────────────────────────────
        # Procesar solo 1 de cada N frames para ahorrar CPU
        self._frame_counter   = 0
        self._procesar_cada   = 2   # procesa 1 frame sí, 1 no

        # Último frame de detección (se reutiliza en frames saltados)
        self._ultimo_resultado = []  # lista de (x,y,w,h,nombre,confianza,color)

    # ── Base de datos ──────────────────────────────────────────────────────

    def get_db(self):
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            return conn
        except sqlite3.Error as e:
            print(f"❌ Error conectando a DB: {e}")
            return None

    # ── Preprocesamiento de imagen ─────────────────────────────────────────

    def preprocesar(self, img_gris):
        """
        Mejora la imagen antes de reconocer:
        - CLAHE: ecualización adaptativa del histograma (mejora contraste local)
        - Filtro bilateral: reduce ruido conservando bordes
        """
        # CLAHE — mejora iluminación sin sobreexponer
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        img = clahe.apply(img_gris)

        # Filtro bilateral — suaviza sin borrar bordes del rostro
        img = cv2.bilateralFilter(img, d=9, sigmaColor=75, sigmaSpace=75)

        return img

    # ── Preparar datos de entrenamiento ───────────────────────────────────

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

        print(f"📸 Procesando {len(resultados)} registros biométricos...")

        for row in resultados:
            user_id       = row[0]
            nombre_completo = f"{row[1]} {row[2] or ''} {row[3] or ''}".strip()
            self.nombres[user_id] = nombre_completo

            imagen_bytes = row[4]
            if imagen_bytes:
                nparr = np.frombuffer(imagen_bytes, np.uint8)
                img   = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)

                if img is not None:
                    img = cv2.resize(img, (200, 200))
                    img = self.preprocesar(img)   # ← preprocesamiento también en entrenamiento
                    faces.append(img)
                    labels.append(user_id)
                    print(f"  ✓ {nombre_completo}")

        return faces, labels

    # ── Entrenamiento ──────────────────────────────────────────────────────

    def entrenar(self):
        print("🔄 Cargando datos desde la base de datos...")
        faces, labels = self.preparar_datos()

        if len(faces) == 0:
            print("❌ No hay datos para entrenar. Registra usuarios con fotos primero.")
            return False

        print(f"🔄 Entrenando con {len(faces)} imágenes de {len(set(labels))} usuarios...")
        self.recognizer.train(faces, np.array(labels))
        self.recognizer.save('modelo_entrenado.yml')

        with open('nombres.pkl', 'wb') as f:
            pickle.dump(self.nombres, f)

        print(f"✅ Modelo entrenado con {len(set(labels))} usuarios")
        return True

    # ── Votación múltiple ──────────────────────────────────────────────────

    def _votar(self, label, confianza):
        """
        Acumula predicciones y devuelve la decisión solo cuando hay
        suficientes votos. Evita aceptar un rostro por un solo frame
        con buena suerte.
        """
        self._votos.append((label, confianza))

        if len(self._votos) < self._frames_votar:
            return None, None  # Aún acumulando votos

        # Tomar decisión con los últimos N votos
        votos_recientes = self._votos[-self._frames_votar:]
        labels_validos  = [l for l, c in votos_recientes if c < self.umbral_confianza]

        if not labels_validos:
            self._votos = []
            return "Desconocido", None

        # El label más votado entre los válidos
        label_ganador   = Counter(labels_validos).most_common(1)[0][0]
        confianza_media = np.mean([c for l, c in votos_recientes if l == label_ganador])

        self._votos = []  # Resetear para la siguiente ronda
        return label_ganador, confianza_media

    # ── Anti-spam de accesos ───────────────────────────────────────────────

    def _puede_registrar(self, user_id):
        """Devuelve True si pasó suficiente tiempo desde el último registro."""
        ahora   = datetime.now()
        key     = user_id if user_id is not None else "desconocido"
        ultimo  = self._ultimo_registro.get(key)

        if ultimo is None:
            return True

        return (ahora - ultimo).total_seconds() >= self._cooldown_segundos

    def registrar_acceso(self, user_id, estado, confianza):
        if not self._puede_registrar(user_id):
            return  # Cooldown activo, no registrar

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

            key = user_id if user_id is not None else "desconocido"
            self._ultimo_registro[key] = datetime.now()

            print(f"📝 Acceso registrado: {estado} — Confianza: {confianza:.1f}")

        except Exception as e:
            print(f"❌ Error registrando acceso: {e}")
        finally:
            conn.close()

    # ── Reconocimiento en tiempo real ──────────────────────────────────────

    def iniciar(self):
        print("="*50)
        print("🚀 SISTEMA DE RECONOCIMIENTO FACIAL")
        print("="*50)

        # Cargar modelo existente o entrenar
        try:
            self.recognizer.read('modelo_entrenado.yml')
            with open('nombres.pkl', 'rb') as f:
                self.nombres = pickle.load(f)
            print(f"✅ Modelo cargado — {len(self.nombres)} usuarios")
        except:
            print("🔄 Sin modelo guardado, entrenando...")
            if not self.entrenar():
                return

        # Iniciar cámara
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("❌ No se pudo abrir la cámara")
            return

        # Resolución reducida para mejor rendimiento en Raspberry Pi
        cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        print("🎥 Cámara iniciada")
        print(f"🎯 Umbral: {self.umbral_confianza} | Votos: {self._frames_votar} frames")
        print("   q → salir | + → umbral mayor | - → umbral menor | r → reentrenar")
        print("="*50)

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            self._frame_counter += 1

            # ── Procesar solo cada N frames ──
            if self._frame_counter % self._procesar_cada == 0:
                gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                gray  = self.preprocesar(gray)

                faces = self.detector.detectMultiScale(
                    gray,
                    scaleFactor=1.1,
                    minNeighbors=5,
                    minSize=(80, 80)
                )

                self._ultimo_resultado = []

                for (x, y, w, h) in faces:
                    rostro = gray[y:y+h, x:x+w]
                    rostro = cv2.resize(rostro, (200, 200))

                    label_raw, conf_raw = self.recognizer.predict(rostro)
                    label, confianza    = self._votar(label_raw, conf_raw)

                    if label is None:
                        # Aún acumulando votos — mostrar "analizando"
                        self._ultimo_resultado.append((x, y, w, h, "Analizando...", 0, (255, 165, 0)))
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

                    self._ultimo_resultado.append((x, y, w, h, nombre, confianza or 0, color))

            # ── Dibujar resultados (en todos los frames) ──
            for (x, y, w, h, nombre, confianza, color) in self._ultimo_resultado:
                cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)

                texto = f"{nombre} ({confianza:.1f})" if confianza else nombre
                cv2.putText(frame, texto, (x, y - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.75, color, 2)

            # HUD superior
            cv2.putText(frame, f"Umbral: {self.umbral_confianza}", (10, 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)
            cv2.putText(frame, f"Votos: {len(self._votos)}/{self._frames_votar}", (10, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, (200, 200, 200), 1)

            cv2.imshow('Reconocimiento Facial — Sentinel System', frame)

            # Teclas
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key in (ord('+'), ord('=')):
                self.umbral_confianza += 5
                print(f"🎯 Umbral → {self.umbral_confianza}")
            elif key in (ord('-'), ord('_')):
                self.umbral_confianza = max(0, self.umbral_confianza - 5)
                print(f"🎯 Umbral → {self.umbral_confianza}")
            elif key == ord('r'):
                print("🔄 Reentrenando modelo...")
                self.entrenar()

        cap.release()
        cv2.destroyAllWindows()
        print("👋 Sistema cerrado")


if __name__ == "__main__":
    reconocedor = ReconocerFacial()
    reconocedor.iniciar()