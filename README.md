# Dólar Telegram Bot

Bot de Telegram que envía las cotizaciones del dólar argentino en tiempo real y permite notificaciones automáticas. Implementado con **FastAPI** y **APScheduler**.

## Características

- Responde a comandos de Telegram para obtener distintas cotizaciones del dólar.  
- Notificaciones automáticas cada 30 minutos.  
- Diseño modular: `services` para lógica de cotizaciones y `utils` para helpers de Telegram.

## Comandos disponibles

| Comando | Descripción |
|---------|-------------|
| `/dolar` | Todas las cotizaciones |
| `/dolar_oficial` | Dólar oficial |
| `/dolar_blue` | Dólar blue |
| `/dolar_mep` | Dólar MEP / Bolsa |
| `/dolar_ccl` | Contado con Liquidación |
| `/dolar_tarjeta` | Dólar tarjeta |
| `/dolar_cripto` | Dólar cripto |
| `/dolar_mayorista` | Dólar mayorista |

## Requisitos

- Python 3.10+  
- pip  
- Ngrok (para exponer localmente el servidor)  
- Telegram Bot Token

## Instalación

1. Clonar el repositorio:
```bash
git clone https://github.com/tuusuario/dolar-whatsapp.git
cd dolar-bot
```

2. Crear y activar un entorno virtual
```
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

3. Instalar dependencias
```
pip install -r requirements.txt
```

4. Crear un archivo `.env` con tus credenciales
```
TELEGRAM_TOKEN=8326548369:AAENidLIsFUbgYBEgoPmZ-PVJiDg2KkRmY4
TELEGRAM_CHAT_ID=7846254050
```

5. Configuracion de NGROK
```
ngrok http 8000
```

6. Configurar el Webhook de Telegram
```
curl -X POST "https://api.telegram.org/bot<TU_TELEGRAM_TOKEN>/setWebhook?url=<TU_URL_NGROK>/webhook"
```

7. Ejecutar uvicorn
```
uvicorn main:app --reload
```

8. Enviale mensajes al bot de telegram y deberia responder sin problemas