from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import json, os, csv
from services.dolar_services import get_all_dolar_rates
from utils.telegram_client import send_telegram_message
import pandas as pd
from services.dolar_services import fetch_dolar_rates

# ⚙️ Configuración
DATA_FILE = "data/last_rates.json"
HISTORY_JSON_FILE = "data/history.json"

HISTORY_CSV_FILE = "data/dolar_history.csv"
os.makedirs(os.path.dirname(HISTORY_CSV_FILE), exist_ok=True)

ERROR_LOG = "logs/errors.log"
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
CHECK_INTERVAL_MINUTES = 5
MIN_CHANGE_THRESHOLD = 0.5  # aviso solo si cambió al menos $0.50

# Tipos de dólar que queremos registrar
DOLAR_TYPES = ["oficial", "blue", "mep", "ccl", "tarjeta", "cripto", "mayorista"]

scheduler = BackgroundScheduler()
last_rates = {}
market_open_sent = False
market_close_sent = False

# ---------------- Funciones auxiliares ----------------
def ensure_dirs():
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    os.makedirs(os.path.dirname(HISTORY_JSON_FILE), exist_ok=True)
    os.makedirs(os.path.dirname(ERROR_LOG), exist_ok=True)

def log_error(msg):
    ensure_dirs()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(ERROR_LOG, "a") as f:
        f.write(f"[{timestamp}] {msg}\n")
    print(f"⚠️ {msg}")

def safe_send_message(chat_id, msg):
    try:
        send_telegram_message(chat_id, msg)
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
    if diff > 0: return "🟢"
    elif diff < 0: return "🔴"
    else: return "🟡"

# ---------------- Función principal ----------------
def check_dolar_changes():
    global last_rates, market_open_sent, market_close_sent
    now = datetime.now()

    # Apertura
    if now.hour == 10 and not market_open_sent:
        safe_send_message(CHAT_ID, "🏦 ¡El mercado abrió! Comenzando monitoreo de cotizaciones...")
        market_open_sent = True

    # Cierre
    if now.hour == 17 and not market_close_sent:
        safe_send_message(CHAT_ID, "🏛️ ¡El mercado cerró! Monitoreo finalizado por hoy.")
        market_close_sent = True

    # Solo monitoreo entre 10 y 17
    if not (10 <= now.hour < 17):
        return

    try:
        current_rates = get_all_dolar_rates()
    except Exception as e:
        log_error(f"Error obteniendo cotizaciones: {e}")
        return

    messages = []
    history = load_json(HISTORY_JSON_FILE)

    for name, data in current_rates.items():
        try:
            current_compra = float(data["compra"])
            current_venta = float(data["venta"])
        except (KeyError, TypeError, ValueError):
            continue

        last_data = last_rates.get(name, {})
        last_compra = last_data.get("compra")
        last_venta = last_data.get("venta")

        diff_compra = (current_compra - last_compra) if last_compra else 0
        diff_venta = (current_venta - last_venta) if last_venta else 0
        pct_compra = round((diff_compra / last_compra) * 100, 2) if last_compra else 0
        pct_venta = round((diff_venta / last_venta) * 100, 2) if last_venta else 0

        if abs(diff_compra) >= MIN_CHANGE_THRESHOLD or abs(diff_venta) >= MIN_CHANGE_THRESHOLD:
            msg = (
                f"{name.replace('_',' ').title()}\n"
                f"   Compra: {emoji(diff_compra)} ${current_compra:.2f} ({diff_compra:+.2f}, {pct_compra:+.2f}%)\n"
                f"   Venta:  {emoji(diff_venta)} ${current_venta:.2f} ({diff_venta:+.2f}, {pct_venta:+.2f}%)"
            )
            messages.append(msg)

        # Guardar historial en JSON y CSV
        log_history_if_significant(
            dolar_name=name,
            compra=current_compra,
            venta=current_venta,
            last_compra=last_compra,
            last_venta=last_venta
        )

        # Actualizar último valor
        last_rates[name] = {"compra": current_compra, "venta": current_venta}

    # Guardar últimos datos
    save_json(DATA_FILE, last_rates)

    if messages:
        final_message = "\n\n".join(messages)
        safe_send_message(CHAT_ID, final_message)

# ---------------- Resumen diario ----------------
def send_daily_summary():
    check_dolar_changes()  # reutiliza lógica de cambios y guardado

# ---------------- Reset de flags ----------------
def reset_market_flags():
    global market_open_sent, market_close_sent
    market_open_sent = False
    market_close_sent = False

# ---------------- Función de historial ----------------
def log_history_if_significant(dolar_name, compra, venta, last_compra, last_venta):
    diff_compra = compra - last_compra if last_compra is not None else 0
    diff_venta = venta - last_venta if last_venta is not None else 0

    if abs(diff_compra) < MIN_CHANGE_THRESHOLD and abs(diff_venta) < MIN_CHANGE_THRESHOLD:
        return

    timestamp = datetime.now().isoformat()

    # JSON
    history_data = load_json(HISTORY_JSON_FILE)
    history_data.setdefault(dolar_name, [])
    history_data[dolar_name].append({
        "timestamp": timestamp,
        "compra": compra,
        "venta": venta,
        "diff_compra": diff_compra,
        "diff_venta": diff_venta
    })
    save_json(HISTORY_JSON_FILE, history_data)

    # CSV
    os.makedirs(os.path.dirname(HISTORY_CSV_FILE), exist_ok=True)
    file_exists = os.path.exists(HISTORY_CSV_FILE)
    with open(HISTORY_CSV_FILE, mode="a", newline="", encoding="utf-8") as csvfile:
        fieldnames = ["timestamp", "dolar_name", "compra", "venta", "diff_compra", "diff_venta"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow({
            "timestamp": timestamp,
            "dolar_name": dolar_name,
            "compra": compra,
            "venta": venta,
            "diff_compra": diff_compra,
            "diff_venta": diff_venta
        })

def log_rates_auto():
    """Función que se ejecuta automáticamente cada intervalo y guarda cotizaciones en CSV."""
    try:
        data = fetch_dolar_rates()
        rates = data.get("rates", {})
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row = {"timestamp": timestamp}
        
        for tipo in DOLAR_TYPES:
            r = rates.get(tipo, {})
            try:
                row[tipo] = float(r.get("venta", 0))
            except (ValueError, TypeError):
                row[tipo] = 0

        file_exists = os.path.isfile(HISTORY_CSV_FILE)
        df = pd.DataFrame([row])
        df.to_csv(HISTORY_CSV_FILE, mode='a', header=not file_exists, index=False)
        print(f"✅ Cotizaciones guardadas: {timestamp}")
    
    except Exception as e:
        print(f"⚠️ Error guardando cotizaciones automáticas: {e}")

# ---------------- Inicializar scheduler ----------------
def start_scheduler():
    global last_rates
    last_rates = load_json(DATA_FILE)
    scheduler.add_job(check_dolar_changes, "interval", minutes=CHECK_INTERVAL_MINUTES)
    scheduler.add_job(send_daily_summary, "cron", hour=17, minute=1)
    scheduler.add_job(reset_market_flags, "cron", hour=0, minute=1)
    scheduler.add_job(log_rates_auto, 'interval', minutes=5, id='log_rates_job', replace_existing=True)

    scheduler.start()
    print("✅ Scheduler iniciado (monitoreo de cotizaciones activo)")
    # Primer chequeo inmediato
    check_dolar_changes()
