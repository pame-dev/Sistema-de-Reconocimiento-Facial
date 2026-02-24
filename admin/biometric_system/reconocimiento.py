# reconocimiento.py
import cv2
import numpy as np
import sqlite3
import os
from datetime import datetime
import pickle

class ReconocerFacial:
    def __init__(self, db_path='database/sistema_biometrico.db'):
        self.db_path = db_path
        # Inicializar el reconocedor LBPH
        self.recognizer = cv2.face.LBPHFaceRecognizer_create()
        # Cargar el clasificador de rostros
        self.detector = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.nombres = {}
        self.umbral_confianza = 80  # Valor más bajo = más estricto

    def get_db(self):
        """Conectar a la base de datos"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            return conn
        except sqlite3.Error as e:
            print(f"❌ Error conectando a DB: {e}")
            return None

    def preparar_datos(self):
        """
        Obtiene los datos de la imagen y las organiza en una lista.
        """
        conn = self.get_db()
        if not conn:
            print("❌ No se pudo conectar a la base de datos")
            return [], []
        
        cursor = conn.cursor()
        
        # Consulta para obtener usuarios con sus fotos
        cursor.execute("""
            SELECT 
                u.idUsuario,
                u.nombreUsuario,
                u.apellidoPaternoUsuario,
                u.apellidoMaternoUsuario,
                b.encodeBiometria
            FROM usuarios u
            INNER JOIN biometria b ON u.idUsuario = b.fkIdUsuario
            WHERE b.encodeBiometria IS NOT NULL
        """)
        
        resultados = cursor.fetchall()
        conn.close()
        
        faces = []
        labels = []
        self.nombres = {}
        
        print(f"📸 Procesando {len(resultados)} registros biométricos...")
        
        for row in resultados:
            user_id = row[0]
            nombre = row[1]
            ap_paterno = row[2] if row[2] else ''
            ap_materno = row[3] if row[3] else ''
            
            nombre_completo = f"{nombre} {ap_paterno} {ap_materno}".strip()
            self.nombres[user_id] = nombre_completo
            
            # Procesar la imagen (está como BLOB en la BD)
            imagen_bytes = row[4]
            if imagen_bytes:
                # Convertir bytes a imagen
                nparr = np.frombuffer(imagen_bytes, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
                
                if img is not None:
                    # Redimensionar para uniformidad
                    img = cv2.resize(img, (200, 200))
                    faces.append(img)
                    labels.append(user_id)
                    print(f"  ✓ Cargada: {nombre_completo}")
        
        return faces, labels

    def entrenar(self):
        """Entrena el modelo con los datos de la BD"""
        print("🔄 Cargando datos desde la base de datos...")
        faces, labels = self.preparar_datos()
        
        if len(faces) > 0:
            print(f"🔄 Entrenando con {len(faces)} imágenes...")
            self.recognizer.train(faces, np.array(labels))
            
            # Guardar el modelo
            self.recognizer.save('modelo_entrenado.yml')
            with open('nombres.pkl', 'wb') as f:
                pickle.dump(self.nombres, f)
            
            print(f"✅ Modelo entrenado con {len(set(labels))} usuarios")
            return True
        else:
            print("❌ No hay datos para entrenar")
            print("   Necesitas registrar usuarios con fotos primero")
            return False

    def registrar_acceso(self, user_id, estado, confianza):
        """Registra el intento de acceso en la BD"""
        conn = self.get_db()
        if not conn:
            return
        
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO accesos (fkIdUsuario, estado_acceso, confianzaAcceso, umbralConfianzaUsado)
                VALUES (?, ?, ?, ?)
            """, (user_id, estado, confianza, self.umbral_confianza))
            
            conn.commit()
            print(f"📝 Acceso registrado: {estado} - Confianza: {confianza:.1f}")
            
        except Exception as e:
            print(f"❌ Error registrando acceso: {e}")
        finally:
            conn.close()

    def iniciar(self):
        """Inicia el reconocimiento facial"""
        print("="*50)
        print("🚀 SISTEMA DE RECONOCIMIENTO FACIAL")
        print("="*50)
        
        # Intentar cargar modelo existente
        try:
            self.recognizer.read('modelo_entrenado.yml')
            with open('nombres.pkl', 'rb') as f:
                self.nombres = pickle.load(f)
            print(f"✅ Modelo cargado con {len(self.nombres)} usuarios")
        except:
            print("🔄 No hay modelo guardado, entrenando...")
            if not self.entrenar():
                print("❌ No se pudo entrenar. Saliendo...")
                return
        
        # Iniciar cámara
        cap = cv2.VideoCapture(0)
        
        if not cap.isOpened():
            print("❌ No se pudo abrir la cámara")
            print("   Verifica que la cámara esté conectada")
            return
        
        print("🎥 Cámara iniciada correctamente")
        print(f"🎯 Umbral de confianza: {self.umbral_confianza}")
        print("   Presiona 'q' para salir")
        print("   Presiona '+' para aumentar umbral (menos estricto)")
        print("   Presiona '-' para disminuir umbral (más estricto)")
        print("="*50)
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Convertir a escala de grises
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Detectar rostros
            faces = self.detector.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(100, 100)
            )
            
            # Procesar cada rostro detectado
            for (x, y, w, h) in faces:
                # Extraer y preparar el rostro
                rostro = gray[y:y+h, x:x+w]
                rostro = cv2.resize(rostro, (200, 200))
                
                # Predecir
                label, confidence = self.recognizer.predict(rostro)
                
                # Determinar si es reconocido
                if confidence < self.umbral_confianza:
                    nombre = self.nombres.get(label, "Desconocido")
                    color = (0, 255, 0)  # Verde
                    estado = "aceptado"
                    print(f"✅ Reconocido: {nombre} ({confidence:.1f})")
                    self.registrar_acceso(label, estado, confidence)
                else:
                    nombre = "Desconocido"
                    color = (0, 0, 255)  # Rojo
                    estado = "denegado"
                    print(f"❌ No reconocido: Label {label} ({confidence:.1f})")  
                    self.registrar_acceso(None, estado, confidence)

                
                # Dibujar rectángulo y texto
                cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
                
                # Mostrar nombre y confianza
                texto = f"{nombre} ({confidence:.1f})"
                cv2.putText(frame, texto, (x, y-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
                
                # Mostrar umbral
                cv2.putText(frame, f"Umbral: {self.umbral_confianza}", (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # Mostrar frame
            cv2.imshow('Reconocimiento Facial', frame)
            
            # Manejar teclas
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('+') or key == ord('='):
                self.umbral_confianza += 5
                print(f"🎯 Umbral aumentado a: {self.umbral_confianza}")
            elif key == ord('-') or key == ord('_'):
                self.umbral_confianza = max(0, self.umbral_confianza - 5)
                print(f"🎯 Umbral disminuido a: {self.umbral_confianza}")
        
        cap.release()
        cv2.destroyAllWindows()
        print("👋 Sistema cerrado")

# Punto de entrada principal
if __name__ == "__main__":
    # Crear instancia del reconocedor
    reconocedor = ReconocerFacial()
    
    # Ejecutar el reconocimiento
    reconocedor.iniciar()