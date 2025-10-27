# services/storage.py

import os
import json
import csv
from datetime import datetime
import requests

# ---------------- Configuración ----------------
DATA_FILE = "data/last_rates.json"
HISTORY_JSON_FILE = "data/history.json"
HISTORY_CSV_FILE = "data/dolar_history.csv"

MIN_CHANGE_THRESHOLD = 0.5  # mínimo cambio para guardar historial

# Supabase config
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_API_KEY = os.getenv("SUPABASE_API_KEY")
SUPABASE_HEADERS = {
    "apikey": SUPABASE_API_KEY,
    "Authorization": f"Bearer {SUPABASE_API_KEY}",
    "Content-Type": "application/json",
}

# ---------------- Funciones auxiliares ----------------
def ensure_dirs():
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    os.makedirs(os.path.dirname(HISTORY_JSON_FILE), exist_ok=True)
    os.makedirs(os.path.dirname(HISTORY_CSV_FILE), exist_ok=True)

def load_json(file_path):
    if os.path.exists(file_path):
        try:
            with open(file_path, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Error leyendo {file_path}: {e}")
    return {}

def save_json(file_path, data):
    ensure_dirs()
    try:
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"⚠️ Error escribiendo {file_path}: {e}")

# ---------------- Función principal ----------------
def guardar_cotizacion(dolar_name, compra, venta, diff_compra, diff_venta, pct_compra, pct_venta, timestamp=None):
    """
    Guarda la cotización en JSON, CSV y Supabase si hay cambios significativos.
    """
    ensure_dirs()
    timestamp = timestamp or datetime.now().isoformat()

    # ---------- JSON ----------
    history_data = load_json(HISTORY_JSON_FILE)
    history_data.setdefault(dolar_name, [])
    history_data[dolar_name].append({
        "timestamp": timestamp,
        "compra": compra,
        "venta": venta,
        "diff_compra": diff_compra,
        "diff_venta": diff_venta,
        "pct_compra": pct_compra,
        "pct_venta": pct_venta
    })
    save_json(HISTORY_JSON_FILE, history_data)

    # ---------- CSV ----------
    file_exists = os.path.exists(HISTORY_CSV_FILE)
    with open(HISTORY_CSV_FILE, mode="a", newline="", encoding="utf-8") as csvfile:
        fieldnames = ["timestamp", "dolar_name", "compra", "venta", "diff_compra", "diff_venta", "pct_compra", "pct_venta"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow({
            "timestamp": timestamp,
            "dolar_name": dolar_name,
            "compra": compra,
            "venta": venta,
            "diff_compra": diff_compra,
            "diff_venta": diff_venta,
            "pct_compra": pct_compra,
            "pct_venta": pct_venta
        })

    # ---------- Supabase ----------
    if SUPABASE_URL and SUPABASE_API_KEY:
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
            response = requests.post(url, json=data, headers=SUPABASE_HEADERS)
            if response.status_code not in [200, 201]:
                print(f"⚠️ Error guardando en Supabase: {response.text}")
        except Exception as e:
            print(f"⚠️ Error conectando a Supabase: {e}")

    print(f"✅ Cotización guardada para {dolar_name} (compra: {compra}, venta: {venta}, diff_compra: {diff_compra}, diff_venta: {diff_venta}, pct_compra: {pct_compra}, pct_venta: {pct_venta})")