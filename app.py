import tkinter as tk #libreria grafica para crear interfaces de usuario
import customtkinter as ctk
import os #libreria para interactuar con el sistema operativo, como manejar archivos y rutas
import sys
import ctypes
import tempfile
import math
from PIL import Image, ImageTk
from config import WINDOW_WIDTH, WINDOW_HEIGHT, ASSETS_PATH, ICON_FILE # importamos configuraciones generales del sistema
from views.login_view import LoginView 
from views.main_view import MainView 
class SentinelApp:
    """Clase principal que maneja la aplicación y navegación entre vistas"""
    
    def __init__(self, root):  
        self.root = root
        self.root.sentinel_app = self
        self.root.title("UnimoraAccess - Sistema de Reconocimiento Facial")
        self.root.configure(fg_color="#F4F7FB")

        # Ajustar la ventana para una pantalla física de 7" en vertical
        try:
            self.set_size_for_physical_diagonal(7.0, orientation='vertical')
        except Exception:
            # fallback a valores de config si falla la detección
            self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
            self.desired_width = WINDOW_WIDTH
            self.desired_height = WINDOW_HEIGHT

        # Permitimos redimensionar por defecto
        self.root.resizable(True, True)

        self.center_window()
        
        # Contenedor principal donde se cargan las vistas
        self.main_container = ctk.CTkFrame(self.root, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True)
        
        self.show_login_view()
    
    def center_window(self):
        """Centra la ventana en el centro de la pantalla"""
        self.root.update_idletasks()
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        # Usa las dimensiones calculadas si existen
        width = getattr(self, 'desired_width', WINDOW_WIDTH)
        height = getattr(self, 'desired_height', WINDOW_HEIGHT)

        # No permitir que la ventana sea mayor que la pantalla
        width = min(width, max(100, screen_w - 8))
        height = min(height, max(100, screen_h - 8))

        x = max((screen_w // 2) - (width // 2), 0)
        y = max((screen_h // 2) - (height // 2), 0)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

    def set_size_for_physical_diagonal(self, diagonal_inches: float = 7.0, orientation: str = 'vertical'):
        """
        Calcula un tamaño de ventana (en píxeles) que corresponda aproximadamente
        a una diagonal física dada (en pulgadas) usando las mediciones del monitor.
        orientation: 'vertical' o 'horizontal'
        """
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        mmw = self.root.winfo_screenmmwidth()
        mmh = self.root.winfo_screenmmheight()

        # Estimar PPI (píxeles por pulgada)
        try:
            if mmw and mmh:
                screen_diag_mm = math.hypot(mmw, mmh)
                screen_diag_in = screen_diag_mm / 25.4
                screen_diag_px = math.hypot(sw, sh)
                ppi = screen_diag_px / screen_diag_in if screen_diag_in > 0 else self.root.winfo_fpixels('1i')
            else:
                # fallback a winfo_fpixels
                ppi = self.root.winfo_fpixels('1i')
        except Exception:
            ppi = self.root.winfo_fpixels('1i')

        desired_diag_px = diagonal_inches * ppi
        screen_diag_px = math.hypot(sw, sh)

        # Escala relativa (no exceder la pantalla completa)
        scale = min(1.0, desired_diag_px / max(1.0, screen_diag_px))

        desired_w = max(120, int(sw * scale))
        desired_h = max(120, int(sh * scale))

        # Para orientación vertical, asegurar que height >= width
        if orientation == 'vertical' and desired_h < desired_w:
            desired_w, desired_h = desired_h, desired_w

        self.desired_width = desired_w
        self.desired_height = desired_h
        self.root.geometry(f"{self.desired_width}x{self.desired_height}")
    
    def clear_container(self):
        """Elimina todos los widgets del contenedor"""
        for widget in self.main_container.winfo_children():
            widget.destroy()
    
    def show_login_view(self):
        """Muestra la pantalla de inicio de sesión"""
        self.clear_container()
        self.main_view = None
        LoginView(self.main_container, self)
    
    def show_main_view(self):
        """Muestra la pantalla principal con menú"""
        self.clear_container()
        self.main_view = MainView(self.main_container, self)


def main():
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")

    # En Windows, establecer AppUserModelID ayuda a que la barra de tareas
    # muestre el icono correcto de la aplicación.
    if sys.platform.startswith("win"):
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Sentinel.System")
        except Exception:
            pass

    root = ctk.CTk()
    
    # Configurar icono de la aplicación para ventana y barra de tareas
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(base_dir, ASSETS_PATH, ICON_FILE)
        if os.path.exists(icon_path):
            # Cargar PNG y usar para iconphoto (ventana/titlebar)
            icon_img = Image.open(icon_path).convert("RGBA")
            root._icon_image = ImageTk.PhotoImage(icon_img)
            root.iconphoto(True, root._icon_image)
            root.after(100, lambda: root.iconphoto(True, root._icon_image))

            # En Windows, convertir PNG a ICO para barra de tareas
            if sys.platform.startswith("win"):
                sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
                ico_path = os.path.join(tempfile.gettempdir(), "sentinel_system_icon.ico")
                icon_img.save(ico_path, format="ICO", sizes=sizes)
                root.iconbitmap(default=ico_path)
        else:
            print(f"Advertencia: No se encontró el icono en {icon_path}")
    except Exception as e:
        print(f"Advertencia: No se pudo cargar el icono: {e}")
    
    app = SentinelApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
