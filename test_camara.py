from picamera2 import Picamera2
import cv2
import time


def main():
    print("🚀 Iniciando prueba con Picamera2...")

    try:
        picam2 = Picamera2()

        # Configuración (puedes cambiar resolución si quieres)
        config = picam2.create_preview_configuration(
            main={"format": "RGB888", "size": (640, 480)}
        )

        picam2.configure(config)

        print("⏳ Iniciando cámara...")
        picam2.start()

        # Pequeño delay para estabilizar
        time.sleep(2)

        print("✅ Cámara iniciada correctamente")
        print("Presiona ESC para salir")

        while True:
            frame = picam2.capture_array()

            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

            # (Opcional) efecto espejo
            frame = cv2.flip(frame, 1)

            cv2.imshow("Test Picamera2", frame)

            key = cv2.waitKey(1) & 0xFF
            if key == 27:  # ESC
                break

        print("🛑 Cerrando cámara...")
        picam2.stop()
        cv2.destroyAllWindows()
        print("👋 Test finalizado")

    except Exception as e:
        print("❌ Error:", e)


if __name__ == "__main__":
    main()