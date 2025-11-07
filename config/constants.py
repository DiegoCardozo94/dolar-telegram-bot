# config/constants.py

import os
from pathlib import Path

# 1. Definir la ruta base del proyecto
# BASE_DIR correcto para una estructura limpia (data/ en la raíz)
BASE_DIR = Path(__file__).resolve().parent.parent

# --- Configuración de Archivos (Rutas Absolutas) ---
# Ahora la ruta será correcta: /.../DOLAR-WHATSAPP/config/data/history.json
DATA_FILE = BASE_DIR / "data" / "last_rates.json"
HISTORY_CSV_FILE = BASE_DIR / "data" / "dolar_history.csv"
HISTORY_JSON_FILE = BASE_DIR / "data" / "history.json"
ERROR_LOG = Path(__file__).resolve().parent.parent / "logs" / "errors.log"
INITIAL_RATES_FILE = BASE_DIR / "data" / "initial_rates.json" 

# --- Configuración de Telegram y Supabase ---
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# --- Configuración del Scheduler y del Monitoreo ---
CHECK_INTERVAL_MINUTES = 5
MIN_CHANGE_THRESHOLD = 0.00001 

# Tipos de Dólar (Opcional mantener aquí para referencia)
DOLAR_TYPES = ["oficial", "blue", "mep", "ccl", "tarjeta", "cripto", "mayorista"]