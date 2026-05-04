import sys
import types
sys.path.insert(0, r'C:\Users\Jahir\Desktop\Sistema-de-Reconocimiento-Facial')

fake_rec = types.SimpleNamespace(ReconocerFacial=type('A',(object,),{}))
sys.modules['reconocimiento'] = fake_rec
sys.modules['admin.biometric_system.reconocimiento'] = fake_rec

import customtkinter as ctk
from views.main_view import MainView

class DummyApp:
    desired_width = 1100
    desired_height = 700

root = ctk.CTk()
root.geometry('1100x700')
root.update_idletasks()
try:
    mv = MainView(root, app=DummyApp())
    mv.show_informacion_escolar()
    root.update()
    print('show_informacion_ok')
    mv.show_historial_accesos()
    root.update()
    print('show_historial_ok')
except Exception:
    import traceback; traceback.print_exc()
finally:
    root.destroy()
