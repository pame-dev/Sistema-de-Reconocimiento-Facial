import time
import gpiod
import os
import threading


CHIP = "/dev/gpiochip0"
LINE = 4

_BOTON_MONITOR_INICIADO = False
_BOTON_MONITOR_LOCK = threading.Lock()


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


def ejecutar_cerradura_egreso(segundos=1, chip_path=CHIP, line=LINE):
	"""Activa cerradura para egreso y decrementa el contador de ocupación."""
	ejecutar_cerradura(segundos=segundos, chip_path=chip_path, line=line)
	try:
		from tools.access_counter import AccessCounter
		AccessCounter.decrement(1)
	except Exception:
		pass


def iniciar_monitor_egreso_boton(
	chip_path=CHIP,
	line=LINE,
	debounce_seg=1.0,
	active_low=True,
):
	"""Monitorea un botón físico de egreso y decrementa el contador al pulsarse.

	Usa GPIO 4 por defecto (mismo pin que la cerradura).
	Configuración por entorno (opcional):
	- EGRESO_BUTTON_LINE: número de línea GPIO de entrada del botón.
	- EGRESO_BUTTON_ACTIVE_LOW: "1" (default) o "0".

	Si no se define la línea, usa LINE=4.
	"""
	global _BOTON_MONITOR_INICIADO

	if line is None:
		line_env = os.getenv("EGRESO_BUTTON_LINE", "").strip()
		if not line_env:
			line = LINE  # Usa GPIO 4 por defecto
		else:
			try:
				line = int(line_env)
			except Exception:
				line = LINE

	active_low_env = os.getenv("EGRESO_BUTTON_ACTIVE_LOW", "1").strip().lower()
	active_low = active_low_env not in ("0", "false", "no")

	with _BOTON_MONITOR_LOCK:
		if _BOTON_MONITOR_INICIADO:
			return True
		_BOTON_MONITOR_INICIADO = True

	def _monitor():
		last_event = 0.0
		try:
			edge = gpiod.line.Edge.FALLING if active_low else gpiod.line.Edge.RISING
			bias = gpiod.line.Bias.PULL_UP if active_low else gpiod.line.Bias.PULL_DOWN
			line_request = gpiod.request_lines(
				chip_path,
				consumer="egreso_button",
				config={
					line: gpiod.LineSettings(
						direction=gpiod.line.Direction.INPUT,
						edge_detection=edge,
						bias=bias,
					)
				},
			)

			while True:
				if not line_request.wait_edge_events(timeout=1.0):
					continue
				_ = line_request.read_edge_events()
				now = time.monotonic()
				if now - last_event < max(0.1, float(debounce_seg)):
					continue
				last_event = now
				try:
					# Abrir cerradura
					ejecutar_cerradura(1, chip_path, LINE)
					# Decrementar contador
					from tools.access_counter import AccessCounter
					AccessCounter.decrement(1)
				except Exception:
					pass
		except Exception:
			pass

	threading.Thread(target=_monitor, daemon=True).start()
	return True
