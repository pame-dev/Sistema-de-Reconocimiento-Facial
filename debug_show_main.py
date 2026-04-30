import sys, traceback
import customtkinter as ctk
from app import SentinelApp

try:
    ctk.set_appearance_mode("light")
    root = ctk.CTk()
    # tamaños de prueba (pequeños) para forzar layout similar al del usuario
    app = SentinelApp(root, target_width=600, target_height=800)
    app.show_main_view()
    print('SHOW_MAIN_OK')
    root.destroy()
except Exception:
    traceback.print_exc()
    sys.exit(1)
