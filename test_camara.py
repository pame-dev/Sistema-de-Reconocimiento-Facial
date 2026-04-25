import cv2
import time
import os
import sys
import numpy as np

# Agregar ruta del proyecto
_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)


def main():
    print("🚀 Iniciando prueba de cámara con OpenCV + Haar Cascade...")
    print(f"   Compatible con Windows y Raspberry Pi | LBPH Ready")

    try:
        # ── Inicializar VideoCapture ──────────────────────────────────────
        # En Raspberry Pi: usa Camera Module 3
        # En Windows: usa webcam integrada
        cap = cv2.VideoCapture(0)

        if not cap.isOpened():
            print("❌ Error: No se pudo abrir la cámara")
            return

        print("⏳ Iniciando cámara...")
        time.sleep(2)  # Estabilizar sensor

        # ── Cargar detector Haar Cascade ────────────────────────────────
        haar_cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        haar_face = cv2.CascadeClassifier(haar_cascade_path)

        if haar_face.empty():
            print("❌ Error: No se pudo cargar Haar Cascade")
            return

        print("✅ Cámara lista y Haar Cascade cargado")
        print("   Presiona ESC para salir")
        print("   Presiona ESPACIO para capturar frame de prueba")

        frame_count = 0
        start_time = time.time()

        while True:
            # Capturar frame
            ret, frame = cap.read()
            if not ret:
                print("❌ Error: No se pudo capturar frame")
                break

            # Convertir a escala de grises para detección
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Detectar rostros
            faces = haar_face.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(30, 30),
                flags=cv2.CASCADE_SCALE_IMAGE
            )

            # Dibujar rectángulos alrededor de rostros detectados
            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                cv2.putText(frame, "Rostro", (x, y-10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            # Información en pantalla
            frame_count += 1
            elapsed = time.time() - start_time
            fps = frame_count / elapsed if elapsed > 0 else 0

            info_text = f"FPS: {fps:.1f} | Rostros: {len(faces)}"
            cv2.putText(frame, info_text, (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

            # Mostrar frame
            cv2.imshow("Test Camara - OpenCV", frame)

            # Controles
            key = cv2.waitKey(1) & 0xFF
            if key == 27:  # ESC
                print("\n🛑 Cerrando...")
                break
            elif key == 32:  # ESPACIO
                filename = f"debug_fotos/test_frame_{int(time.time())}.jpg"
                os.makedirs("debug_fotos", exist_ok=True)
                cv2.imwrite(filename, frame)
                print(f"✅ Frame guardado: {filename}")

        cap.release()
        cv2.destroyAllWindows()

        print(f"👋 Test finalizado")
        print(f"   Frames capturados: {frame_count}")
        print(f"   Tiempo total: {elapsed:.1f}s")
        print(f"   FPS promedio: {fps:.1f}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()