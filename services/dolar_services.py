import requests, os, csv, json
from datetime import datetime
from services.storage import guardar_cotizacion
# ---------------- Config ----------------
DOLAR_API = "https://dolarapi.com/v1/dolares"
HISTORY_FILE = "data/dolar_history.csv"
LAST_RATES_FILE = "data/last_rates.json"

DOLAR_TYPES = ["oficial", "blue", "mep", "ccl", "tarjeta", "cripto", "mayorista"]

# ---------------- Funciones de persistencia ----------------
def load_last_rates():
    try:
        with open(LAST_RATES_FILE, "r") as f:
            content = f.read().strip()
            if not content:
                return {}  # archivo vacío → devolvemos dict vacío
            return json.loads(content)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}  # JSON inválido → devolvemos dict vacío

def save_last_rates(rates):
    """Guarda las cotizaciones en JSON, creando la carpeta si no existe."""
    os.makedirs(os.path.dirname(LAST_RATES_FILE), exist_ok=True)
    try:
        with open(LAST_RATES_FILE, "w", encoding="utf-8") as f:
            json.dump(rates, f, ensure_ascii=False, indent=4)
    except IOError as e:
        print(f"⚠️ No se pudo guardar last_rates.json: {e}")

def load_last_rates():
    """Carga las últimas cotizaciones desde JSON. Devuelve {} si no existe o está vacío/corrupto."""
    try:
        if not os.path.exists(LAST_RATES_FILE):
            return {}
        with open(LAST_RATES_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return {}
            return json.loads(content)
    except (json.JSONDecodeError, IOError):
        return {}

def log_rates_csv(rates):
    """Registra las cotizaciones en un CSV histórico."""
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

# ---------------- Función para traer cotizaciones ----------------
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

        last_rates = load_last_rates()
        for tipo, data in rates.items():
            last = last_rates.get(tipo, {})
            last_compra = last.get("compra", 0)
            last_venta = last.get("venta", 0)

            diff_compra = data["compra"] - last_compra
            diff_venta = data["venta"] - last_venta
            pct_compra = round((diff_compra / last_compra) * 100, 2) if last_compra else 0
            pct_venta = round((diff_venta / last_venta) * 100, 2) if last_venta else 0

            guardar_cotizacion(tipo, data["compra"], data["venta"], diff_compra, diff_venta, pct_compra, pct_venta)

        save_last_rates(rates)

        return {"rates": rates, "updated_at": fecha_str}

    except Exception as e:
        return {"error": f"No se pudo obtener la cotización ({e})"}

# ---------------- Función para formatear mensajes con variación ----------------
def format_message(result, last_rates, tipo=None):
    if "error" in result:
        return result["error"]

    rates = result["rates"]
    updated_at = result.get("updated_at", "fecha desconocida")

    def emoji(diff):
        if diff > 0: return "🟢"
        elif diff < 0: return "🔴"
        else: return "🟡"

    def format_rate(name, data):
        last = last_rates.get(name, {})
        last_compra = last.get("compra")
        last_venta = last.get("venta")

        diff_compra = data["compra"] - last_compra if last_compra else 0
        diff_venta = data["venta"] - last_venta if last_venta else 0
        pct_compra = round((diff_compra / last_compra) * 100, 2) if last_compra else 0
        pct_venta = round((diff_venta / last_venta) * 100, 2) if last_venta else 0

        emojis = {
            "oficial": "🏦",
            "blue": "💵",
            "mep": "📊",
            "ccl": "💹",
            "tarjeta": "💳",
            "cripto": "🪙",
            "mayorista": "🏛️"
        }
        e = emojis.get(name, "💰")

        return (
            f"{e} *{name.capitalize()}*\n"
            f"   Compra: {emoji(diff_compra)} ${data['compra']} ({diff_compra:+.2f}, {pct_compra:+.2f}%)\n"
            f"   Venta:  {emoji(diff_venta)} ${data['venta']} ({diff_venta:+.2f}, {pct_venta:+.2f}%)\n"
        )

    # Mostrar solo el tipo pedido
    if tipo:
        tipo = tipo.lower()
        if tipo in rates:
            return format_rate(tipo, rates[tipo]) + f"\n🕒 Última actualización: {updated_at}"
        else:
            return f"No se encontró el tipo '{tipo}'. Tipos disponibles: {', '.join(DOLAR_TYPES)}"

    # Mostrar todos los tipos
    msg = "\n".join([format_rate(k, v) for k, v in rates.items()])
    msg += f"\n🕒 Última actualización: {updated_at}"
    return msg

# ---------------- Función para uso de scheduler ----------------
def get_all_dolar_rates():
    result = fetch_dolar_rates()
    if "rates" in result:
        return result["rates"]
    return {}

def save_changes(rates, last_rates):
    for tipo, data in rates.items():
        last = last_rates.get(tipo, {})
        last_compra = last.get("compra", 0)
        last_venta = last.get("venta", 0)

        diff_compra = data["compra"] - last_compra
        diff_venta = data["venta"] - last_venta
        pct_compra = round((diff_compra / last_compra) * 100, 2) if last_compra else 0
        pct_venta = round((diff_venta / last_venta) * 100, 2) if last_venta else 0

        # Guardar en JSON, CSV y Supabase
        guardar_cotizacion(tipo, data["compra"], data["venta"], diff_compra, diff_venta, pct_compra, pct_venta)

    # Actualizar last_rates
    save_last_rates(rates)

def prepare_data_for_html(rates, last_rates=None):
    def emoji(diff):
        return "🟢" if diff > 0 else "🔴" if diff < 0 else "🟡"

    prepared = {}
    for name, data in rates.items():
        last = last_rates.get(name, {}) if last_rates else {}
        last_compra = last.get("compra", 0)
        last_venta = last.get("venta", 0)

        compra = data.get("compra", 0)
        venta = data.get("venta", 0)
        diff_compra = compra - last_compra
        diff_venta = venta - last_venta
        pct_compra = f"{(diff_compra / last_compra * 100):+.2f}%" if last_compra else "+0.00%"
        pct_venta = f"{(diff_venta / last_venta * 100):+.2f}%" if last_venta else "+0.00%"

        prepared[name] = {
            "compra": f"{compra:.2f}",
            "venta": f"{venta:.2f}",
            "emoji_compra": emoji(diff_compra),
            "emoji_venta": emoji(diff_venta),
            "pct_compra": pct_compra,
            "pct_venta": pct_venta
        }
    return prepared
