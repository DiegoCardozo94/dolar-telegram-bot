# storage/json_history.py

from scheduler.constants import HISTORY_JSON_FILE
# Importamos las utilidades de archivos ya refactorizadas
from utils.file_helpers import load_json, save_json

def append_to_json_history(dolar_name: str, data: dict):
    """
    Agrega una nueva entrada de cotización al archivo JSON histórico.

    :param dolar_name: Nombre del tipo de dólar (ej. 'blue').
    :param data: Diccionario con los datos a guardar (timestamp, compra, venta, etc.).
    """
    try:
        # Carga el historial existente
        history_data = load_json(HISTORY_JSON_FILE)
        
        # Inicializa la lista si es la primera vez que se guarda este tipo de dólar
        history_data.setdefault(dolar_name, [])
        
        # Agrega la nueva entrada
        history_data[dolar_name].append(data)
        
        # Guarda el archivo JSON
        save_json(HISTORY_JSON_FILE, history_data)
        
    except Exception as e:
        # Reutilizamos el logger global si es necesario, o un simple print
        from utils.file_helpers import log_error 
        log_error(f"Error guardando historial JSON para {dolar_name}: {e}")