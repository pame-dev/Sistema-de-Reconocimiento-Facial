import time

try:
    import RPi.GPIO as GPIO
except ImportError:
    GPIO = None

RELE_PIN = 4  # GPIO 4 (pin físico 7)


def ejecutar_cerradura(segundos=8):
    if GPIO is None:
        print("⚠️  RPi.GPIO no disponible. No se puede accionar la cerradura.")
        return False

    GPIO.setmode(GPIO.BCM)
    GPIO.setup(RELE_PIN, GPIO.OUT)

    try:
        print("🔓 Abriendo cerradura...")
        GPIO.output(RELE_PIN, GPIO.HIGH)  # Activa el relé
        time.sleep(segundos)

        print("🔒 Cerrando cerradura...")
        GPIO.output(RELE_PIN, GPIO.LOW)   # Desactiva el relé
        return True

    finally:
        GPIO.cleanup()


if __name__ == "__main__":
    try:
        ejecutar_cerradura(8)
    except KeyboardInterrupt:
        print("Programa detenido")