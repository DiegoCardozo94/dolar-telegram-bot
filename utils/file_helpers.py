# utils/file_helpers.py

import os
import json
from datetime import datetime
from config.constants import ERROR_LOG

def ensure_dirs(file_path):
    """Asegura que el directorio del archivo exista."""
    dir_name = os.path.dirname(file_path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)

def log_error(msg):
    """Guarda un mensaje de error en el archivo de log."""
    ensure_dirs(ERROR_LOG)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(ERROR_LOG, "a") as f:
        f.write(f"[{timestamp}] {msg}\n")
    print(f"⚠️ {msg}")

def load_json(file_path):
    """Carga datos desde un archivo JSON, con manejo de errores."""
    if os.path.exists(file_path):
        try:
            with open(file_path, "r") as f:
                return json.load(f)
        except Exception as e:
            log_error(f"Error leyendo {file_path}: {e}")
    return {}

def save_json(file_path, data):
    """Guarda datos en un archivo JSON, con manejo de errores."""
    ensure_dirs(file_path)
    try:
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        log_error(f"Error escribiendo {file_path}: {e}")