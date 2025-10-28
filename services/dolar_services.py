import requests, os, csv, json
from datetime import datetime
from services.storage import guardar_cotizacion

# ---------------- Config ----------------
DOLAR_API = "https://dolarapi.com/v1/dolares"
HISTORY_FILE = "data/dolar_history.csv"
LAST_RATES_FILE = "data/last_rates.json"
INITIAL_RATES_FILE = "data/initial_rates.json"

DOLAR_TYPES = ["oficial", "blue", "mep", "ccl", "tarjeta", "cripto", "mayorista"]

# ---------------- Funciones de persistencia ----------------
def save_json(file_path, data):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except IOError as e:
        print(f"⚠️ No se pudo guardar {file_path}: {e}")

def load_json(file_path):
    try:
        if not os.path.exists(file_path):
            return {}
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            return json.loads(content) if content else {}
    except (json.JSONDecodeError, IOError):
        return {}

def save_last_rates(rates):
    save_json(LAST_RATES_FILE, rates)

def load_last_rates():
    return load_json(LAST_RATES_FILE)

def save_initial_rates(rates):
    save_json(INITIAL_RATES_FILE, rates)

def load_initial_rates():
    return load_json(INITIAL_RATES_FILE)

def log_rates_csv(rates):
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    file_exists = os.path.isfile(HISTORY_FILE)
    try:
        with open(HISTORY_FILE, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["timestamp"] + DOLAR_TYPES)
            row = [now] + [rates.get(tipo, {}).get("venta", "") for tipo in DOLAR_TYPES]
            writer.writerow(row)
    except IOError as e:
        print(f"⚠️ No se pudo registrar en el CSV: {e}")

# ---------------- Funciones de cálculo ----------------
def compute_diff(data, last):
    last_compra = last.get("compra", 0)
    last_venta = last.get("venta", 0)
    diff_compra = data["compra"] - last_compra
    diff_venta = data["venta"] - last_venta
    pct_compra = round((diff_compra / last_compra) * 100, 2) if last_compra else 0
    pct_venta = round((diff_venta / last_venta) * 100, 2) if last_venta else 0
    return diff_compra, diff_venta, pct_compra, pct_venta

# ---------------- Función para traer cotizaciones ----------------
def fetch_dolar_rates():
    try:
        resp = requests.get(DOLAR_API, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        rates, last_update = {}, None

        for item in data:
            nombre = item["nombre"].lower()
            compra, venta = item.get("compra"), item.get("venta")
            if compra is None or venta is None:
                continue
            promedio = (compra + venta) / 2
            fecha = item.get("fechaActualizacion")
            if fecha:
                dt = datetime.fromisoformat(fecha.replace("Z", "+00:00"))
                if not last_update or dt > last_update:
                    last_update = dt

            if "oficial" in nombre: rates["oficial"] = {"compra": compra, "venta": venta, "promedio": promedio}
            elif "blue" in nombre: rates["blue"] = {"compra": compra, "venta": venta, "promedio": promedio}
            elif "bolsa" in nombre or "mep" in nombre: rates["mep"] = {"compra": compra, "venta": venta, "promedio": promedio}
            elif "contado con liqui" in nombre or "ccl" in nombre: rates["ccl"] = {"compra": compra, "venta": venta, "promedio": promedio}
            elif "tarjeta" in nombre: rates["tarjeta"] = {"compra": compra, "venta": venta, "promedio": promedio}
            elif "cripto" in nombre: rates["cripto"] = {"compra": compra, "venta": venta, "promedio": promedio}
            elif "mayorista" in nombre: rates["mayorista"] = {"compra": compra, "venta": venta, "promedio": promedio}

        fecha_str = last_update.astimezone().strftime("%d/%m/%Y %H:%M") if last_update else "desconocida"

        last_rates = load_last_rates()
        for tipo, data in rates.items():
            diff_compra, diff_venta, pct_compra, pct_venta = compute_diff(data, last_rates.get(tipo, {}))
            guardar_cotizacion(tipo, data["compra"], data["venta"], diff_compra, diff_venta, pct_compra, pct_venta)

        save_last_rates(rates)
        return {"rates": rates, "updated_at": fecha_str}

    except Exception as e:
        return {"error": f"No se pudo obtener la cotización ({e})"}

# ---------------- Formateo de mensajes ----------------
def format_message(result, last_rates, tipo=None):
    if "error" in result:
        return result["error"]
    rates = result["rates"]
    updated_at = result.get("updated_at", "fecha desconocida")

    def emoji(diff):
        return "🟢" if diff > 0 else "🔴" if diff < 0 else "🟡"

    def format_rate(name, data):
        last = last_rates.get(name, {})
        diff_compra, diff_venta, pct_compra, pct_venta = compute_diff(data, last)
        emojis = {"oficial":"🏦","blue":"💵","mep":"📊","ccl":"💹","tarjeta":"💳","cripto":"🪙","mayorista":"🏛️"}
        e = emojis.get(name, "💰")
        return (
            f"{e} *{name.capitalize()}*\n"
            f"   Compra: {emoji(diff_compra)} ${data['compra']} ({diff_compra:+.2f}, {pct_compra:+.2f}%)\n"
            f"   Venta:  {emoji(diff_venta)} ${data['venta']} ({diff_venta:+.2f}, {pct_venta:+.2f}%)\n"
        )

    if tipo:
        tipo = tipo.lower()
        if tipo in rates:
            return format_rate(tipo, rates[tipo]) + f"\n🕒 Última actualización: {updated_at}"
        return f"No se encontró el tipo '{tipo}'. Tipos disponibles: {', '.join(DOLAR_TYPES)}"

    msg = "\n".join([format_rate(k, v) for k, v in rates.items()])
    return msg + f"\n🕒 Última actualización: {updated_at}"

# ---------------- Funciones de uso general ----------------
def get_all_dolar_rates():
    result = fetch_dolar_rates()
    return result.get("rates", {})

def save_changes(rates, last_rates):
    for tipo, data in rates.items():
        diff_compra, diff_venta, pct_compra, pct_venta = compute_diff(data, last_rates.get(tipo, {}))
        guardar_cotizacion(tipo, data["compra"], data["venta"], diff_compra, diff_venta, pct_compra, pct_venta)
    save_last_rates(rates)
