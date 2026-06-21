"""
logger.py — logger centralizzato per tutto il progetto.
"""

import logging
import os
from datetime import datetime

os.makedirs("logs", exist_ok=True)


def get_logger(nome: str) -> logging.Logger:
    """
    Restituisce un logger configurato con output su console e su file.

    Uso:
        from .logger import get_logger
        logger = get_logger(__name__)
        logger.info("Messaggio informativo")
        logger.warning("Attenzione")
        logger.error("Errore grave")
    """
    logger = logging.getLogger(nome)

    if logger.handlers:
        return logger   # evita di aggiungere handler duplicati

    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        fmt='%(asctime)s %(levelname)-8s %(name)s — %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Handler console — mostra INFO e sopra
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(formatter)

    # Handler file — salva tutto (DEBUG e sopra)
    log_file = os.path.join("logs", f"rete_{datetime.now().strftime('%Y%m%d')}.log")
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    logger.addHandler(console)
    logger.addHandler(file_handler)

    return logger