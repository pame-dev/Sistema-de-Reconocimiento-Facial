import cv2

def main():
    print("🚀 Probando cámara IMX708 (Raspberry Pi 5)...")

    pipeline = (
        "libcamerasrc ! "
        "video/x-raw, width=640, height=480, framerate=30/1 ! "
        "videoconvert ! appsink"
    )

    cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)

    if not cap.isOpened():
        print("❌ No se pudo abrir la cámara")
        print("👉 Posibles causas:")
        print("   - OpenCV sin soporte GStreamer")
        print("   - GStreamer no instalado")
        print("   - Pipeline incorrecto")
        return

    print("✅ Cámara abierta correctamente")
    print("Presiona ESC para salir")

    while True:
        ret, frame = cap.read()

        if not ret:
            print("❌ No se pudo leer frame")
            break

        cv2.imshow("Camara IMX708 - Raspberry Pi 5", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == 27:  # ESC
            break

    cap.release()
    cv2.destroyAllWindows()
    print("👋 Prueba terminada")

if __name__ == "__main__":
    main()