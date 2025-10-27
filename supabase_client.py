import requests
import os

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_API_KEY = os.getenv("SUPABASE_API_KEY")

headers = {
    "apikey": SUPABASE_API_KEY,
    "Authorization": f"Bearer {SUPABASE_API_KEY}",
    "Content-Type": "application/json",
}

def insertar_cotizacion(dolar_type, compra, venta, timestamp):
    url = f"{SUPABASE_URL}/rest/v1/cotizaciones"
    data = {
        "dolar_type": dolar_type,
        "compra": compra,
        "venta": venta,
        "timestamp": timestamp
    }
    response = requests.post(url, json=data, headers=headers)
    if response.status_code == 201:
        print("Cotización guardada correctamente")
    else:
        print("Error guardando cotización:", response.text)
