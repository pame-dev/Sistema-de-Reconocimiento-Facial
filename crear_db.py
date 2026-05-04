# PRUEBAS/crear_db.py
import sqlite3
import os

def crear_base_datos():
    """
    Crea la base de datos con todas las tablas
    EJECUTA ESTO SOLO UNA VEZ
    """
    
    print("🔄 Creando base de datos...")
    print("="*50)
    
    # Ruta donde se creará la DB
    db_path = 'database/sistema_biometrico.db'

    # Asegurar que la carpeta existe
    os.makedirs('database', exist_ok=True)

    # Si existe la base de datos, eliminarla para recrear desde cero
    if os.path.exists(db_path):
        try:
            print(f"🗑️  Base de datos existente encontrada. Eliminando: {db_path}")
            os.remove(db_path)
        except Exception as e:
            print(f"⚠️  Error al eliminar la base de datos existente: {e}")

    # Conectar (esto crea el archivo si no existe)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. Tabla usuarios
    print("📦 Creando tabla: usuarios")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            idUsuario INTEGER PRIMARY KEY AUTOINCREMENT,
            apellidoPaternoUsuario VARCHAR(50) NOT NULL,
            apellidoMaternoUsuario VARCHAR(50),
            nombreUsuario VARCHAR(50) NOT NULL,
            matriculaUsuario VARCHAR(20),
            rolUsuario VARCHAR(20) NOT NULL,
            estadoUsuario VARCHAR(10) DEFAULT 'activo',
            fechaNacimientoUsuario DATE,
            direccionUsuario VARCHAR(150),
            tipoSangreUsuario VARCHAR(5),
            correoUsuario VARCHAR(100),
            FkIdUsuarioRegistro INTEGER,
            FkIdUsuarioActualizacion INTEGER,
            fechaHoraRegistroUsuario DATETIME DEFAULT CURRENT_TIMESTAMP,
            fechaHoraActualizacionUsuario DATETIME DEFAULT CURRENT_TIMESTAMP,
            labelLBPH INTEGER,
            telefonoUsuario VARCHAR(20)
        )
    ''')
    
    # 2. Tabla alumnos
    print("📦 Creando tabla: alumnos")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alumnos (
            fkIdUsuario INTEGER PRIMARY KEY,
            gradoAlumno VARCHAR(10),
            grupoAlumno VARCHAR(10),
            facultadAlumno VARCHAR(100),
            carreraAlumno VARCHAR(100),
            FOREIGN KEY (fkIdUsuario) REFERENCES usuarios(idUsuario)
        )
    ''')
    
    # 3. Tabla maestros
    print("📦 Creando tabla: maestros")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS maestros (
            fkIdUsuario INTEGER PRIMARY KEY,
            gradoImpartidoMaestro VARCHAR(20),
            materiaImpartidaMaestro VARCHAR(100),
            FOREIGN KEY (fkIdUsuario) REFERENCES usuarios(idUsuario)
        )
    ''')
    
    # 4. Tabla personal_escolar
    print("📦 Creando tabla: personal_escolar")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS personal_escolar (
            fkIdUsuario INTEGER PRIMARY KEY,
            telefonoPersonalEscolar VARCHAR(20),
            correoPersonalEscolar VARCHAR(100),
            puestoPersonalEscolar VARCHAR(50),
            areaPersonalEscolar VARCHAR(50),
            FOREIGN KEY (fkIdUsuario) REFERENCES usuarios(idUsuario)
        )
    ''')
    
    # 5. Tabla biometria
    print("📦 Creando tabla: biometria")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS biometria (
            idBiometria INTEGER PRIMARY KEY AUTOINCREMENT,
            fkIdUsuario INTEGER NOT NULL,
            encodeBiometria BLOB,
            fechaHoraRegistroBiometria DATETIME DEFAULT CURRENT_TIMESTAMP,
            fechaHoraActualizacionBiometria DATETIME DEFAULT CURRENT_TIMESTAMP,
            fkIdUsuarioRegistroBiometria INTEGER,
            fkIdUsuarioActualizacionBiometria INTEGER,
            FOREIGN KEY (fkIdUsuario) REFERENCES usuarios(idUsuario)
        )
    ''')
    
    # 6. Tabla accesos
    print("📦 Creando tabla: accesos")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS accesos (
            idAcceso INTEGER PRIMARY KEY AUTOINCREMENT,
            fkIdUsuario INTEGER,
            fechaHoraIntentoAcceso DATETIME DEFAULT CURRENT_TIMESTAMP,
            estado_acceso VARCHAR(10) NOT NULL,
            confianzaAcceso FLOAT NOT NULL,
            umbralConfianzaUsado FLOAT,
            FOREIGN KEY (fkIdUsuario) REFERENCES usuarios(idUsuario)
        )
    ''')
    
    # Crear índices
    print("📦 Creando índices...")
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_matricula ON usuarios(matriculaUsuario)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_label ON usuarios(labelLBPH)')
    
    # Guardar cambios
    conn.commit()
    
    # Verificar lo que se creó
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tablas = cursor.fetchall()
    
    print("\n" + "="*50)
    print("✅ BASE DE DATOS CREADA EXITOSAMENTE")
    print("="*50)
    print(f"📍 Ubicación: {db_path}")
    print(f"📊 Tablas creadas ({len(tablas)}):")
    
    for tabla in tablas:
        # Contar registros en cada tabla
        cursor.execute(f"SELECT COUNT(*) FROM {tabla[0]}")
        count = cursor.fetchone()[0]
        print(f"   - {tabla[0]}: {count} registros")
    
    conn.close()
    
    # Crear un archivo .gitkeep para mantener la carpeta en git (opcional)
    with open('database/.gitkeep', 'w') as f:
        pass

if __name__ == "__main__":
    crear_base_datos()