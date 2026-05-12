import json
import threading
import os

# Simple thread-safe counter persisted to a JSON file in the database folder.
class AccessCounter:
    _lock = threading.Lock()
    _path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "database", "access_counter.json")

    @classmethod
    def _ensure_exists(cls):
        d = os.path.dirname(cls._path)
        if not os.path.exists(d):
            try:
                os.makedirs(d, exist_ok=True)
            except Exception:
                pass
        if not os.path.exists(cls._path):
            try:
                with open(cls._path, "w", encoding="utf-8") as f:
                    json.dump({"total": 0}, f)
            except Exception:
                pass

    @classmethod
    def _read(cls):
        cls._ensure_exists()
        try:
            with open(cls._path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"total": 0}

    @classmethod
    def _write(cls, data):
        cls._ensure_exists()
        try:
            with open(cls._path, "w", encoding="utf-8") as f:
                json.dump(data, f)
        except Exception:
            pass

    @classmethod
    def get(cls):
        with cls._lock:
            data = cls._read()
            return int(data.get("total", 0))

    @classmethod
    def set(cls, value: int):
        with cls._lock:
            cls._write({"total": int(value)})

    @classmethod
    def increment(cls, n: int = 1):
        with cls._lock:
            data = cls._read()
            total = int(data.get("total", 0)) + int(n)
            if total < 0:
                total = 0
            cls._write({"total": total})
            return total

    @classmethod
    def decrement(cls, n: int = 1):
        return cls.increment(-int(n))
