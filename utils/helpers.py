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
    
def time_ago(timestamp_str: str) -> str:
    """
    Calcula la diferencia de tiempo, manejando el formato ISO con zona horaria.
    """
    try:
        # 1. Parsear el timestamp: fromisoformat ya maneja el -03:00
        past_time = datetime.fromisoformat(timestamp_str)
        now = now_argentina()

        # 2. Convertir past_time a la zona horaria del servidor (Buenos Aires)
        # Esto es clave para que la resta sea segura si las zonas son diferentes.
        past_time = past_time.astimezone(now.tzinfo)

        # 3. Calcular la diferencia. Aseguramos que past_time no esté en el futuro.
        if now < past_time:
             # Si el timestamp es posterior a la hora de la consulta (raro, pero seguro)
             return "Actualizado recientemente" 
             
        diff = now - past_time
        seconds = diff.total_seconds()
        minutes = int(seconds / 60)
        
        # 4. Formatear la salida
        if minutes < 1:
            return "Hace menos de un minuto"
        elif minutes < 60:
            return f"Hace {minutes} minutos"
        elif minutes < (24 * 60):
            hours = int(minutes / 60)
            return f"Hace {hours} horas"
        else:
            days = int(minutes / (24 * 60))
            return f"Hace {days} días"
            
    except Exception as e:
        # Prevenimos que Jinja2 se rompa si el timestamp es inválido
        print(f"ERROR: Fallo en time_ago para '{timestamp_str}': {e}")
        return "ERROR DE CÁLCULO"