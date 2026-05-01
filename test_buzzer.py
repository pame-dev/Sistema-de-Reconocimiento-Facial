# test_buzzer.py
import gpiod
import time

PIN = 18

def play_tone(request, pin, frequency, duration):
    period = 1.0 / frequency
    half = period / 2
    end = time.time() + duration
    while time.time() < end:
        request.set_value(pin, gpiod.line.Value.ACTIVE)
        time.sleep(half)
        request.set_value(pin, gpiod.line.Value.INACTIVE)
        time.sleep(half)

def beep():
    with gpiod.request_lines(
        "/dev/gpiochip0",
        consumer="buzzer",
        config={PIN: gpiod.LineSettings(direction=gpiod.line.Direction.OUTPUT)}
    ) as request:
        play_tone(request, PIN, 1000, 0.1)

# Solo suena si se ejecuta directamente
if __name__ == "__main__":
    beep()