# config.py
import sqlite3
import os

# Configuración General del Sistema

# Paleta de colores de la aplicación
COLORS = {
    'primary': '#4CAF50',          # Verde principal
    'primary_dark': '#45a049',     # Verde oscuro (hover)
    'header': '#2c3e50',           # Azul oscuro header
    'header_hover': '#34495e',     # Azul hover
    'sidebar': '#34495e',          # Fondo menú lateral
    'sidebar_hover': '#2c3e50',    # Hover menú lateral
    'danger': '#e74c3c',           # Rojo para acciones peligrosas
    'danger_dark': '#c0392b',      # Rojo oscuro (hover)
    'background': '#f5f5f5',       # Fondo general
    'white': '#ffffff',            # Blanco
    'text_dark': '#2c3e50',        # Texto oscuro
    'text_gray': '#7f8c8d',        # Texto gris
    'text_light': '#95a5a6',       # Texto claro
    'content_bg': '#ecf0f1',       # Fondo de contenido
    'info': '#17A2B8'
}

# Dimensiones de ventana
WINDOW_WIDTH = 900
WINDOW_HEIGHT = 600
SIDEBAR_WIDTH = 250
HEADER_HEIGHT = 60

# Rutas de archivos
ASSETS_PATH = "assets"
LOGO_FILE = "sentinelSystemLogo.png"
ICON_FILE = "sentinelSystemIcono.png"

# Ruta a la base de datos (usando la carpeta que ya tienes)
DB_PATH = os.path.join(os.path.dirname(__file__), 'database', 'sistema_biometrico.db')

def get_db():
    """
    Obtiene una conexión a la base de datos
    Úsala cada vez que necesites conectar a la BD
    """
    try:
        # Asegurar que la carpeta database existe
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        
        # Conectar a la base de datos
        conn = sqlite3.connect(DB_PATH)
        
        # Esto hace que las filas se comporten como diccionarios
        conn.row_factory = sqlite3.Row
        
        print(f"✅ Conectado a: {DB_PATH}")
        return conn
        
    except sqlite3.Error as e:
        print(f"❌ Error conectando a DB: {e}")
        return None

def test_connection():
    """Prueba rápida de conexión"""
    conn = get_db()
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tablas = cursor.fetchall()
        print(f"📊 Tablas encontradas: {len(tablas)}")
        conn.close()
        return True
    return False