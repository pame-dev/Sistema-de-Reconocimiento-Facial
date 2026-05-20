import sqlite3
import hashlib
import pickle
import os
import cv2
import numpy as np


class DatabaseMixin:

    # ─────────────────────────────────────────────────────────────────────────
    # Base de datos
    # ─────────────────────────────────────────────────────────────────────────
    def get_db(self):
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            return conn
        except sqlite3.Error as e:
            print(f"❌ Error conectando a DB: {e}")
            return None

    def _usuario_activo(self, user_id: int) -> bool:
        """Retorna True si el usuario está activo en la BD."""
        if user_id is None:
            return False
        conn = self.get_db()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT estadoUsuario FROM usuarios WHERE idUsuario = ? LIMIT 1",
                (int(user_id),)
            )
            row = cur.fetchone()
            if not row:
                return False
            estado = row[0]
            return str(estado).lower() == "activo"
        except Exception:
            return False
        finally:
            conn.close()

    def _frame_a_bytes(self, frame):
        """Convierte un frame BGR de OpenCV a bytes JPEG comprimidos."""
        if frame is None:
            return None
        try:
            ok, buf = cv2.imencode(
                '.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 75]
            )
            if ok:
                return buf.tobytes()
        except Exception as e:
            print(f"⚠️ Error al codificar foto de acceso: {e}")
        return None

    # ─────────────────────────────────────────────────────────────────────────
    # Gestión de IDs y persistencia
    # ─────────────────────────────────────────────────────────────────────────
    def _ids_en_bd(self):
        conn = self.get_db()
        if not conn:
            return set()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT DISTINCT b.fkIdUsuario
                FROM biometria b
                INNER JOIN usuarios u ON u.idUsuario = b.fkIdUsuario
                WHERE b.encodeBiometria IS NOT NULL
                AND LOWER(TRIM(u.estadoUsuario)) = 'activo'
            """)
            return {row[0] for row in cur.fetchall()}
        except Exception:
            return set()
        finally:
            conn.close()

    def _ids_en_modelo(self):
        if not os.path.exists(self.ids_hash_path):
            return set(), None
        try:
            with open(self.ids_hash_path, 'rb') as f:
                data = pickle.load(f)
            if isinstance(data, set):
                return data, None
            if isinstance(data, dict):
                return data.get('ids', set()), data.get('fingerprint')
        except Exception:
            pass
        return set(), None

    def _fingerprint_en_bd(self):
        conn = self.get_db()
        if not conn:
            return None
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT b.fkIdUsuario, b.encodeBiometria
                FROM biometria b
                INNER JOIN usuarios u ON u.idUsuario = b.fkIdUsuario
                WHERE b.encodeBiometria IS NOT NULL
                AND LOWER(TRIM(u.estadoUsuario)) = 'activo'
            """)
            items = []
            for user_id, imagen_bytes in cur.fetchall():
                if imagen_bytes is None:
                    continue
                digest = hashlib.md5(imagen_bytes).hexdigest()
                items.append((user_id, digest))
            return tuple(sorted(items))
        except Exception:
            return None
        finally:
            conn.close()

    def _guardar_ids_hash(self, ids_set, fingerprint=None):
        os.makedirs(self.artifacts_dir, exist_ok=True)
        data = {'ids': ids_set, 'fingerprint': fingerprint}
        with open(self.ids_hash_path, 'wb') as f:
            pickle.dump(data, f)

    def _borrar_archivos_modelo(self):
        for p in (self.model_path, self.data_path, self.ids_hash_path):
            try:
                os.remove(p)
            except Exception:
                pass