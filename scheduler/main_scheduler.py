# scheduler/main_scheduler.py

from apscheduler.schedulers.background import BackgroundScheduler
from .tasks import check_and_save_dolar, send_daily_summary, reset_flags, last_rates
from .constants import CHECK_INTERVAL_MINUTES
from utils.file_helpers import load_json
from scheduler.constants import DATA_FILE

scheduler = BackgroundScheduler()

def start_scheduler():
    """Inicializa el estado y arranca todos los jobs del scheduler."""
    
    # 1. Inicialización de estado (Cargar la última cotización)
    # Se actualiza el diccionario global 'last_rates' importado de tasks.py
    last_rates.update(load_json(DATA_FILE))
    
    # 2. Programación de jobs
    # Job de chequeo periódico
    scheduler.add_job(check_and_save_dolar, "interval", minutes=CHECK_INTERVAL_MINUTES, id="dolar_check_job")
    
    # Job de resumen al cierre (17:01 hs)
    scheduler.add_job(send_daily_summary, "cron", hour=17, minute=1, timezone='America/Argentina/Buenos_Aires', id="daily_summary_job")
    
    # Job de reseteo de flags (00:01 hs)
    scheduler.add_job(reset_flags, "cron", hour=0, minute=1, timezone='America/Argentina/Buenos_Aires', id="reset_flags_job")
    
    # 3. Arranque
    scheduler.start()
    print("✅ Scheduler iniciado")
    
    # Primer chequeo inmediato para cargar datos
    check_and_save_dolar() 

def stop_scheduler():
    """Detiene el scheduler."""
    scheduler.shutdown()

if __name__ == '__main__':
    # Esto permite ejecutar el scheduler directamente si es necesario
    start_scheduler()
    
    # Para mantener el script vivo si lo ejecutas en main:
    try:
        import time
        while True:
            time.sleep(2)
    except (KeyboardInterrupt, SystemExit):
        stop_scheduler()