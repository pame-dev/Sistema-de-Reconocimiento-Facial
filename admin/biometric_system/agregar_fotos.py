# agregar_fotos.py
import sqlite3
import cv2
import numpy as np
import os
import sys

_PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from camera import Camera

def agregar_fotos_usuario():
    """Agrega más fotos a un usuario existente"""
    
    conn = sqlite3.connect('database/sistema_biometrico.db')
    cursor = conn.cursor()
    
    print("="*50)
    print("📸 AGREGAR FOTOS A USUARIO")
    print("="*50)
    
    # Mostrar usuarios existentes
    cursor.execute("""
        SELECT u.idUsuario, u.nombreUsuario, u.apellidoPaternoUsuario, 
               COUNT(b.idBiometria) as num_fotos
        FROM usuarios u
        LEFT JOIN biometria b ON u.idUsuario = b.fkIdUsuario
        GROUP BY u.idUsuario
    """)
    
    usuarios = cursor.fetchall()
    
    if not usuarios:
        print("❌ No hay usuarios registrados")
        conn.close()
        return
    
    print("\n📋 Usuarios disponibles:")
    for user in usuarios:
        print(f"   {user[0]}: {user[1]} {user[2]} - {user[3]} fotos actuales")
    
    # Seleccionar usuario
    user_id = input("\n👉 ID del usuario para agregar fotos: ")
    
    # Verificar que existe
    cursor.execute("SELECT nombreUsuario, apellidoPaternoUsuario FROM usuarios WHERE idUsuario = ?", (user_id,))
    user = cursor.fetchone()
    
    if not user:
        print("❌ Usuario no encontrado")
        conn.close()
        return
    
    nombre_completo = f"{user[0]} {user[1]}"
    
    print(f"\n📸 Agregando fotos para: {nombre_completo}")
    
    # Iniciar cámara (wrapper unificado Raspberry/Windows)
    try:
        cap = Camera()
        cap.start()
    except Exception as e:
        print(f"❌ No se pudo abrir la cámara: {e}")
        conn.close()
        return
    
    print("\n🎯 INSTRUCCIONES PARA MEJOR RECONOCIMIENTO:")
    print("   1. Toma fotos desde DIFERENTES ÁNGULOS:")
    print("      - Frente")
    print("      - Ligeramente izquierda")
    print("      - Ligeramente derecha")
    print("      - Arriba")
    print("      - Abajo")
    print("   2. Con DIFERENTES EXPRESIONES:")
    print("      - Serio")
    print("      - Sonriendo")
    print("      - Ojos abiertos/cerrados")
    print("   3. Con DIFERENTE ILUMINACIÓN:")
    print("      - Con luz")
    print("      - Sin mucha luz")
    print("\n   Presiona ESPACIO para tomar cada foto")
    print("   Presiona Q para terminar\n")
    
    fotos_agregadas = 0
    
    try:
        while True:
            frame = cap.read()
            if frame is None:
                continue
        
            h, w = frame.shape[:2]
        
            # Dibujar guía para el rostro
            cv2.rectangle(frame, (w//4, h//4), (3*w//4, 3*h//4), (255, 255, 0), 2)
        
            # Mostrar información
            cv2.putText(frame, f"Fotos agregadas: {fotos_agregadas}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(frame, f"Usuario: {nombre_completo}", (10, 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(frame, "Presiona ESPACIO para capturar", (10, 90),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            cv2.putText(frame, "Presiona Q para terminar", (10, 120),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
            cv2.imshow('Agregar Fotos - Reconocimiento Facial', frame)
        
            key = cv2.waitKey(1) & 0xFF
        
            if key == ord(' '):  # ESPACIO
                # Extraer solo la región del rostro (mejor para entrenamiento)
                rostro = frame[h//4:3*h//4, w//4:3*w//4]
            
                # Redimensionar a tamaño estándar
                rostro = cv2.resize(rostro, (200, 200))
            
                # Convertir a bytes
                _, buffer = cv2.imencode('.jpg', rostro)
                imagen_bytes = buffer.tobytes()
            
                # Guardar en BD
                cursor.execute("""
                    INSERT INTO biometria (fkIdUsuario, encodeBiometria)
                    VALUES (?, ?)
                """, (user_id, imagen_bytes))
            
                conn.commit()
                fotos_agregadas += 1
                print(f"✅ Foto {fotos_agregadas} agregada")
            
            elif key == ord('q'):
                break
    finally:
        cap.stop()
        cv2.destroyAllWindows()
    
    # Mostrar resumen
    cursor.execute("SELECT COUNT(*) FROM biometria WHERE fkIdUsuario = ?", (user_id,))
    total_fotos = cursor.fetchone()[0]
    
    print("\n" + "="*50)
    print(f"📊 RESUMEN")
    print(f"   Usuario: {nombre_completo}")
    print(f"   Fotos agregadas hoy: {fotos_agregadas}")
    print(f"   Total de fotos: {total_fotos}")
    print("="*50)
    
    conn.close()
    
    # Preguntar si quiere reentrenar ahora
    respuesta = input("\n🔄 ¿Quieres reentrenar el modelo ahora? (s/n): ")
    if respuesta.lower() == 's':
        print("\n🔄 Reentrenando modelo...")
        from reconocimiento import ReconocerFacial
        reconocedor = ReconocerFacial()
        reconocedor.entrenar()
        print("✅ Modelo reentrenado con nuevas fotos")

if __name__ == "__main__":
    agregar_fotos_usuario()