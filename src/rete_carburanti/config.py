"""
config.py — carica la configurazione dal file .env
"""

import os
from dotenv import load_dotenv

# Carica il file .env
load_dotenv()


class Config:
    """Configurazione centralizzata del progetto."""

    # Database
    DB_PATH: str = os.getenv("DB_PATH", "data/database.db")

    # Anomaly detection
    SOGLIA_MOM_PCT: float = float(os.getenv("SOGLIA_MOM_PCT", "-10.0"))
    SOGLIA_ZSCORE: float  = float(os.getenv("SOGLIA_ZSCORE", "1.5"))

    # Output
    OUTPUT_DIR: str    = os.getenv("OUTPUT_DIR", "output")
    DATA_RAW_DIR: str  = os.getenv("DATA_RAW_DIR", "data/raw")