# PRUEBAS/crear_db.py
import sqlite3
import os

def crear_base_datos():
    """
    Crea la base de datos con todas las tablas.
    EJECUTA ESTO SOLO UNA VEZ (o cuando quieras resetear la BD).
    """

    print("🔄 Creando base de datos...")
    print("=" * 50)

    db_path = 'database/sistema_biometrico.db'
    os.makedirs('database', exist_ok=True)

    if os.path.exists(db_path):
        try:
            print(f"🗑️  Base de datos existente encontrada. Eliminando: {db_path}")
            os.remove(db_path)
        except Exception as e:
            print(f"⚠️  Error al eliminar la base de datos existente: {e}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 1. Tabla usuarios
    print("📦 Creando tabla: usuarios")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            idUsuario                     INTEGER PRIMARY KEY AUTOINCREMENT,
            apellidoPaternoUsuario        VARCHAR(50)  NOT NULL,
            apellidoMaternoUsuario        VARCHAR(50),
            nombreUsuario                 VARCHAR(50)  NOT NULL,
            matriculaUsuario              VARCHAR(20),
            rolUsuario                    VARCHAR(20)  NOT NULL,
            estadoUsuario                 VARCHAR(10)  DEFAULT 'activo',
            fechaNacimientoUsuario        DATE,
            direccionUsuario              VARCHAR(150),
            tipoSangreUsuario             VARCHAR(5),
            correoUsuario                 VARCHAR(100),
            FkIdUsuarioRegistro           INTEGER,
            FkIdUsuarioActualizacion      INTEGER,
            fechaHoraRegistroUsuario      DATETIME     DEFAULT CURRENT_TIMESTAMP,
            fechaHoraActualizacionUsuario DATETIME     DEFAULT CURRENT_TIMESTAMP,
            labelLBPH                     INTEGER,
            telefonoUsuario               VARCHAR(20)
        )
    ''')

    # 2. Tabla alumnos
    print("📦 Creando tabla: alumnos")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alumnos (
            fkIdUsuario    INTEGER PRIMARY KEY,
            gradoAlumno    VARCHAR(10),
            grupoAlumno    VARCHAR(10),
            facultadAlumno VARCHAR(100),
            carreraAlumno  VARCHAR(100),
            FOREIGN KEY (fkIdUsuario) REFERENCES usuarios(idUsuario)
        )
    ''')

    # 3. Tabla maestros
    print("📦 Creando tabla: maestros")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS maestros (
            fkIdUsuario              INTEGER PRIMARY KEY,
            gradoImpartidoMaestro    VARCHAR(20),
            materiaImpartidaMaestro  VARCHAR(100),
            FOREIGN KEY (fkIdUsuario) REFERENCES usuarios(idUsuario)
        )
    ''')

    # 4. Tabla personal_escolar
    print("📦 Creando tabla: personal_escolar")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS personal_escolar (
            fkIdUsuario            INTEGER PRIMARY KEY,
            telefonoPersonalEscolar VARCHAR(20),
            correoPersonalEscolar  VARCHAR(100),
            puestoPersonalEscolar  VARCHAR(50),
            areaPersonalEscolar    VARCHAR(50),
            FOREIGN KEY (fkIdUsuario) REFERENCES usuarios(idUsuario)
        )
    ''')

    # 5. Tabla biometria
    print("📦 Creando tabla: biometria")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS biometria (
            idBiometria                       INTEGER PRIMARY KEY AUTOINCREMENT,
            fkIdUsuario                       INTEGER NOT NULL,
            encodeBiometria                   BLOB,
            fechaHoraRegistroBiometria        DATETIME DEFAULT CURRENT_TIMESTAMP,
            fechaHoraActualizacionBiometria   DATETIME DEFAULT CURRENT_TIMESTAMP,
            fkIdUsuarioRegistroBiometria      INTEGER,
            fkIdUsuarioActualizacionBiometria INTEGER,
            FOREIGN KEY (fkIdUsuario) REFERENCES usuarios(idUsuario)
        )
    ''')

    # 6. Tabla accesos
    # CAMBIO: se agrega fotoAcceso BLOB para almacenar la foto capturada
    # en el momento del intento de acceso denegado.
    print("📦 Creando tabla: accesos")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS accesos (
            idAcceso               INTEGER PRIMARY KEY AUTOINCREMENT,
            fkIdUsuario            INTEGER,
            fechaHoraIntentoAcceso DATETIME DEFAULT CURRENT_TIMESTAMP,
            estado_acceso          VARCHAR(10) NOT NULL,
            confianzaAcceso        FLOAT       NOT NULL,
            umbralConfianzaUsado   FLOAT,
            fotoAcceso             BLOB,
            FOREIGN KEY (fkIdUsuario) REFERENCES usuarios(idUsuario)
        )
    ''')

    # Índices
    print("📦 Creando índices...")
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_matricula ON usuarios(matriculaUsuario)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_label     ON usuarios(labelLBPH)')

    conn.commit()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tablas = cursor.fetchall()

    print("\n" + "=" * 50)
    print("✅ BASE DE DATOS CREADA EXITOSAMENTE")
    print("=" * 50)
    print(f"📍 Ubicación: {db_path}")
    print(f"📊 Tablas creadas ({len(tablas)}):")

    for tabla in tablas:
        cursor.execute(f"SELECT COUNT(*) FROM {tabla[0]}")
        count = cursor.fetchone()[0]
        print(f"   - {tabla[0]}: {count} registros")

    conn.close()

    with open('database/.gitkeep', 'w') as f:
        pass


def migrar_columna_foto():
    """
    Si ya tienes una BD existente y NO quieres recrearla desde cero,
    ejecuta esta función para agregar solo la columna fotoAcceso.
    SQLite ignora el ALTER TABLE si la columna ya existe (gracias al try/except).
    """
    db_path = 'database/sistema_biometrico.db'
    if not os.path.exists(db_path):
        print("❌ No se encontró la base de datos. Ejecuta crear_base_datos() primero.")
        return

    conn = sqlite3.connect(db_path)
    try:
        conn.execute("ALTER TABLE accesos ADD COLUMN fotoAcceso BLOB")
        conn.commit()
        print("✅ Columna fotoAcceso agregada a la tabla accesos.")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            print("ℹ️  La columna fotoAcceso ya existe, no se hizo nada.")
        else:
            print(f"❌ Error: {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    import sys
    if "--migrar" in sys.argv:
        migrar_columna_foto()
    else:
        crear_base_datos()