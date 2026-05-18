import gpiod
import time

PIN = 18

chip = "/dev/gpiochip0"

with gpiod.request_lines(
    chip,
    consumer="test-buzzer",
    config={
        PIN: gpiod.LineSettings(
            direction=gpiod.line.Direction.OUTPUT
        )
    }
) as request:

    print("Probando buzzer...")

    # 3 pitidos cortos
    for i in range(3):
        request.set_value(PIN, gpiod.line.Value.ACTIVE)
        time.sleep(0.2)

        request.set_value(PIN, gpiod.line.Value.INACTIVE)
        time.sleep(0.2)

    # pitido largo
    request.set_value(PIN, gpiod.line.Value.ACTIVE)
    time.sleep(1)

    request.set_value(PIN, gpiod.line.Value.INACTIVE)

print("Prueba terminada")