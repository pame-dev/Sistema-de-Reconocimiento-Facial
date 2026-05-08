# Vista Principal con Menú Lateral
import tkinter as tk
import customtkinter as ctk
import os
import sys
import threading
import time
import cv2
from datetime import datetime
from camera import Camera
from config import COLORS, get_colors, toggle_theme, SIDEBAR_WIDTH, HEADER_HEIGHT, get_db
from views.nuevo_registro_view import NuevoRegistroView
from views.informacion_escolar_view import InformacionEscolarView
from views.historial_accesos_view import HistorialAccesosView
from PIL import Image, ImageTk
from tkinter import messagebox
from idiomas import t, cambiar_idioma

sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "admin", "biometric_system")
))
from reconocimiento import ReconocerFacial


from views.main_view_archivos.zoom import ZoomMixin
from views.main_view_archivos.header import HeaderMixin
from views.main_view_archivos.sidebar import SidebarMixin
from views.main_view_archivos.home import HomeMixin
from views.main_view_archivos.accesos import AccesosMixin
from views.main_view_archivos.camera_main import CameraMainMixin
from views.main_view_archivos.engine import EngineMixin
from views.main_view_archivos.animations import AnimationsMixin
from views.main_view_archivos.settings import SettingsMixin
from views.main_view_archivos.utils import UtilsMixin

ZOOM_MIN  = 0.7
ZOOM_MAX  = 2.0
ZOOM_STEP = 0.1

from views.font_scale import FontScale


class MainView(ZoomMixin,HeaderMixin, SidebarMixin, HomeMixin, AccesosMixin, CameraMainMixin, EngineMixin, AnimationsMixin, SettingsMixin, UtilsMixin):
    def __init__(self, parent, app):
        self.app           = app
        self.parent        = parent
        self.menu_visible  = False
        self.nav_buttons   = []
        self._active_btn   = None
        self._vista_actual = None
        self.parent.winfo_toplevel().focus_force()
        self.colors = get_colors()

        self._cam_running   = False
        self._cam_thread    = None
        self._cap           = None
        self._engine        = None
        self._cam_photo     = None
        self._frame_pending = False
        self._zoom_popover  = None
        self._zoom_manual   = False
        self._nuevo_registro_view  = None
        self._nuevo_registro_state = None
        self._informacion_escolar_view = None

        self._panel_reset_job = None
        self._borde_job       = None
        self._historial_items = []
        self._sin_cara_job    = None
        self._last_scale      = None
        self._accesos_layout_vertical = None
        self._accesos_body            = None

        self.main_frame = ctk.CTkFrame(parent, fg_color=self.colors['background'])
        self.main_frame.pack(fill="both", expand=True)

        # Base design dimensions used for responsive scaling.
        # They are adjusted to the real window size after first layout pass
        # so language/theme refreshes do not unexpectedly shrink fonts.
        self._base_w = getattr(self.app, 'desired_width', 900)
        self._base_h = getattr(self.app, 'desired_height', 600)

        self.create_header()

        self.body_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.body_frame.pack(fill="both", expand=True)

        self.create_sidebar()
        self.create_content_area()
        self.show_home()
        self._capturar_base_real_ventana()
        self._bind_zoom_keys()
        # Bind to parent window resize to keep UI responsive
        try:
            root = self.parent.winfo_toplevel()
            root.bind("<Configure>", self._on_root_configure)
        except Exception:
            pass

    def show_nuevo_registro(self):
        self._stop_camera()
        self._vista_actual = "nuevo_registro"
        self.clear_content()
        estado = self._nuevo_registro_state
        self._nuevo_registro_state = None
        self._nuevo_registro_view  = NuevoRegistroView(self.content_frame,
                                                       main_view=self,
                                                       initial_state=estado)

    def show_informacion_escolar(self, preselect_user_id=None):
        self._vista_actual = "info_escolar"
        self.clear_content()
        vista = InformacionEscolarView(self.content_frame)
        self._informacion_escolar_view = vista
        self.content_frame.update()
        vista.cargar_datos()
        if preselect_user_id is not None:
            vista.mostrar_edicion_por_id(preselect_user_id)

    def show_historial_accesos(self):
        self._vista_actual = "historial"
        self.clear_content()
        vista = HistorialAccesosView(self.content_frame)
        self.content_frame.update()
        vista.cargar_datos()
