# storage/initial_rates.py
from utils.file_helpers import load_json, save_json
from scheduler.constants import INITIAL_RATES_FILE
from datetime import date

def load_initial_rates():
    """
    Carga el historial completo de las cotizaciones iniciales diarias desde el archivo.
    
    Retorna:
        dict: Un diccionario donde la clave es la fecha ('YYYY-MM-DD') y el valor son 
              las cotizaciones de ese día.
    """
    return load_json(INITIAL_RATES_FILE)

def save_initial_rates_by_day(rates):
    """
    Guarda la cotización inicial del día bajo la clave YYYY-MM-DD.
    
    Esta función es idempotente: solo guarda las tasas si aún no existe 
    un registro para la fecha actual, evitando sobreescrituras accidentales.

    Args:
        rates (dict): El diccionario de cotizaciones actuales (ej. {"blue": {...}, ...}).
    """
    today_str = date.today().isoformat()
    
    # 1. Cargar el historial completo de aperturas
    all_initials = load_initial_rates()

    # 2. Verificar si ya existe una apertura para hoy
    if today_str not in all_initials:
        # 3. Si no existe, guardar las tasas actuales como apertura
        all_initials[today_str] = rates
        
        # 4. Guardar el archivo actualizado
        save_json(INITIAL_RATES_FILE, all_initials)