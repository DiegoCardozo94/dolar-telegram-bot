import requests, os, csv, json
from datetime import datetime

DOLAR_API = "https://dolarapi.com/v1/dolares"
HISTORY_FILE = "data/dolar_history.csv"
LAST_RATES_FILE = "data/last_rates.json"

def log_rates(rates):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    file_exists = os.path.isfile(HISTORY_FILE)
    os.makedirs("data", exist_ok=True)
    with open(HISTORY_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["timestamp", "oficial", "blue", "mep", "ccl"])
        writer.writerow([now, rates.get("oficial", ""), rates.get("blue", ""), rates.get("mep", ""), rates.get("ccl", "")])

def fetch_dolar_rates():
    try:
        resp = requests.get(DOLAR_API, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        rates, last_update = {}, None

        for item in data:
            nombre = item["nombre"].lower()
            compra = item.get("compra")
            venta = item.get("venta")
            if compra is None or venta is None:
                continue
            promedio = (compra + venta) / 2

            fecha = item.get("fechaActualizacion")
            if fecha:
                dt = datetime.fromisoformat(fecha.replace("Z", "+00:00"))
                if not last_update or dt > last_update:
                    last_update = dt

            if "oficial" in nombre:
                rates["oficial"] = {"compra": compra, "venta": venta, "promedio": promedio}
            elif "blue" in nombre:
                rates["blue"] = {"compra": compra, "venta": venta, "promedio": promedio}
            elif "bolsa" in nombre or "mep" in nombre:
                rates["mep"] = {"compra": compra, "venta": venta, "promedio": promedio}
            elif "contado con liqui" in nombre or "ccl" in nombre:
                rates["ccl"] = {"compra": compra, "venta": venta, "promedio": promedio}
            elif "tarjeta" in nombre:
                rates["tarjeta"] = {"compra": compra, "venta": venta, "promedio": promedio}
            elif "cripto" in nombre:
                rates["cripto"] = {"compra": compra, "venta": venta, "promedio": promedio}
            elif "mayorista" in nombre:
                rates["mayorista"] = {"compra": compra, "venta": venta, "promedio": promedio}

        fecha_str = last_update.astimezone().strftime("%d/%m/%Y %H:%M") if last_update else "desconocida"
        return {"rates": rates, "updated_at": fecha_str}

    except Exception as e:
        return {"error": f"No se pudo obtener la cotización ({e})"}

def format_message(result, tipo=None):
    if "error" in result:
        return result["error"]

    rates = result["rates"]
    updated_at = result.get("updated_at", "fecha desconocida")

    # Función interna para formatear cada tipo
    def format_rate(name, data):
        emojis = {
            "oficial": "🏦",
            "blue": "💵",
            "mep": "📊",
            "ccl": "💹",
            "bolsa": "📈",
            "tarjeta": "💳",
            "cripto": "🪙",
            "mayorista": "🏛️"
        }
        e = emojis.get(name, "💰")
        return f"{e} *{name.capitalize()}*\n   Compra: ${data['compra']}\n   Venta: ${data['venta']}\n"

    # Si el usuario pide un tipo específico
    if tipo and tipo in rates:
        return format_rate(tipo, rates[tipo]) + f"🕒 Actualizado: {updated_at}"

    # Mensaje completo
    msg = "\n".join([format_rate(k, v) for k, v in rates.items()])
    msg += f"\n🕒 Última actualización: {updated_at}"
    return msg

def load_last_rates():
    try:
        with open(LAST_RATES_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_last_rates(rates):
    os.makedirs("data", exist_ok=True)
    with open(LAST_RATES_FILE, "w") as f:
        json.dump(rates, f)
