import cv2
import numpy as np
from collections import Counter


class ReconocimientoMixin:

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


            # ── DEBUG temporal ──
            print(f"DEBUG predicciones: {[(l, round(c,1)) for l, c in predicciones]}")
            print(f"DEBUG tolerancia: {self.tolerancia}")
            # ───────────────────
            mejor_label, mejor_conf = min(predicciones, key=lambda it: it[1])

            labels      = [l for l, _ in predicciones]
            label       = Counter(labels).most_common(1)[0][0]
            dists_label = [c for l, c in predicciones if l == label]
            conf = float(min(dists_label))

            if label == -1:
                return "Desconocido", conf
            if conf <= self.tolerancia:
                return label, conf
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