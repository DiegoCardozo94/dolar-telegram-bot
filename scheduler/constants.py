# scheduler/constants.py

import os

# --- Configuración de Archivos ---
DATA_FILE = "data/last_rates.json"
HISTORY_CSV_FILE = "data/dolar_history.csv"
HISTORY_JSON_FILE = "data/history.json"  # ¡CONSTANTE AGREGADA!
ERROR_LOG = "logs/errors.log"

# --- Configuración de Telegram y Supabase ---
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# --- Configuración del Scheduler y del Monitoreo ---
CHECK_INTERVAL_MINUTES = 5
MIN_CHANGE_THRESHOLD = 0.5

# Tipos de Dólar (Opcional mantener aquí para referencia)
DOLAR_TYPES = ["oficial", "blue", "mep", "ccl", "tarjeta", "cripto", "mayorista"]