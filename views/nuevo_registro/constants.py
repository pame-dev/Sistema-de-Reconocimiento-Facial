# views/constants.py
from idiomas import t

# ── Haar cascade helper ───────────────────────────────────────────────────────
import os
import cv2

def haar_path(filename: str) -> str:
    if hasattr(cv2, "data") and hasattr(cv2.data, "haarcascades"):
        return os.path.join(cv2.data.haarcascades, filename)
    debian_dir = "/usr/share/opencv4/haarcascades"
    p = os.path.join(debian_dir, filename)
    if os.path.exists(p):
        return p
    for base in ("/usr/share/opencv/haarcascades",):
        p2 = os.path.join(base, filename)
        if os.path.exists(p2):
            return p2
    raise FileNotFoundError(
        f"No encontré Haar cascade '{filename}'. "
        f"En Debian instala: sudo apt install opencv-data"
    )

# ── Roles ─────────────────────────────────────────────────────────────────────
ROL_CONFIG = {
    "alumno":   {"icono": "🎓", "titulo": t("estudiante"), "desc": " ", "color": "#4A90D9"},
    "maestro":  {"icono": "📚", "titulo": t("docente"),    "desc": " ", "color": "#27AE60"},
    "personal": {"icono": "🏢", "titulo": t("personal"),   "desc": "",  "color": "#E67E22"},
}

CAMPOS_POR_ROL = {
    "alumno": [
        (t("grado")+":",    "gradoAlumno",             True),
        (t("grupo")+":",    "grupoAlumno",             True),
        (t("facultad")+":", "facultadAlumno",           True),
        (t("carrera")+":",  "carreraAlumno",            True),
    ],
    "maestro": [
        (t("grado_imparte")+":", "gradoImpartidoMaestro",   True),
        (t("materia")+":",       "materiaImpartidaMaestro",  True),
    ],
    "personal": [
        (t("puesto")+":", "puestoPersonalEscolar", True),
        (t("area")+":",   "areaPersonalEscolar",   True),
    ],
}

CAMPOS_COMUNES = [
    (t("nombre")+":",           "nombreUsuario",          True),
    (t("apellido_paterno")+":", "apellidoPaternoUsuario",  True),
    (t("apellido_materno")+":", "apellidoMaternoUsuario",  False),
    (t("matricula")+":",        "matriculaUsuario",        False),
    (t("telefono")+":",         "telefonoUsuario",         True),
    (t("correo")+":",           "correoUsuario",           True),
    (t("fecha_nacimiento")+":", "fechaNacimientoUsuario",  True),
    (t("tipo_sangre")+":",      "tipoSangreUsuario",       True),
    (t("direccion")+":",        "direccionUsuario",        True),
]

# ── Posturas biométricas ───────────────────────────────────────────────────────
POSTURAS = [
    {"id": "frontal",    "titulo": t("frontal"),          "instruccion": t("inst_frontal"),    "imagen": "../assets/posturas/postura_frontal.png",    "icono": "😐", "fotos": 60},
    {"id": "izquierda",  "titulo": t("izquierda"),        "instruccion": t("inst_izquierda"),  "imagen": "../assets/posturas/postura_izquierda.png",  "icono": "😶", "fotos": 60},
    {"id": "derecha",    "titulo": t("derecha"),          "instruccion": t("inst_derecha"),    "imagen": "../assets/posturas/postura_derecha.png",    "icono": "😶", "fotos": 60},
    {"id": "perfil_izq", "titulo": t("perfil_izquierda"), "instruccion": t("inst_perfil_izq"), "imagen": "../assets/posturas/postura_perfil_izq.png", "icono": "🙂", "fotos": 60},
    {"id": "perfil_der", "titulo": t("perfil_derecha"),   "instruccion": t("inst_perfil_der"), "imagen": "../assets/posturas/postura_perfil_der.png", "icono": "🙂", "fotos": 60},
]

TOTAL_FOTOS    = sum(p["fotos"] for p in POSTURAS)   # 300
FRAMES_ESTABLE = 5
CAPTURE_DELAY  = 0.18   # segundos entre capturas