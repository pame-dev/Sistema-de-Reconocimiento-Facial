import cv2
import numpy as np


class DeteccionMixin:

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