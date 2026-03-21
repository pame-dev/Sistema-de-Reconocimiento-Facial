import tkinter as tk #libreria grafica para crear interfaces de usuario
import customtkinter as ctk
import os #libreria para interactuar con el sistema operativo, como manejar archivos y rutas
import ctypes
from PIL import Image, ImageTk
from config import WINDOW_WIDTH, WINDOW_HEIGHT, ASSETS_PATH, ICON_FILE # importamos configuraciones generales del sistema
from views.login_view import LoginView 
from views.main_view import MainView 

class SentinelApp:
    """Clase principal que maneja la aplicación y navegación entre vistas"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Sentinel System")
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.resizable(True, True)
        self.root.configure(fg_color="#F4F7FB")
        
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

        # Evita abrir más grande que la pantalla útil.
        width = min(WINDOW_WIDTH, max(720, screen_w - 80))
        height = min(WINDOW_HEIGHT, max(520, screen_h - 120))

        x = max((screen_w // 2) - (width // 2), 0)
        y = max((screen_h // 2) - (height // 2), 0)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
    
    def clear_container(self):
        """Elimina todos los widgets del contenedor"""
        for widget in self.main_container.winfo_children():
            widget.destroy()
    
    def show_login_view(self):
        """Muestra la pantalla de inicio de sesión"""
        self.clear_container()
        LoginView(self.main_container, self)
    
    def show_main_view(self):
        """Muestra la pantalla principal con menú"""
        self.clear_container()
        MainView(self.main_container, self)


def main():
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")
    root = ctk.CTk()
    
    # Configurar icono de la aplicación
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(base_dir, ASSETS_PATH, ICON_FILE)
        if os.path.exists(icon_path):
            # Usar PIL para cargar PNG en cualquier sistema operativo
            icon_img = Image.open(icon_path)
            root._icon_image = ImageTk.PhotoImage(icon_img)
            root.iconphoto(True, root._icon_image)

            # En Windows, establecer también el icono en la barra de tareas
            if os.name == 'nt':
                try:
                    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("sentinel.system.app")
                    ico_path = os.path.splitext(icon_path)[0] + '.ico'
                    if not os.path.exists(ico_path):
                        icon_img.save(ico_path, format='ICO', sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (256, 256)])
                    root.iconbitmap(ico_path)
                except:
                    pass
    except Exception as e:
        print(f"Advertencia: No se pudo cargar el icono: {e}")
    
    app = SentinelApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
