import RPi.GPIO as GPIO
import time

RELE_PIN = 4  # GPIO 4 (pin físico 7)

GPIO.setmode(GPIO.BCM)
GPIO.setup(RELE_PIN, GPIO.OUT)

try:
    while True:
        print("🔓 Abriendo cerradura...")
        GPIO.output(RELE_PIN, GPIO.HIGH)  # Activa el relé
        time.sleep(3)  # Mantiene abierto 3 segundos

        print("🔒 Cerrando cerradura...")
        GPIO.output(RELE_PIN, GPIO.LOW)   # Desactiva el relé
        time.sleep(3)

except KeyboardInterrupt:
    print("Programa detenido")

finally:
    GPIO.cleanup()