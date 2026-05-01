import time

from admin.biometric_system.contro_cerradura import ejecutar_cerradura


def ciclo_prueba(intervalo=2):
    """Prueba manual: alterna ON/OFF en bucle hasta Ctrl+C."""
    while True:
        print("ON")
        ejecutar_cerradura(segundos=intervalo)
        print("OFF")
        time.sleep(intervalo)


if __name__ == "__main__":
    ciclo_prueba()