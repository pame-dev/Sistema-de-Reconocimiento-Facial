import time
import gpiod


CHIP = "/dev/gpiochip0"
LINE = 4


def ejecutar_cerradura(segundos=1, chip_path=CHIP, line=LINE):
	"""Activa la cerradura por una cantidad de segundos y luego la desactiva."""
	line_request = gpiod.request_lines(
		chip_path,
		consumer="cerradura",
		config={
			line: gpiod.LineSettings(direction=gpiod.line.Direction.OUTPUT)
		},
	)

	try:
		line_request.set_value(line, gpiod.line.Value.ACTIVE)
		time.sleep(max(0, float(segundos)))
		line_request.set_value(line, gpiod.line.Value.INACTIVE)
	finally:
		line_request.release()
