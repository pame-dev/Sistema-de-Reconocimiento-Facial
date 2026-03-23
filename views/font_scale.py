# views/font_scale.py

ZOOM_MIN  = 0.7
ZOOM_MAX  = 2.0

class FontScale:
    _escala: float = 1.0

    @classmethod
    def get(cls) -> float:
        return cls._escala

    @classmethod
    def set(cls, v: float):
        cls._escala = round(max(ZOOM_MIN, min(ZOOM_MAX, v)), 2)

    @classmethod
    def f(cls, base: int) -> tuple:
        return ("Segoe UI", max(7, round(base * cls._escala)))

    @classmethod
    def fb(cls, base: int) -> tuple:
        return ("Segoe UI", max(7, round(base * cls._escala)), "bold")