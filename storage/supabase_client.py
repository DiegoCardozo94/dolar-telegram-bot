# storage/supabase_client.py

import os
import requests
from utils.file_helpers import log_error # Reutilizamos el logger

# --- Configuración ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_API_KEY = os.getenv("SUPABASE_API_KEY")

headers = {
    "apikey": SUPABASE_API_KEY,
    "Authorization": f"Bearer {SUPABASE_API_KEY}",
    "Content-Type": "application/json",
}
# ---------------------

def insertar_cotizacion_supabase(dolar_name, compra, venta, diff_compra, diff_venta, pct_compra, pct_venta, timestamp):
    """Inserta una cotización histórica en la tabla de Supabase."""
    
    if not SUPABASE_URL or not SUPABASE_API_KEY:
        log_error("Faltan variables de entorno para Supabase. Omitiendo guardado.")
        return

    url = f"{SUPABASE_URL}/rest/v1/cotizaciones"
    data = {
        "dolar_name": dolar_name,
        "compra": compra,
        "venta": venta,
        "diff_compra": diff_compra,
        "diff_venta": diff_venta,
        "pct_compra": pct_compra,
        "pct_venta": pct_venta,
        "timestamp": timestamp,
    }
    try:
        response = requests.post(url, json=data, headers=headers)
        if response.status_code not in [200, 201]:
            log_error(f"Error guardando en Supabase (status {response.status_code}): {response.text}")
    except Exception as e:
        log_error(f"Excepción conectando a Supabase: {e}")