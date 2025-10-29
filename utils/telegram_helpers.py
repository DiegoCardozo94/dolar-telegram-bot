# utils/telegram_helpers.py

from utils.file_helpers import log_error
from utils.telegram_client import send_telegram_message # Asume que esta librería existe
from config.constants import CHAT_ID

def safe_send_message(msg):
    """Envía un mensaje a Telegram y registra errores si falla."""
    try:
        # Se asume que CHAT_ID se carga correctamente de las variables de entorno
        send_telegram_message(CHAT_ID, msg)
    except Exception as e:
        log_error(f"Error enviando mensaje de Telegram: {e}")