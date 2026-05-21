# views/nuevo_registro_view.py
"""
Orquestador de la vista de nuevo registro.
Toda la lógica de cada pantalla vive en los mixins:

    constants.py          — constantes, config de roles y posturas
    utils.py              — helpers (darken, etc.)
    seleccion_rol.py      — Pantalla 1: tarjetas de rol
    formulario.py         — Pantalla 2: formulario de datos
    animacion_camara.py   — Pantalla 3: animación de carga de cámara
    captura_biometrica.py — Pantalla 4: detección, captura y guardado
"""
import cv2
import hashlib
import customtkinter as ctk

from config import get_colors
from views.nuevo_registro.constants import ROL_CONFIG, haar_path
from views.nuevo_registro.seleccion_rol import SeleccionRolMixin
from views.nuevo_registro.formulario import FormularioMixin
from views.nuevo_registro.animacion_camara import AnimacionCamaraMixin
from views.nuevo_registro.captura_biometrica import CapturaBiometricaMixin


class NuevoRegistroView(
    SeleccionRolMixin,
    FormularioMixin,
    AnimacionCamaraMixin,
    CapturaBiometricaMixin,
):
    def __init__(self, parent, main_view=None, initial_state=None, on_back_callback=None):
        self.colors    = get_colors()
        self.parent    = parent
        self.main_view = main_view or getattr(parent, 'main_view', None)
        self.container = ctk.CTkFrame(parent, fg_color=self.colors['background'])
        self.container.pack(fill="both", expand=True, padx=1, pady=30)

        self.camara    = None
        self.capturando = False
        self.fotos_temp = []
        self.rol_actual = None
        self.entries    = {}

        self.postura_idx          = 0
        self.fotos_postura        = 0
        self.posturas_completadas = []

        self._auto_activo     = False
        self._frames_con_cara = 0
        self._ultima_captura  = 0.0
        self._countdown       = 0
        self._countdown_job   = None
        self._guardando       = False
        self._pausado         = False
        self._ultima_muestra_gray = None
        self._user_id_creado  = None
        self._engine_duplicados = None
        self._engine_inactivos = None
        self._engine_inactivos_fp = None
        self._alerta_duplicado_abierta = False
        self._usuario_duplicado_detectado = None

        # ── Detectores Haar ────────────────────────────────────────────────────
        self.detector_frontal = cv2.CascadeClassifier(
            haar_path("haarcascade_frontalface_default.xml")
        )
        self.detector_alt = cv2.CascadeClassifier(
            haar_path("haarcascade_frontalface_alt2.xml")
        )
        self.detector_perfil = cv2.CascadeClassifier(
            haar_path("haarcascade_profileface.xml")
        )
        self.detector_eyes = cv2.CascadeClassifier(
            haar_path("haarcascade_eye.xml")
        )

        if self.detector_frontal.empty():
            raise RuntimeError("No se pudo cargar haarcascade_frontalface_default.xml")
        if self.detector_alt.empty():
            raise RuntimeError("No se pudo cargar haarcascade_frontalface_alt2.xml")
        if self.detector_perfil.empty():
            raise RuntimeError("No se pudo cargar haarcascade_profileface.xml")
        if self.detector_eyes.empty():
            print("⚠️ No se pudo cargar haarcascade_eye.xml — validación de ojos desactivada")

        self.modo_retomar_fotos = False
        self.user_id_existente  = None
        self.valores_form       = {}
        self._on_back_callback  = on_back_callback

        # Restaurar estado si viene de un recargo de vista
        estado = initial_state or {}
        self.rol_actual = estado.get("rol_actual")
        # Si es modo retomar fotos, no mostrar nada aquí (se hará después)
        if estado.get("modo_retomar_fotos", False):
            self.modo_retomar_fotos = True
            self.user_id_existente = estado.get("user_id")
            self.valores_form = dict(estado.get("valores_form") or {})
        elif self.rol_actual in ROL_CONFIG:
            self.valores_form = dict(estado.get("valores_form") or {})
            self._mostrar_formulario()
        else:
            self._mostrar_seleccion_rol()

    def _disable_top_controls(self):
        if getattr(self, 'main_view', None):
            try:
                self.main_view.disable_top_controls()
            except Exception:
                pass

    def _enable_top_controls(self):
        if getattr(self, 'main_view', None):
            try:
                self.main_view.enable_top_controls()
            except Exception:
                pass

    def export_state(self):
        """Exporta el estado del formulario para restaurarlo tras recargar la vista."""
        valores = dict(getattr(self, 'valores_form', {}) or {})
        for key, entry in getattr(self, 'entries', {}).items():
            try:
                valores[key] = entry.get().strip()
            except Exception:
                pass
        return {
            "rol_actual":   self.rol_actual,
            "valores_form": valores,
        }

    def _limpiar_container(self):
        self._detener_camara_silencio()
        for w in self.container.winfo_children():
            w.destroy()

    def __del__(self):
        if self.camara:
            try:
                self.camara.stop()
            except Exception:
                pass