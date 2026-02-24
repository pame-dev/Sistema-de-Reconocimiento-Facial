# views/nuevo_registro_view.py
import tkinter as tk
from tkinter import messagebox, ttk
import cv2
from PIL import Image, ImageTk
import sqlite3
import os
from datetime import datetime
import threading
import sys
import numpy as np

# Añadir la carpeta raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import COLORS, get_db

class NuevoRegistroView:
    """Vista para registrar nuevos usuarios en el sistema"""
    
    def __init__(self, parent):
        self.parent = parent
        self.container = tk.Frame(parent, bg=COLORS['white'])
        self.container.pack(fill="both", expand=True, padx=30, pady=30)
        
        self.camara = None
        self.capturando = False
        self.fotos_tomadas = 0
        self.fotos_necesarias = 20
        self.user_id = None
        
        self.crear_interfaz()
    
    def crear_interfaz(self):
        """Crea todos los elementos de la interfaz"""
        
        # Título de la sección
        tk.Label(
            self.container,
            text="📝 Nuevo Registro de Usuario",
            font=("Arial", 20, "bold"),
            bg=COLORS['white'],
            fg=COLORS['text_dark']
        ).pack(pady=(0, 20), anchor="w")
        
        # Frame para el formulario y la cámara
        main_frame = tk.Frame(self.container, bg=COLORS['white'])
        main_frame.pack(fill="both", expand=True)
        
        # === FORMULARIO DE DATOS (Izquierda) ===
        form_frame = tk.Frame(main_frame, bg=COLORS['white'], width=400)
        form_frame.pack(side="left", fill="both", expand=True, padx=(0, 20))
        form_frame.pack_propagate(False)
        
        # Campos del formulario
        self.crear_formulario(form_frame)
        
        # === ÁREA DE CÁMARA (Derecha) ===
        self.cam_frame = tk.Frame(main_frame, bg=COLORS['content_bg'], relief="solid", borderwidth=1)
        self.cam_frame.pack(side="right", fill="both", expand=True)
        
        # Label para mostrar el video
        self.video_label = tk.Label(self.cam_frame, bg=COLORS['content_bg'])
        self.video_label.pack(expand=True, padx=10, pady=10)
        
        # Frame para controles de cámara
        cam_controls = tk.Frame(self.cam_frame, bg=COLORS['content_bg'])
        cam_controls.pack(fill="x", padx=10, pady=10)
        
        self.btn_iniciar_cam = tk.Button(
            cam_controls,
            text="📷 Iniciar Cámara",
            bg=COLORS['primary'],
            fg=COLORS['white'],
            font=("Arial", 10, "bold"),
            relief="flat",
            padx=20,
            pady=8,
            command=self.iniciar_camara
        )
        self.btn_iniciar_cam.pack(side="left", padx=5)
        
        self.btn_capturar = tk.Button(
            cam_controls,
            text="📸 Capturar Foto",
            bg=COLORS['header'],
            fg=COLORS['white'],
            font=("Arial", 10, "bold"),
            relief="flat",
            padx=20,
            pady=8,
            state="disabled",
            command=self.capturar_foto
        )
        self.btn_capturar.pack(side="left", padx=5)
        
        self.btn_detener = tk.Button(
            cam_controls,
            text="⏹️ Detener",
            bg=COLORS['danger'],
            fg=COLORS['white'],
            font=("Arial", 10, "bold"),
            relief="flat",
            padx=20,
            pady=8,
            state="disabled",
            command=self.detener_camara
        )
        self.btn_detener.pack(side="left", padx=5)
        
        # Barra de progreso
        self.progreso_frame = tk.Frame(self.cam_frame, bg=COLORS['content_bg'])
        self.progreso_frame.pack(fill="x", padx=10, pady=10)
        
        self.progreso_label = tk.Label(
            self.progreso_frame,
            text="Fotos: 0/20",
            bg=COLORS['content_bg'],
            fg=COLORS['text_dark'],
            font=("Arial", 10)
        )
        self.progreso_label.pack(side="left", padx=5)
        
        self.progreso_bar = ttk.Progressbar(
            self.progreso_frame,
            length=200,
            maximum=20
        )
        self.progreso_bar.pack(side="left", padx=5)
        
        # Mensaje de instrucciones
        self.instrucciones_label = tk.Label(
            self.cam_frame,
            text="1. Completa el formulario\n2. Inicia la cámara\n3. Toma 20 fotos desde diferentes ángulos",
            bg=COLORS['content_bg'],
            fg=COLORS['text_gray'],
            font=("Arial", 10),
            justify="left"
        )
        self.instrucciones_label.pack(pady=10)
        
        # Botón guardar (inicialmente deshabilitado)
        self.btn_guardar = tk.Button(
            self.container,
            text="💾 Guardar Usuario",
            bg=COLORS['primary'],
            fg=COLORS['white'],
            font=("Arial", 12, "bold"),
            relief="flat",
            padx=30,
            pady=10,
            state="disabled",
            command=self.guardar_usuario
        )
        self.btn_guardar.pack(pady=20)
    
    def crear_formulario(self, parent):
        """Crea los campos del formulario"""
        
        campos = [
            ("Nombre:", "entry_nombre"),
            ("Apellido Paterno:", "entry_paterno"),
            ("Apellido Materno:", "entry_materno"),
            ("Matrícula:", "entry_matricula"),
            ("Teléfono:", "entry_telefono")
        ]
        
        self.entries = {}
        
        for i, (label_text, attr_name) in enumerate(campos):
            frame = tk.Frame(parent, bg=COLORS['white'])
            frame.pack(fill="x", pady=5)
            
            tk.Label(
                frame,
                text=label_text,
                bg=COLORS['white'],
                fg=COLORS['text_dark'],
                font=("Arial", 11),
                width=15,
                anchor="w"
            ).pack(side="left")
            
            entry = tk.Entry(
                frame,
                font=("Arial", 11),
                relief="solid",
                borderwidth=1
            )
            entry.pack(side="left", fill="x", expand=True, padx=(5, 0))
            self.entries[attr_name] = entry
        
        # Rol
        frame_rol = tk.Frame(parent, bg=COLORS['white'])
        frame_rol.pack(fill="x", pady=5)
        
        tk.Label(
            frame_rol,
            text="Rol:",
            bg=COLORS['white'],
            fg=COLORS['text_dark'],
            font=("Arial", 11),
            width=15,
            anchor="w"
        ).pack(side="left")
        
        self.rol_var = tk.StringVar(value="alumno")
        roles = ["alumno", "maestro", "personal", "admin"]
        
        rol_combo = ttk.Combobox(
            frame_rol,
            textvariable=self.rol_var,
            values=roles,
            font=("Arial", 11),
            state="readonly"
        )
        rol_combo.pack(side="left", fill="x", expand=True, padx=(5, 0))
    
    def iniciar_camara(self):
        """Inicia la cámara en un hilo separado"""
        try:
            self.camara = cv2.VideoCapture(0)
            if not self.camara.isOpened():
                messagebox.showerror("Error", "No se pudo abrir la cámara")
                return
            
            self.capturando = True
            self.btn_iniciar_cam.config(state="disabled")
            self.btn_capturar.config(state="normal")
            self.btn_detener.config(state="normal")
            
            self.instrucciones_label.config(
                text="📸 Toma 20 fotos desde diferentes ángulos\nPresiona 'Capturar Foto' para cada una"
            )
            
            self.actualizar_video()
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al iniciar cámara: {e}")
    
    def actualizar_video(self):
        """Actualiza el frame de video en la interfaz"""
        if self.capturando and self.camara is not None:
            ret, frame = self.camara.read()
            if ret:
                # Convertir de BGR a RGB
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Redimensionar para que quepa en el label
                height, width = frame_rgb.shape[:2]
                new_width = 400
                new_height = int((new_width / width) * height)
                frame_rgb = cv2.resize(frame_rgb, (new_width, new_height))
                
                # Dibujar guía para el rostro
                h, w = frame_rgb.shape[:2]
                cv2.rectangle(frame_rgb, (w//4, h//4), (3*w//4, 3*h//4), (0, 255, 0), 2)
                
                # Convertir a ImageTk
                img = Image.fromarray(frame_rgb)
                imgtk = ImageTk.PhotoImage(image=img)
                
                self.video_label.imgtk = imgtk
                self.video_label.config(image=imgtk)
            
            self.video_label.after(10, self.actualizar_video)
    
    def capturar_foto(self):
        """Captura una foto y la guarda temporalmente"""
        if self.camara is None or not self.capturando:
            return
        
        ret, frame = self.camara.read()
        if ret:
            self.fotos_tomadas += 1
            self.progreso_bar['value'] = self.fotos_tomadas
            self.progreso_label.config(text=f"Fotos: {self.fotos_tomadas}/20")
            
            # Guardar foto temporalmente en atributo de clase
            if not hasattr(self, 'fotos_temp'):
                self.fotos_temp = []
            
            # Extraer solo la región del rostro (mejor para entrenamiento)
            h, w = frame.shape[:2]
            rostro = frame[h//4:3*h//4, w//4:3*w//4]
            
            # Redimensionar
            rostro = cv2.resize(rostro, (200, 200))
            
            # Convertir a bytes
            _, buffer = cv2.imencode('.jpg', rostro)
            self.fotos_temp.append(buffer.tobytes())
            
            if self.fotos_tomadas >= 20:
                self.btn_capturar.config(state="disabled")
                self.instrucciones_label.config(
                    text="✅ ¡20 fotos capturadas!\nAhora puedes guardar el usuario"
                )
                # Habilitar botón guardar si hay datos
                self.verificar_datos_completos()
    
    def detener_camara(self):
        """Detiene la cámara"""
        self.capturando = False
        if self.camara is not None:
            self.camara.release()
            self.camara = None
        
        self.video_label.config(image='')
        self.btn_iniciar_cam.config(state="normal")
        self.btn_capturar.config(state="disabled")
        self.btn_detener.config(state="disabled")
    
    def verificar_datos_completos(self):
        """Verifica si todos los datos están completos"""
        nombre = self.entries['entry_nombre'].get().strip()
        paterno = self.entries['entry_paterno'].get().strip()
        
        if nombre and paterno and hasattr(self, 'fotos_temp') and len(self.fotos_temp) >= 20:
            self.btn_guardar.config(state="normal")
    
    def guardar_usuario(self):
        """Guarda el usuario y las fotos en la base de datos"""
        try:
            # Obtener datos del formulario
            nombre = self.entries['entry_nombre'].get().strip().upper()
            paterno = self.entries['entry_paterno'].get().strip().upper()
            materno = self.entries['entry_materno'].get().strip().upper()
            matricula = self.entries['entry_matricula'].get().strip()
            telefono = self.entries['entry_telefono'].get().strip()
            rol = self.rol_var.get()
            
            if not nombre or not paterno:
                messagebox.showwarning("Campos incompletos", "Nombre y Apellido Paterno son obligatorios")
                return
            
            if not hasattr(self, 'fotos_temp') or len(self.fotos_temp) < 20:
                messagebox.showwarning("Fotos insuficientes", "Debes tomar 20 fotos")
                return
            
            # Guardar en BD
            conn = get_db()
            cursor = conn.cursor()
            
            # Insertar usuario
            cursor.execute("""
                INSERT INTO usuarios (
                    nombreUsuario, apellidoPaternoUsuario, apellidoMaternoUsuario,
                    matriculaUsuario, rolUsuario, estadoUsuario, telefonoUsuario
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (nombre, paterno, materno, matricula, rol, 'activo', telefono))
            
            user_id = cursor.lastrowid
            
            # Guardar fotos
            ahora = datetime.now()
            for foto_bytes in self.fotos_temp:
                cursor.execute("""
                    INSERT INTO biometria (
                        fkIdUsuario, encodeBiometria,
                        fechaHoraRegistroBiometria, fechaHoraActualizacionBiometria
                    ) VALUES (?, ?, ?, ?)
                """, (user_id, foto_bytes, ahora, ahora))
            
            conn.commit()
            conn.close()
            
            messagebox.showinfo(
                "Éxito",
                f"✅ Usuario {nombre} {paterno} registrado con {len(self.fotos_temp)} fotos"
            )
            
            # Limpiar formulario
            self.limpiar_formulario()
            self.detener_camara()
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al guardar: {e}")
    
    def limpiar_formulario(self):
        """Limpia el formulario después de guardar"""
        for entry in self.entries.values():
            entry.delete(0, tk.END)
        
        self.fotos_tomadas = 0
        self.progreso_bar['value'] = 0
        self.progreso_label.config(text="Fotos: 0/20")
        
        if hasattr(self, 'fotos_temp'):
            delattr(self, 'fotos_temp')
        
        self.btn_guardar.config(state="disabled")
        self.btn_capturar.config(state="disabled")
        
        self.instrucciones_label.config(
            text="1. Completa el formulario\n2. Inicia la cámara\n3. Toma 20 fotos desde diferentes ángulos"
        )
    
    def __del__(self):
        """Destructor para asegurar que la cámara se libera"""
        if self.camara is not None:
            self.camara.release()