from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Optional # Para usar Optional[str] en parse_tipo

def now_argentina() -> datetime:
    """Devuelve el objeto datetime actual en la zona horaria de Buenos Aires."""
    return datetime.now(ZoneInfo("America/Argentina/Buenos_Aires"))

def get_full_date() -> str:
    """
    Formatea la fecha actual en un formato legible para el título de la web.
    Ej: 'Cotización del dólar hoy Miércoles 29 de Octubre'
    """
    dias = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
    meses = [
        "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
    ]
    now = now_argentina()
    day_name = dias[now.weekday()].capitalize()
    day_num = now.day
    month_name = meses[now.month - 1].capitalize()
    return f"Cotización del dólar hoy {day_name} {day_num} de {month_name}"

def parse_tipo(text: str) -> Optional[str]:
    """
    Busca un tipo de dólar válido dentro de un comando de texto.
    Ej: '/dolar_blue' -> 'blue'
    """
    mapping = {
        "oficial": "oficial", "blue": "blue", "mep": "mep", "bolsa": "mep",
        "ccl": "ccl", "tarjeta": "tarjeta", "cripto": "cripto", "mayorista": "mayorista"
    }
    for k, v in mapping.items():
        if k in text:
            return v
    return None