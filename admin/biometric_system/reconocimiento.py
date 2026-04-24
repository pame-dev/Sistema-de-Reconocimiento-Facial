import cv2
import numpy as np
import sqlite3
import os
import sys
import threading
from datetime import datetime, timedelta
import pickle
import hashlib
from collections import Counter
import time

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
    Reconocimiento:  LBPH (OpenCV) — histograma local de patrones binarios
    Persistencia:    modelo entrenado en .yml, datos en .pkl, sin reentrenar si no hay cambios
    """

    def __init__(self, db_path='database/sistema_biometrico.db'):
        self.db_path       = db_path
        self.project_root  = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.artifacts_dir = os.path.join(self.project_root, 'database')

        # Archivos de persistencia
        self.model_path = os.path.join(self.artifacts_dir, 'lbph_model.yml')
        self.data_path  = os.path.join(self.artifacts_dir, 'lbph_data.pkl')
        self.ids_hash_path  = os.path.join(self.artifacts_dir, 'ids_hash.pkl')
        self._modelo_version = 8

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

        # ── Reconocedor LBPH ───────────────────────────────────────────────────
        self.recognizer = cv2.face.LBPHFaceRecognizer_create()

        # ── Datos de reconocimiento ────────────────────────────────────────────
        self.nombres             = {}   # dict[int, str]    — user_id → nombre completo

        # ── Parámetros de reconocimiento ───────────────────────────────────────
        self.tolerancia           = 85.0   # distancia máxima para considerar match
        self._TOLERANCIA_MIN      = 70.0
        self._TOLERANCIA_MAX      = 130.0

        # ── Votación ──────────────────────────────────────────────────────────
        self._votos         = []   # list[(user_id|"Desconocido", distancia)]
        self._frames_votar  = 4
        self._procesar_cada = 2
        self._frame_counter = 0
        self._ultimo_resultado = []

        # ── Cooldown de registros en BD ────────────────────────────────────────
        self._ultimo_registro   = {}
        self._cooldown_segundos = 5

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
        self._ultimo_usuario_aceptado = None
        self._ultimo_aceptado_ts      = None
        self._ventana_recuperacion_seg = 20.0
        self._margen_recuperacion      = 10.0

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

        for detector, params, flipped in [
            (self._haar_frontal, dict(scaleFactor=1.1, minNeighbors=6, minSize=(80, 80)), False),
            (self._haar_alt,     dict(scaleFactor=1.1, minNeighbors=5, minSize=(70, 70)), False),
            (self._haar_perfil,  dict(scaleFactor=1.1, minNeighbors=5, minSize=(70, 70)), False),
            (self._haar_perfil,  dict(scaleFactor=1.1, minNeighbors=5, minSize=(70, 70)), True),
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
                break  # Basta con la primera detección confiable

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
                  AND u.estadoUsuario = 'activo'
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
        data = {
            'ids':         ids_set,
            'fingerprint': fingerprint,
        }
        with open(self.ids_hash_path, 'wb') as f:
            pickle.dump(data, f)

    def _borrar_archivos_modelo(self):
        for p in (self.model_path, self.data_path, self.ids_hash_path):
            try:
                os.remove(p)
            except Exception:
                pass

    def _cargar_modelo_lbph(self):
        """Compatibilidad OpenCV: algunos builds usan read, otros load."""
        if hasattr(self.recognizer, 'read'):
            self.recognizer.read(self.model_path)
            return
        if hasattr(self.recognizer, 'load'):
            self.recognizer.load(self.model_path)
            return
        raise AttributeError("LBPHFaceRecognizer no soporta read/load en este build")

    def _guardar_modelo_lbph(self):
        """Compatibilidad OpenCV: algunos builds usan write, otros save."""
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
        """
        Lee imágenes de la BD, extrae rostros en gris para LBPH
        y los guarda en self.faces / self.labels.
        Retorna True si hay al menos un rostro válido.
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

        faces_tmp = []
        labels_tmp = []
        nombres_tmp = {}
        fallback_directo = 0

        print(f"📸 Procesando {len(filas)} imágenes biométricas...")

        for fila in filas:
            user_id = fila[0]
            nombre_completo = f"{fila[1]} {fila[2] or ''} {fila[3] or ''}".strip()
            nombres_tmp[user_id] = nombre_completo

            imagen_bytes = fila[4]
            if not imagen_bytes:
                continue

            try:
                nparr = np.frombuffer(imagen_bytes, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                if img is None:
                    continue

                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                gray = cv2.equalizeHist(gray)

                # Detectar caras con Haar. Si no detecta, usar imagen completa
                # porque en este sistema muchas biometrías ya están recortadas.
                caras = self._detectar_caras(img, gray)
                if len(caras) > 0:
                    # Usar la cara más grande
                    x, y, w, h = max(caras, key=lambda x: x[2] * x[3])

                    # Recortar con margen
                    fh, fw = gray.shape[:2]
                    pad = int(min(w, h) * 0.08)
                    x1 = max(0, x - pad)
                    y1 = max(0, y - pad)
                    x2 = min(fw, x + w + pad)
                    y2 = min(fh, y + h + pad)

                    rostro_gray = gray[y1:y2, x1:x2]
                    if rostro_gray.size == 0:
                        continue
                else:
                    fallback_directo += 1
                    rostro_gray = gray

                # Redimensionar a 100x100 para consistencia
                rostro_gray = cv2.resize(rostro_gray, (100, 100))

                faces_tmp.append(rostro_gray)
                labels_tmp.append(user_id)

            except Exception as e:
                print(f"  ⚠️  Error procesando imagen user {user_id}: {e}")
                continue

        if not faces_tmp:
            print("❌ No se pudieron extraer rostros.")
            return False

        self.faces = faces_tmp
        self.labels = labels_tmp
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
        """
        Carga modelo LBPH desde disco si el conjunto de IDs no cambió.
        Si cambió (nuevo usuario, eliminado), regenera desde la BD.
        """
        ids_bd          = self._ids_en_bd()
        ids_modelo, fp_modelo = self._ids_en_modelo()
        fp_bd            = self._fingerprint_en_bd()

        if not ids_bd:
            print("⚠️  No hay usuarios activos con biometría en la BD")
            if self.on_status:
                self.on_status("Sin datos — registra usuarios primero")
            return False

        archivo_ok = os.path.exists(self.model_path) and os.path.exists(self.data_path)

        # Detectar cambios en usuarios o en imágenes biométricas existentes
        if archivo_ok and (ids_bd != ids_modelo or fp_bd != fp_modelo):
            nuevos     = ids_bd - ids_modelo
            eliminados = ids_modelo - ids_bd
            if nuevos:
                print(f"🔄 {len(nuevos)} usuario(s) nuevo(s) — regenerando modelo")
            if eliminados:
                print(f"🔄 {len(eliminados)} usuario(s) eliminado(s) — regenerando modelo")
            elif fp_bd != fp_modelo:
                print("🔄 Imagen(es) biométrica(s) actualizada(s) — regenerando modelo")
            self._borrar_archivos_modelo()
            archivo_ok = False

        if archivo_ok:
            try:
                self._cargar_modelo_lbph()
                with open(self.data_path, 'rb') as f:
                    data = pickle.load(f)
                self.nombres = data['nombres']
                ids_archivo = data['ids']
                self.tolerancia = float(data.get('tolerancia', self.tolerancia))
                modelo_version_archivo = int(data.get('modelo_version', 1))

                if modelo_version_archivo != self._modelo_version:
                    print("🔄 Versión de preprocesado cambiada — regenerando modelo...")
                    self._borrar_archivos_modelo()
                    return self._generar_y_guardar()

                # Doble verificación: IDs en el archivo vs BD
                if ids_archivo != ids_bd:
                    print("🔄 Modelo desincronizado con BD — regenerando...")
                    self._borrar_archivos_modelo()
                    return self._generar_y_guardar()

                print(f"✅ Modelo LBPH cargado · {len(self.nombres)} usuarios")
                if self.on_status:
                    self.on_status(f"Modelo listo · {len(self.nombres)} usuarios")
                return True

            except Exception as e:
                print(f"⚠️  Modelo corrupto ({e}) — regenerando...")
                self._borrar_archivos_modelo()

        return self._generar_y_guardar()

    def _generar_y_guardar(self):
        """Genera datos desde la BD, entrena LBPH y los persiste en disco."""
        if self.on_status:
            self.on_status("Generando modelo LBPH...")
        print("🔄 Generando modelo LBPH desde cero...")

        ok = self.preparar_datos()
        if not ok:
            return False

        # Entrenar el reconocedor LBPH
        self.recognizer.train(self.faces, np.array(self.labels, dtype=np.int32))

        os.makedirs(self.artifacts_dir, exist_ok=True)
        self._guardar_modelo_lbph()

        self._ajustar_tolerancia_post_entreno()

        data = {
            'nombres':    self.nombres,
            'ids':        set(self.labels),
            'tolerancia': self.tolerancia,
            'modelo_version': self._modelo_version,
        }
        with open(self.data_path, 'wb') as f:
            pickle.dump(data, f)

        self._guardar_ids_hash(set(self.labels), self._fingerprint_en_bd())

        print(f"✅ Modelo LBPH guardado · {len(self.nombres)} usuarios")
        if self.on_status:
            self.on_status(f"Modelo listo · {len(self.nombres)} usuarios")
        return True

    def _ajustar_tolerancia_post_entreno(self):
        """Ajusta la tolerancia automáticamente según los datos entrenados."""
        if not getattr(self, 'faces', None):
            return
        distancias = []
        for rostro in self.faces:
            try:
                _, conf = self.recognizer.predict(rostro)
                distancias.append(conf)
            except Exception:
                continue
        if not distancias:
            return
        umbral = float(np.percentile(distancias, 95)) + 20.0
        # Con pocos usuarios, evitar umbrales excesivamente permisivos.
        if len(self.nombres) <= 2:
            umbral = min(umbral, 92.0)
        self.tolerancia = min(self._TOLERANCIA_MAX,
                              max(self._TOLERANCIA_MIN, umbral))
        print(f"🔧 Tolerancia ajustada a {self.tolerancia:.1f} según datos de entrenamiento")

    # ─────────────────────────────────────────────────────────────────────────
    # Reconocimiento
    # ─────────────────────────────────────────────────────────────────────────
    def _reconocer_rostro(self, rostro_bgr):
        """
        Dado un recorte BGR del rostro detectado por Haar,
        extrae el rostro en gris y lo compara con el modelo LBPH.
        Retorna (user_id|"Desconocido", distancia).
        """
        try:
            gray_base = cv2.cvtColor(rostro_bgr, cv2.COLOR_BGR2GRAY)
            gray_base = cv2.resize(gray_base, (100, 100))

            variantes = [
                gray_base,
                cv2.equalizeHist(gray_base),
                cv2.GaussianBlur(cv2.equalizeHist(gray_base), (3, 3), 0),
            ]

            predicciones = []
            for variante in variantes:
                label_i, conf_i = self.recognizer.predict(variante)
                predicciones.append((label_i, float(conf_i)))

            # Elegir la etiqueta más estable entre variantes y usar distancia robusta.
            labels = [l for l, _ in predicciones]
            label = Counter(labels).most_common(1)[0][0]
            dists_label = [c for l, c in predicciones if l == label]
            conf = float(np.median(dists_label))

            if conf <= self.tolerancia:
                return label, conf

            # Histeresis de recuperacion: despues de un denegado, permitir
            # un margen corto solo si coincide con el ultimo usuario aceptado.
            if (self._ultimo_usuario_aceptado is not None
                    and label == self._ultimo_usuario_aceptado
                    and self._ultimo_aceptado_ts is not None):
                delta = (datetime.now() - self._ultimo_aceptado_ts).total_seconds()
                if (0 <= delta <= self._ventana_recuperacion_seg
                        and conf <= (self.tolerancia + self._margen_recuperacion)):
                    return label, conf
            return "Desconocido", conf

        except Exception as e:
            print(f"⚠️  Error en reconocimiento: {e}")
            return "Desconocido", 100.0

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
        if len(labels_validos) < int(self._frames_votar * 0.50):
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
        confianza = round(max(0.0, 100 - distancia), 2)
        hubo_cambio_estado = (self._ultimo_tipo != estado)

        if not self._puede_registrar(user_id):
            # Aunque no se escriba en BD por cooldown, mantener el estado vivo
            # para que la UI pueda volver a "aceptado" tras un "desconocido".
            self._ultimo_tipo = estado
            if hubo_cambio_estado:
                if estado == "aceptado":
                    self._overlay_texto  = "ACCESO PERMITIDO"
                    self._overlay_color  = (30, 200, 60)
                    self._overlay_frames = 10
                    self._votos = []
                    self._ultimo_usuario_aceptado = user_id
                    self._ultimo_aceptado_ts = datetime.now()
                else:
                    self._overlay_texto  = "ACCESO DENEGADO"
                    self._overlay_color  = (40, 40, 220)
                    self._overlay_frames = 8
                    self._votos = []

                if self.on_resultado:
                    nombre = self.nombres.get(user_id, "Desconocido")
                    self.on_resultado(nombre, confianza, estado)
            return

        conn = self.get_db()
        if not conn:
            return

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
                self._ultimo_usuario_aceptado = user_id
                self._ultimo_aceptado_ts = datetime.now()
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

                    # Limpiar votos solo cuando cambia entre dos identidades conocidas.
                    # No resetear por transiciones con "Desconocido" para no bloquear
                    # la recuperación inmediata tras una denegación.
                    if (label_anterior is not None and label_raw != label_anterior
                            and label_anterior != "Desconocido"
                            and label_raw != "Desconocido"):
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
                    f"Tolerancia: {self.tolerancia:.1f}  |  +/- ajustar  |  q salir",
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