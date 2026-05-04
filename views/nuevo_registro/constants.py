from idiomas import t
import os
import cv2

# ─────────────────────────────────────────────
# 🔹 Haar cascade helper
# ─────────────────────────────────────────────

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
        f"{t('error_haar')} '{filename}'. {t('instalar_opencv')}"
    )


ROL_CONFIG = {
    "alumno": {
        "icono": "🎓",
        "titulo": "estudiante",        # 🔑 clave
        "desc": "desc_estudiante",     # 🔑 clave
        "color": "#4A90D9"
    },
    "maestro": {
        "icono": "📚",
        "titulo": "docente",
        "desc": "desc_docente",
        "color": "#27AE60"
    },
    "personal": {
        "icono": "🏢",
        "titulo": "personal",
        "desc": "desc_personal",
        "color": "#E67E22"
    },
}


CAMPOS_POR_ROL = {
    "alumno": [
        ("grado", "gradoAlumno", True),
        ("grupo", "grupoAlumno", True),
        ("facultad", "facultadAlumno", True),
        ("carrera", "carreraAlumno", True),
    ],
    "maestro": [
        ("grado_imparte", "gradoImpartidoMaestro", True),
        ("materia", "materiaImpartidaMaestro", True),
    ],
    "personal": [
        ("puesto", "puestoPersonalEscolar", True),
        ("area", "areaPersonalEscolar", True),
    ],
}


CAMPOS_COMUNES = [
    ("nombre", "nombreUsuario", True),
    ("apellido_paterno", "apellidoPaternoUsuario", True),
    ("apellido_materno", "apellidoMaternoUsuario", False),
    ("matricula", "matriculaUsuario", False),
    ("telefono", "telefonoUsuario", True),
    ("correo", "correoUsuario", True),
    ("fecha_nacimiento", "fechaNacimientoUsuario", True),
    ("tipo_sangre", "tipoSangreUsuario", True),
]

# ─────────────────────────────────────────────
# 🔹 POSTURAS (SOLO CLAVES)
# ─────────────────────────────────────────────

POSTURAS = [
    {
        "id": "frontal",
        "titulo": "frontal",
        "instruccion": "inst_frontal",
        "imagen": "../assets/posturas/postura_frontal.png",
        "icono": "😐",
        "fotos": 60
    },
    {
        "id": "izquierda",
        "titulo": "izquierda",
        "instruccion": "inst_izquierda",
        "imagen": "../assets/posturas/postura_izquierda.png",
        "icono": "😶",
        "fotos": 60
    },
    {
        "id": "derecha",
        "titulo": "derecha",
        "instruccion": "inst_derecha",
        "imagen": "../assets/posturas/postura_derecha.png",
        "icono": "😶",
        "fotos": 60
    },
    {
        "id": "perfil_izq",
        "titulo": "perfil_izquierda",
        "instruccion": "inst_perfil_izq",
        "imagen": "../assets/posturas/postura_perfil_izq.png",
        "icono": "🙂",
        "fotos": 60
    },
    {
        "id": "perfil_der",
        "titulo": "perfil_derecha",
        "instruccion": "inst_perfil_der",
        "imagen": "../assets/posturas/postura_perfil_der.png",
        "icono": "🙂",
        "fotos": 60
    },
]

# ─────────────────────────────────────────────
# 🔹 CÁLCULOS
# ─────────────────────────────────────────────

TOTAL_FOTOS = sum(p["fotos"] for p in POSTURAS)

# ─────────────────────────────────────────────
# 🔹 CONSTANTES
# ─────────────────────────────────────────────

FRAMES_ESTABLE = 5
CAPTURE_DELAY = 0.18