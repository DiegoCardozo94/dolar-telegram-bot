from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import os, json, requests, pandas as pd
from services.dolar_services import fetch_dolar_rates
from services.storage import guardar_cotizacion
from utils.telegram_client import send_telegram_message

# ---------------- Config ----------------
DATA_FILE = "data/last_rates.json"
HISTORY_JSON_FILE = "data/history.json"
HISTORY_CSV_FILE = "data/dolar_history.csv"
ERROR_LOG = "logs/errors.log"
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
CHECK_INTERVAL_MINUTES = 5
MIN_CHANGE_THRESHOLD = 0.5

DOLAR_TYPES = ["oficial", "blue", "mep", "ccl", "tarjeta", "cripto", "mayorista"]

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_API_KEY = os.getenv("SUPABASE_API_KEY")

headers = {
    "apikey": SUPABASE_API_KEY,
    "Authorization": f"Bearer {SUPABASE_API_KEY}",
    "Content-Type": "application/json",
}

scheduler = BackgroundScheduler()
last_rates = {}
market_open_sent = False
market_close_sent = False

# ---------------- Utilidades ----------------
def ensure_dirs():
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    os.makedirs(os.path.dirname(HISTORY_JSON_FILE), exist_ok=True)
    os.makedirs(os.path.dirname(HISTORY_CSV_FILE), exist_ok=True)
    os.makedirs(os.path.dirname(ERROR_LOG), exist_ok=True)

def log_error(msg):
    ensure_dirs()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(ERROR_LOG, "a") as f:
        f.write(f"[{timestamp}] {msg}\n")
    print(f"⚠️ {msg}")

def safe_send_message(msg):
    try:
        send_telegram_message(CHAT_ID, msg)
    except Exception as e:
        log_error(f"Error enviando mensaje de Telegram: {e}")

def load_json(file_path):
    if os.path.exists(file_path):
        try:
            with open(file_path, "r") as f:
                return json.load(f)
        except Exception as e:
            log_error(f"Error leyendo {file_path}: {e}")
    return {}

def save_json(file_path, data):
    ensure_dirs()
    try:
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        log_error(f"Error escribiendo {file_path}: {e}")

def emoji(diff):
    return "🟢" if diff > 0 else "🔴" if diff < 0 else "🟡"

def insertar_cotizacion_supabase(dolar_name, compra, venta, diff_compra, diff_venta, pct_compra, pct_venta, timestamp):
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
        if response.status_code != 201:
            log_error(f"Error guardando cotización en Supabase: {response.text}")
    except Exception as e:
        log_error(f"Excepción guardando cotización en Supabase: {e}")

# ---------------- Lógica principal ----------------
def check_and_save_dolar():
    global last_rates, market_open_sent, market_close_sent
    now = datetime.now()

    # Apertura/Cierre
    if now.hour == 10 and not market_open_sent:
        safe_send_message("🏦 ¡El mercado abrió! Comenzando monitoreo de cotizaciones...")
        market_open_sent = True
    if now.hour == 17 and not market_close_sent:
        safe_send_message("🏛️ ¡El mercado cerró! Monitoreo finalizado por hoy.")
        market_close_sent = True
    if not (10 <= now.hour < 17):
        return

    # Fetch de cotizaciones
    try:
        data = fetch_dolar_rates()
        rates = data.get("rates", {})
        timestamp = now.isoformat()
    except Exception as e:
        log_error(f"Error obteniendo cotizaciones: {e}")
        return

    messages = []

    # Guardado histórico CSV y revisión de cambios
    os.makedirs(os.path.dirname(HISTORY_CSV_FILE), exist_ok=True)
    file_exists = os.path.isfile(HISTORY_CSV_FILE)
    csv_rows = []

    for name, info in rates.items():
        try:
            compra = float(info["compra"])
            venta = float(info["venta"])
        except (TypeError, ValueError, KeyError):
            continue

        last = last_rates.get(name, {})
        last_compra = last.get("compra", compra)
        last_venta = last.get("venta", venta)

        diff_compra = compra - last_compra
        diff_venta = venta - last_venta
        pct_compra = round((diff_compra / last_compra) * 100, 2) if last_compra else 0
        pct_venta = round((diff_venta / last_venta) * 100, 2) if last_venta else 0

        # CSV histórico
        csv_rows.append({
            "timestamp": timestamp,
            "dolar_name": name,
            "compra": compra,
            "venta": venta,
            "diff_compra": diff_compra,
            "diff_venta": diff_venta
        })

        # Guardar en Supabase/JSON solo si hay cambios significativos
        if abs(diff_compra) >= MIN_CHANGE_THRESHOLD or abs(diff_venta) >= MIN_CHANGE_THRESHOLD:
            msg = (
                f"{name.title()}\n"
                f"   Compra: {emoji(diff_compra)} ${compra:.2f} ({diff_compra:+.2f}, {pct_compra:+.2f}%)\n"
                f"   Venta:  {emoji(diff_venta)} ${venta:.2f} ({diff_venta:+.2f}, {pct_venta:+.2f}%)"
            )
            messages.append(msg)

            insertar_cotizacion_supabase(name, compra, venta, diff_compra, diff_venta, pct_compra, pct_venta, timestamp)
            guardar_cotizacion(name, compra, venta, diff_compra, diff_venta, pct_compra, pct_venta, timestamp)

        last_rates[name] = {"compra": compra, "venta": venta}

    # Guardar CSV histórico
    if csv_rows:
        df = pd.DataFrame(csv_rows)
        df.to_csv(HISTORY_CSV_FILE, mode='a', header=not file_exists, index=False)

    # Guardar últimos rates en JSON
    save_json(DATA_FILE, last_rates)

    # Enviar mensaje Telegram si hubo cambios
    if messages:
        safe_send_message("\n\n".join(messages))

# ---------------- Jobs del Scheduler ----------------
def send_daily_summary():
    safe_send_message("📊 Resumen diario de cotizaciones")
    check_and_save_dolar()

def reset_flags():
    global market_open_sent, market_close_sent
    market_open_sent = False
    market_close_sent = False

def start_scheduler():
    global last_rates
    last_rates = load_json(DATA_FILE)
    scheduler.add_job(check_and_save_dolar, "interval", minutes=CHECK_INTERVAL_MINUTES)
    scheduler.add_job(send_daily_summary, "cron", hour=17, minute=1)
    scheduler.add_job(reset_flags, "cron", hour=0, minute=1)
    scheduler.start()
    print("✅ Scheduler iniciado")
    check_and_save_dolar()  # primer chequeo inmediato
