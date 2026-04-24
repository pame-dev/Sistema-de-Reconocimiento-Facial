# agregar_fotos.py (recomendado)
# Agrega fotos biométricas a un usuario existente, guardando SOLO el rostro detectado (no un recorte fijo).
import sqlite3
import cv2
import numpy as np
import os
import sys
import time
from datetime import datetime

_PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from camera import Camera


DB_PATH = os.path.join(_PROJECT_ROOT, "database", "sistema_biometrico.db")

# Detectores Haar (mismo enfoque que el motor)
_HAAR_FRONTAL = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
_HAAR_ALT     = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_alt2.xml")
_HAAR_PERFIL  = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_profileface.xml")


def _detectar_caras(frame_gray):
    """
    Devuelve lista de (x,y,w,h). Intenta frontal/alt/perfil y filtro por tamaño.
    """
    h, w = frame_gray.shape[:2]
    min_size = (max(70, int(w * 0.12)), max(70, int(h * 0.12)))

    # Más minNeighbors => menos falsos positivos pero puede fallar con poca luz.
    configs = [
        (_HAAR_FRONTAL, dict(scaleFactor=1.1, minNeighbors=6, minSize=min_size), False),
        (_HAAR_ALT,     dict(scaleFactor=1.1, minNeighbors=5, minSize=min_size), False),
        (_HAAR_PERFIL,  dict(scaleFactor=1.1, minNeighbors=5, minSize=min_size), False),
        (_HAAR_PERFIL,  dict(scaleFactor=1.1, minNeighbors=5, minSize=min_size), True),
    ]

    resultados = []
    for det, params, flipped in configs:
        gray = cv2.flip(frame_gray, 1) if flipped else frame_gray
        caras = det.detectMultiScale(gray, **params)
        if len(caras) == 0:
            continue
        for (x, y, cw, ch) in caras:
            if flipped:
                x = w - (x + cw)

            # filtrar bordes
            cx = x + cw // 2
            cy = y + ch // 2
            if not (int(w * 0.08) < cx < int(w * 0.92) and int(h * 0.08) < cy < int(h * 0.92)):
                continue

            # filtrar ratio raro
            r = cw / float(ch)
            if not (0.6 < r < 1.6):
                continue

            resultados.append((x, y, cw, ch))

        if resultados:
            break

    return resultados


def _extraer_rostro(frame_bgr, rect):
    """
    Recorta rostro con un pequeño margen y lo retorna.
    """
    x, y, w, h = rect
    fh, fw = frame_bgr.shape[:2]
    pad = int(min(w, h) * 0.10)
    x1 = max(0, x - pad)
    y1 = max(0, y - pad)
    x2 = min(fw, x + w + pad)
    y2 = min(fh, y + h + pad)
    rostro = frame_bgr[y1:y2, x1:x2]
    return rostro


def _rostro_apto(rostro_bgr):
    """
    Valida calidad mínima: nitidez e iluminación.
    Retorna (ok, msg).
    """
    try:
        gray = cv2.cvtColor(rostro_bgr, cv2.COLOR_BGR2GRAY)

        # nitidez (Laplacian var). Sube si está borroso.
        nitidez = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        if nitidez < 40.0:
            return False, f"Borroso (nitidez={nitidez:.1f})"

        # brillo promedio
        brillo = float(np.mean(gray))
        if brillo < 45.0:
            return False, "Muy oscuro (más luz)"
        if brillo > 215.0:
            return False, "Muy iluminado (baja luz)"

        return True, "OK"
    except Exception:
        return True, "OK"


