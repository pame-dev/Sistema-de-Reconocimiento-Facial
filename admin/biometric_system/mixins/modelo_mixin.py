import cv2
import numpy as np
import pickle
import os
from idiomas import t


class ModeloMixin:

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
            ORDER BY b.idBiometria ASC
        """)
        filas = cur.fetchall()
        conn.close()

        # ── LÍMITE: máximo 40 fotos por usuario para entrenar ──────────────────
        MAX_FOTOS_POR_USUARIO = 40
        conteo_por_usuario = {}

        faces_tmp    = []
        labels_tmp   = []
        nombres_tmp  = {}
        fallback_directo = 0

        print(t("procesando_imagenes"))

        for fila in filas:
            user_id = fila[0]

            # Saltar si ya alcanzó el límite
            if conteo_por_usuario.get(user_id, 0) >= MAX_FOTOS_POR_USUARIO:
                continue

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
                fh, fw = gray.shape[:2]

                if fw > 250 and fh > 250:
                    caras = self._detectar_caras(img, gray)
                    if len(caras) > 0:
                        x, y, w, h = max(caras, key=lambda c: c[2] * c[3])
                        pad = int(min(w, h) * 0.08)
                        x1  = max(0,  x - pad)
                        y1  = max(0,  y - pad)
                        x2  = min(fw, x + w + pad)
                        y2  = min(fh, y + h + pad)
                        rostro_gray = gray[y1:y2, x1:x2]
                        if rostro_gray.size == 0:
                            rostro_gray = gray
                    else:
                        fallback_directo += 1
                        rostro_gray = gray
                else:
                    rostro_gray = gray

                rostro_gray = cv2.resize(rostro_gray, (100, 100))
                rostro_gray = self._normalizar_rostro_gray(rostro_gray)

                faces_tmp.append(rostro_gray)
                labels_tmp.append(user_id)
                conteo_por_usuario[user_id] = conteo_por_usuario.get(user_id, 0) + 1

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
        print(f"  ✅ {len(ids_usados)} usuarios · {len(faces_tmp)} rostros (máx {MAX_FOTOS_POR_USUARIO}/usuario)")
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
        """Umbral fijo basado en comportamiento real observado de LBPH."""
        n_usuarios = len(self.nombres)

        # Basado en datos reales observados:
        # - distancias intra-clase en cámara: ~70-90
        # - necesitamos estar por encima del peor caso intra-clase
        if n_usuarios == 1:
            self.tolerancia = 90.0
        elif n_usuarios <= 3:
            self.tolerancia = 95.0
        else:
            self.tolerancia = 92.0

        # Respetar los límites configurados
        self.tolerancia = min(self._TOLERANCIA_MAX,
                            max(self._TOLERANCIA_MIN, self.tolerancia))
        print(f"🔧 Tolerancia fija a {self.tolerancia:.1f} · {n_usuarios} usuario(s)")