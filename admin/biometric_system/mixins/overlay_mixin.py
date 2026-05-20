import cv2


class OverlayMixin:

    def _dibujar_overlay(self, frame):
        h, w  = frame.shape[:2]
        texto = self._overlay_texto
        color = self._overlay_color
        alpha = min(1.0, self._overlay_frames / 8)

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