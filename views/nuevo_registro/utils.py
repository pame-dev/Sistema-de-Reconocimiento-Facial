# views/utils.py


def darken(hex_color: str, amount: int = 30) -> str:
    """Oscurece un color hexadecimal dado un delta."""
    h = hex_color.lstrip('#')
    r, g, b = (int(h[i:i+2], 16) for i in (0, 2, 4))
    return f"#{max(0, r-amount):02x}{max(0, g-amount):02x}{max(0, b-amount):02x}"