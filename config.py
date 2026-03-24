import sqlite3
import os

LIGHT_COLORS = {
    'primary':      '#4CAF50',
    'primary_dark': '#45a049',
    'header':       '#1a2744',
    'header_hover': '#2a3a5c',
    'sidebar':      '#1a2744',
    'sidebar_hover':'#2a3a5c',
    'danger':       '#e74c3c',
    'danger_dark':  '#c0392b',
    'background':   '#f0f2f5',
    'white':        '#ffffff',
    'text_dark':    '#1e2a3a',
    'text_gray':    '#6b7a8d',
    'text_light':   '#95a5a6',
    'content_bg':   '#e4e8ef',
    'info':         '#2563eb',
    'card_bg':      '#ffffff',
    'border':       '#d1d9e6',
    'accent':       '#F59E0B',
    'cam_bg':       '#e8eef8',
    'cam_border':   '#a8c0e8',
    'bar_bg':       '#ffffff',
    'bar_border':   '#d1d9e6',
    'info_bar_bg':  '#f4f7fc',
    'tree_bg':      '#ffffff',
    'tree_fg':      '#1e2a3a',
    'tree_head_bg': '#e4e8ef',
    'tree_head_fg': '#1e2a3a',
    'tree_sel_bg':  '#2563eb',
    'tree_sel_fg':  '#ffffff',
    'tree_aceptado_bg': '#e8f5e9',
    'tree_aceptado_fg': '#1b5e20',
    'tree_denegado_bg': '#fdecea',
    'tree_denegado_fg': '#b71c1c',
}

DARK_COLORS = {
    'primary':      '#34d399',
    'primary_dark': '#10b981',
    'header':       '#060d1a',
    'header_hover': '#0f1e36',
    'sidebar':      '#060d1a',
    'sidebar_hover':'#0f1e36',
    'danger':       '#f87171',
    'danger_dark':  '#ef4444',
    'background':   '#0d1117',
    'white':        '#cdd6e0',
    'text_dark':    '#e2e8f0',
    'text_gray':    '#8b9cb0',
    'text_light':   '#4a5568',
    'content_bg':   '#161b22',
    'info':         '#60a5fa',
    'card_bg':      '#161b22',
    'border':       '#21293a',
    'accent':       '#fbbf24',
    'cam_bg':       '#0d1117',
    'cam_border':   '#21293a',
    'bar_bg':       '#060d1a',
    'bar_border':   '#21293a',
    'info_bar_bg':  '#0d1117',
    'tree_bg':      '#161b22',
    'tree_fg':      '#e2e8f0',
    'tree_head_bg': '#0d1117',
    'tree_head_fg': '#8b9cb0',
    'tree_sel_bg':  '#1d4ed8',
    'tree_sel_fg':  '#ffffff',
    'tree_aceptado_bg': '#0d2117',
    'tree_aceptado_fg': '#34d399',
    'tree_denegado_bg': '#1a0d0d',
    'tree_denegado_fg': '#f87171',
}

CURRENT_THEME = "light"

COLORS: dict = dict(LIGHT_COLORS)


def get_colors() -> dict:
    return COLORS


def toggle_theme():
    global CURRENT_THEME
    CURRENT_THEME = "dark" if CURRENT_THEME == "light" else "light"
    nueva = DARK_COLORS if CURRENT_THEME == "dark" else LIGHT_COLORS
    COLORS.update(nueva)
    import customtkinter as ctk
    ctk.set_appearance_mode("dark" if CURRENT_THEME == "dark" else "light")


WINDOW_WIDTH  = 900
WINDOW_HEIGHT = 600
SIDEBAR_WIDTH = 250
HEADER_HEIGHT = 60

ASSETS_PATH = "assets"
LOGO_FILE   = "sentinelSystemLogo.png"
ICON_FILE   = "sentinelSystemIcono.png"

DB_PATH = os.path.join(os.path.dirname(__file__), 'database', 'sistema_biometrico.db')


def get_db():
    try:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        print(f"✅ Conectado a: {DB_PATH}")
        return conn
    except sqlite3.Error as e:
        print(f"❌ Error conectando a DB: {e}")
        return None


def test_connection():
    conn = get_db()
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tablas = cursor.fetchall()
        print(f"📊 Tablas encontradas: {len(tablas)}")
        conn.close()
        return True
    return False