def agregar_fotos_usuario():
    """Agrega más fotos a un usuario existente (guardando rostro detectado)."""

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("=" * 60)
    print("📸 AGREGAR FOTOS A USUARIO (guardando rostro detectado)")
    print("=" * 60)

    # Mostrar usuarios existentes + total fotos
    cursor.execute("""
        SELECT u.idUsuario,
               u.nombreUsuario,
               u.apellidoPaternoUsuario,
               u.estadoUsuario,
               COUNT(b.idBiometria) as num_fotos
        FROM usuarios u
        LEFT JOIN biometria b ON u.idUsuario = b.fkIdUsuario
        GROUP BY u.idUsuario
        ORDER BY u.idUsuario ASC
    """)
    usuarios = cursor.fetchall()

    if not usuarios:
        print("❌ No hay usuarios registrados")
        conn.close()
        return

    print("\n📋 Usuarios disponibles:")
    for (uid, nom, pat, estado, nf) in usuarios:
        print(f"   {uid}: {nom} {pat}  | estado={estado}  | fotos={nf}")

    user_id = input("\n👉 ID del usuario para agregar fotos: ").strip()
    if not user_id.isdigit():
        print("❌ ID inválido")
        conn.close()
        return
    user_id = int(user_id)

    cursor.execute("""
        SELECT nombreUsuario, apellidoPaternoUsuario, apellidoMaternoUsuario, estadoUsuario
        FROM usuarios WHERE idUsuario = ?
    """, (user_id,))
    row = cursor.fetchone()
    if not row:
        print("❌ Usuario no encontrado")
        conn.close()
        return

    nombre_completo = f"{row[0]} {row[1]} {row[2] or ''}".strip()
    estado = row[3]
    print(f"\n👤 Usuario: {nombre_completo} (estado={estado})")

    # Config de captura
    try:
        objetivo = input("🎯 ¿Cuántas fotos quieres agregar? (default 40): ").strip()
        objetivo = int(objetivo) if objetivo else 40
        objetivo = max(5, min(objetivo, 300))
    except Exception:
        objetivo = 40

    print("\n🎯 Consejos:")
    print(" - Gira un poco la cara (izq/der), sube/baja mentón, cambia expresión.")
    print(" - Mantén la cara centrada y cerca.")
    print(" - Presiona ESPACIO para guardar 1 foto (si la calidad es OK).")
    print(" - Presiona A para modo automático (captura cada ~0.25s si OK).")
    print(" - Presiona Q para terminar.\n")

    # Iniciar cámara (wrapper unificado)
    try:
        cap = Camera()
        cap.start()
        time.sleep(0.6)
    except Exception as e:
        print(f"❌ No se pudo abrir la cámara: {e}")
        conn.close()
        return

    fotos_agregadas = 0
    auto = False
    last_auto = 0.0
    AUTO_DELAY = 0.25

    try:
        while True:
            frame = cap.read()
            if frame is None:
                continue

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            caras = _detectar_caras(gray)
            face_rect = None
            if caras:
                face_rect = max(caras, key=lambda r: r[2] * r[3])
                x, y, w, h = face_rect
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 220, 0), 2)
            else:
                cv2.putText(frame, "No se detecta cara", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (30, 30, 220), 2)

            cv2.putText(frame, f"Usuario: {nombre_completo}", (10, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            cv2.putText(frame, f"Agregadas: {fotos_agregadas}/{objetivo}  Auto={'ON' if auto else 'OFF'}", (10, 90),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2)
            cv2.putText(frame, "ESPACIO=guardar | A=auto | Q=salir", (10, 120),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 2)

            cv2.imshow("Agregar Fotos - Sentinel System", frame)

            key = cv2.waitKey(1) & 0xFF
            ahora = time.time()

            def _guardar_rostro_actual():
                nonlocal fotos_agregadas
                if face_rect is None:
                    print("⚠️  No hay cara detectada.")
                    return False

                rostro = _extraer_rostro(frame, face_rect)
                if rostro.size == 0:
                    print("⚠️  Recorte vacío.")
                    return False

                # Normalizar tamaño para consistencia
                rostro = cv2.resize(rostro, (200, 200))

                ok, msg = _rostro_apto(rostro)
                if not ok:
                    print(f"⚠️  Foto descartada: {msg}")
                    return False

                # Guardar JPEG con buena calidad
                ok_enc, buffer = cv2.imencode(".jpg", rostro, [cv2.IMWRITE_JPEG_QUALITY, 92])
                if not ok_enc:
                    print("⚠️  No se pudo codificar imagen.")
                    return False

                imagen_bytes = buffer.tobytes()
                cursor.execute("""
                    INSERT INTO biometria (fkIdUsuario, encodeBiometria, fechaHoraRegistroBiometria, fechaHoraActualizacionBiometria)
                    VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """, (user_id, imagen_bytes))
                conn.commit()

                fotos_agregadas += 1
                print(f"✅ Foto {fotos_agregadas}/{objetivo} agregada ({msg})")
                return True

            if key == ord('a'):
                auto = not auto
                print("🔁 Auto:", "ON" if auto else "OFF")

            if key == ord('q'):
                break

            if key == ord(' '):
                _guardar_rostro_actual()

            # Auto-captura si está ON
            if auto and fotos_agregadas < objetivo and (ahora - last_auto) >= AUTO_DELAY:
                if _guardar_rostro_actual():
                    last_auto = ahora

            if fotos_agregadas >= objetivo:
                print("🎉 Objetivo alcanzado.")
                break

    finally:
        try:
            cap.stop()
        except Exception:
            pass
        cv2.destroyAllWindows()

    cursor.execute("SELECT COUNT(*) FROM biometria WHERE fkIdUsuario = ?", (user_id,))
    total_fotos = cursor.fetchone()[0]
    conn.close()

    print("\n" + "=" * 60)
    print("📊 RESUMEN")
    print(f"   Usuario: {nombre_completo}")
    print(f"   Fotos agregadas: {fotos_agregadas}")
    print(f"   Total de fotos del usuario: {total_fotos}")
    print("=" * 60)

    # Reentrenar (recomendado)
    respuesta = input("\n🔄 ¿Quieres reentrenar el modelo ahora? (s/n): ").strip().lower()
    if respuesta == 's':
        print("\n🔄 Reentrenando modelo...")
        from reconocimiento import ReconocerFacial
        rec = ReconocerFacial()
        rec.cargar_o_reentrenar()
        print("✅ Modelo reentrenado (o cargado si no detectó cambios).")


if __name__ == "__main__":
    agregar_fotos_usuario()