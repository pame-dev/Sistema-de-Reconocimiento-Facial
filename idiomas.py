IDIOMA_ACTUAL = "es"

TEXTOS = {
    "es": {
        "titulo": "Sentinel System — Panel Principal",
        "salir": "← Salir",
        "inicio": "Inicio",
        "nuevo": "Nuevo Registro",
        "info": "Información Escolar",
        "historial": "Historial de Accesos",
        "pantalla": "Pantalla de Accesos",
        "bienvenida": "Le da la Bienvenida al Sistema",
        "seleccion": "Seleccione una opción del menú para comenzar",
        "agregar": "➕  Agregar nuevo usuario",
        "iniciar": "▶  Iniciar",
        "detener": "⏹  Detener",
        "camara_on": "⬤  Cámara en línea",
        "camara_off": "⬤  Cámara apagada",
        "navegacion": "NAVEGACIÓN",
        "control_accesos": "Control de Accesos",
        "esperando": "Esperando reconocimiento",
        "colocate": "Colócate frente a la cámara",
        "presiona_iniciar": "Presiona ▶ Iniciar para comenzar",
        "iniciando_camara": "Iniciando cámara",
        "preparando": "Preparando reconocimiento facial...",
        "confirmar_salida": "Confirmar salida",
"seguro_salir": "¿Estás seguro de que deseas salir?"
    },
    "en": {
        "titulo": "Sentinel System — Main Panel",
        "salir": "← Logout",
        "inicio": "Home",
        "nuevo": "New Register",
        "info": "School Info",
        "historial": "Access History",
        "pantalla": "Access Screen",
        "bienvenida": "Welcome to the System",
        "seleccion": "Select an option from the menu",
        "agregar": "➕  Add new user",
        "iniciar": "▶  Start",
        "detener": "⏹  Stop",
        "camara_on": "⬤  Camera online",
        "camara_off": "⬤  Camera off",
        "navegacion": "NAVIGATION",
        "control_accesos": "Access Control",
        "esperando": "Waiting for recognition",
        "colocate": "Stand in front of the camera",
        "presiona_iniciar": "Press ▶ Start to begin",
        "iniciando_camara": "Starting camera",
        "preparando": "Preparing facial recognition...",
        "confirmar_salida": "Confirm exit",
        "seguro_salir": "Are you sure you want to exit?"
    }
}

def t(clave):
    return TEXTOS[IDIOMA_ACTUAL].get(clave, clave)

def cambiar_idioma():
    global IDIOMA_ACTUAL
    IDIOMA_ACTUAL = "en" if IDIOMA_ACTUAL == "es" else "es"