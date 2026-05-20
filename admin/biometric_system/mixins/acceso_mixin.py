import threading
from datetime import datetime

try:
    from tools.access_counter import AccessCounter
except Exception:
    AccessCounter = None

try:
    from admin.biometric_system.contro_cerradura import ejecutar_cerradura as ejecutar_test_cerradura
except Exception:
    ejecutar_test_cerradura = None

try:
    from test_buzzer import beep as ejecutar_buzzer_concedido
except Exception as e:
    print(f"⚠️ Buzzer concedido no disponible: {e}")
    ejecutar_buzzer_concedido = None

try:
    from test_buzzer2 import beep as ejecutar_buzzer_denegado
except Exception as e:
    print(f"⚠️ Buzzer denegado no disponible: {e}")
    ejecutar_buzzer_denegado = None

from idiomas import t


class AccesoMixin:

    # ─────────────────────────────────────────────────────────────────────────
    # Registro de acceso en BD (con cooldown real)
    # ─────────────────────────────────────────────────────────────────────────
    def _puede_registrar(self, user_id):
        ahora  = datetime.now()
        key    = user_id if user_id is not None else "desconocido"
        ultimo = self._ultimo_registro.get(key)
        if ultimo is None:
            return True
        return (ahora - ultimo).total_seconds() >= self._cooldown_segundos

    def registrar_acceso(self, user_id, estado, distancia, frame_limpio=None):
        confianza          = round(max(0.0, 100 - float(distancia)), 2)
        hubo_cambio_estado = (self._ultimo_tipo != estado)

        if not self._puede_registrar(user_id):
            self._ultimo_tipo = estado
            if hubo_cambio_estado and self.on_resultado:
                nombre = self.nombres.get(user_id, t("desconocido"))
                self.on_resultado(nombre, confianza, estado, float(distancia))
            return

        conn = self.get_db()
        if not conn:
            return

        cur = conn.cursor()

        try:
            foto_bytes = None
            if estado == "denegado" and frame_limpio is not None:
                foto_bytes = self._frame_a_bytes(frame_limpio)

            cur.execute("""
                INSERT INTO accesos
                    (fkIdUsuario, estado_acceso, confianzaAcceso,
                     umbralConfianzaUsado, fechaHoraIntentoAcceso, fotoAcceso)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                estado,
                confianza,
                round(self.tolerancia, 2),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                foto_bytes
            ))
            conn.commit()

            key = user_id if user_id is not None else "desconocido"
            self._ultimo_registro[key] = datetime.now()
            self._ultimo_tipo = estado

            if estado == "aceptado":
                self.total_aceptados += 1
                if AccessCounter is not None:
                    try:
                        AccessCounter.increment(1)
                    except Exception:
                        pass
                self._overlay_texto  = t("acceso_permitido")
                self._overlay_color  = (30, 200, 60)
                self._overlay_frames = self._overlay_duracion
                self._ultimo_registro.pop("desconocido", None)
                self._ultimo_usuario_aceptado = user_id
                self._ultimo_aceptado_ts      = datetime.now()
                self._abrir_cerradura()
                if ejecutar_buzzer_concedido:
                    threading.Thread(target=ejecutar_buzzer_concedido, daemon=True).start()
            else:
                self.total_denegados += 1
                self._overlay_texto     = t("acceso_denegado")
                self._overlay_color     = (40, 40, 220)
                self._overlay_frames    = 8
                self._votos             = []
                self._desconocido_desde = None
                if ejecutar_buzzer_denegado:
                    threading.Thread(target=ejecutar_buzzer_denegado, daemon=True).start()

            if self.on_resultado:
                nombre = self.nombres.get(user_id, t("desconocido"))
                self.on_resultado(nombre, confianza, estado, float(distancia))

        except Exception as e:
            print(f"❌ Error registrando acceso: {e}")
        finally:
            conn.close()

    def _abrir_cerradura(self):
        if self._cerradura_en_proceso or ejecutar_test_cerradura is None:
            return
        self._cerradura_en_proceso = True

        def _run():
            try:
                ejecutar_test_cerradura(1)
            except Exception as e:
                print(f"⚠️  Error en cerradura: {e}")
            finally:
                self._cerradura_en_proceso = False

        threading.Thread(target=_run, daemon=True).start()