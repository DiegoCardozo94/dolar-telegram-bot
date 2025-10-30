# storage/csv_history.py

import os
import pandas as pd
from config.constants import HISTORY_CSV_FILE
from utils.file_helpers import ensure_dirs, log_error

def append_to_csv(csv_rows):
    """
    Agrega filas de cotizaciones al archivo CSV histórico usando pandas.
    """
    ensure_dirs(HISTORY_CSV_FILE)
    file_exists = os.path.isfile(HISTORY_CSV_FILE)
    
    if csv_rows:
        try:
            df = pd.DataFrame(csv_rows)
            df.to_csv(HISTORY_CSV_FILE, mode='a', header=not file_exists, index=False)
        except Exception as e:
            log_error(f"Error escribiendo en CSV histórico: {e}")