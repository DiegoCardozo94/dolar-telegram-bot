from utils.telegram_client import send_telegram_message
from services.dolar_services import fetch_dolar_rates, load_last_rates, save_last_rates
from datetime import datetime
import os

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_daily_notification():
    current_hour = datetime.now().hour
    if not (10 <= current_hour < 17):
        print("⏰ Fuera del horario bancario.")
        return

    current_data = fetch_dolar_rates()
    if "error" in current_data:
        print("❌ No se pudo obtener la cotización.")
        return

    rates = current_data["rates"]
    last_rates = load_last_rates()
    changes = []

    if last_rates:
        for tipo, valor in rates.items():
            if tipo in last_rates:
                diff = round(valor - last_rates[tipo], 2)
                if abs(diff) >= 2:
                    arrow = "📈" if diff > 0 else "📉"
                    changes.append(f"{arrow} Dólar {tipo}: cambio de ${diff} (ahora ${valor})")
    else:
        print("Primera ejecución registrada.")

    if changes:
        message = "⚡ Actualización:\n" + "\n".join(changes)
        message += f"\n\n🕒 {current_data['updated_at']}"
        send_telegram_message(message)  # <-- aquí se manda a Telegram
        print("✅ Notificación enviada.")

    save_last_rates(rates)
    print("✅ Datos guardados.")