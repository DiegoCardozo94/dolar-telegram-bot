from flask import Flask, render_template
from datetime import datetime
import random, locale
from services.dolar_services import load_last_rates, get_all_dolar_rates, save_last_rates

app = Flask(__name__)

# ----------------- Helpers -----------------
def emoji(diff):
    if diff > 0: return "🟢"
    elif diff < 0: return "🔴"
    else: return "🟡"

# Valores iniciales para el mock
initial_rates_mock = {
    "oficial": 350,
    "blue": 650,
    "mep": 630,
    "ccl": 640,
    "tarjeta": 580,
    "cripto": 600,
    "mayorista": 345
}

# Valores iniciales del día para la API real
initial_rates_real = {}

def prepare_data(data_dict, initial_dict=None):
    """Calcula emojis y variaciones %"""
    prepared = {}
    for name, rates in data_dict.items():
        try:
            compra = float(rates.get("compra", rates)) if isinstance(rates, dict) else float(rates)
            venta = float(rates.get("venta", rates)) if isinstance(rates, dict) else float(rates)

            if initial_dict is not None:
                if name not in initial_dict:
                    initial_dict[name] = {"compra": compra, "venta": venta}
                diff_compra = compra - initial_dict[name]["compra"]
                diff_venta = venta - initial_dict[name]["venta"]
                pct_compra = f"{(diff_compra / initial_dict[name]['compra'] * 100):+.2f}%"
                pct_venta = f"{(diff_venta / initial_dict[name]['venta'] * 100):+.2f}%"
            else:
                diff_compra = diff_venta = 0
                pct_compra = pct_venta = "+0.00%"
        except Exception:
            compra = venta = diff_compra = diff_venta = 0
            pct_compra = pct_venta = "+0.00%"

        prepared[name] = {
            "compra": f"{compra:.2f}",
            "venta": f"{venta:.2f}",
            "emoji_compra": emoji(diff_compra),
            "emoji_venta": emoji(diff_venta),
            "pct_compra": pct_compra,
            "pct_venta": pct_venta
        }
    return prepared

# ----------------- Routes -----------------
@app.route("/mock")
def mock_rates():
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    full_date = get_full_date()
    data = {}
    for name, initial in initial_rates_mock.items():
        compra = initial + random.uniform(-5, 5)
        venta = initial + random.uniform(-5, 5)
        data[name] = {"compra": compra, "venta": venta}

    prepared = prepare_data(data, {k: {"compra": v, "venta": v} for k, v in initial_rates_mock.items()})

    # Actualizo el mock para la próxima vez (compra y venta)
    for name in data:
        initial_rates_mock[name] = (data[name]["compra"] + data[name]["venta"]) / 2

    return render_template("dolar_table.html", title="Mock Cotizaciones", now=now, full_date=full_date, data=prepared)

# Configuramos locale a español (funciona en sistemas donde está disponible)
try:
    locale.setlocale(locale.LC_TIME, "es_ES.UTF-8")
except locale.Error:
    # Windows o sistemas sin locale instalado
    locale.setlocale(locale.LC_TIME, "Spanish_Spain")

def get_full_date():
    now = datetime.now()
    # Ejemplo: Lunes 27 de Octubre
    day_name = now.strftime("%A").capitalize()
    day_num = now.day
    month_name = now.strftime("%B").capitalize()
    return f"Cotización del dólar hoy {day_name} {day_num} de {month_name}"

# En tu función Flask, haces algo así:
@app.route("/real")
def real_rates():
    data = get_all_dolar_rates()
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    full_date = get_full_date()

    try:
        last_rates = load_last_rates()
        prepared = prepare_data(data, last_rates)
        save_last_rates(data)
    except Exception as e:
        return f"⚠️ Error obteniendo cotizaciones: {e}"

    return render_template("dolar_table.html", title="Cotizaciones Reales", now=now, full_date=full_date, data=prepared)
# ----------------- Run -----------------
if __name__ == "__main__":
    app.run(debug=True)
