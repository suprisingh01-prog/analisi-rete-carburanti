"""
DatabaseManager — gestisce lo storage storico su SQLite.
"""

import sqlite3
import os
from datetime import datetime
from typing import List, Optional
from .models import StazioneFortech


class DatabaseManager:
    """
    Gestisce il database SQLite del progetto.

    Uso:
        db = DatabaseManager("data/database.db")
        db.salva_elaborazione([stazione1, stazione2])
        storico = db.storico_stazione("imola_25_26")
    """

    def __init__(self, percorso_db: str = "data/database.db"):
        self.percorso_db = percorso_db
        os.makedirs(os.path.dirname(percorso_db), exist_ok=True)
        self._inizializza_db()

    def _inizializza_db(self) -> None:
        """Crea le tabelle se non esistono ancora."""
        with sqlite3.connect(self.percorso_db) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS elaborazioni (
                    id                INTEGER PRIMARY KEY AUTOINCREMENT,
                    data_elaborazione TEXT NOT NULL,
                    n_stazioni        INTEGER,
                    totale_litri_rete REAL,
                    totale_euro_rete  REAL,
                    note              TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS stazioni (
                    id               INTEGER PRIMARY KEY AUTOINCREMENT,
                    elaborazione_id  INTEGER NOT NULL,
                    nome             TEXT NOT NULL,
                    nome_impianto    TEXT,
                    verde_litri      REAL,
                    diesel_litri     REAL,
                    diesel_plus_litri REAL,
                    totale_litri     REAL,
                    verde_euro       REAL,
                    diesel_euro      REAL,
                    totale_euro      REAL,
                    pct_verde        REAL,
                    pct_diesel       REAL,
                    pct_flotte       REAL,
                    litri_flotte     REAL,
                    litri_carta      REAL,
                    litri_cash       REAL,
                    prezzo_medio_verde  REAL,
                    prezzo_medio_diesel REAL,
                    margine_stimato  REAL,
                    FOREIGN KEY (elaborazione_id) REFERENCES elaborazioni(id)
                )
            """)
            conn.commit()
            
    def salva_elaborazione(self, stazioni: List[StazioneFortech]) -> int:
        """
        Salva una nuova elaborazione nel database.
        Restituisce l'id dell'elaborazione creata.
        """
        totale_litri = sum(s.totale_litri for s in stazioni)
        totale_euro  = sum(s.totale_euro  for s in stazioni)

        with sqlite3.connect(self.percorso_db) as conn:
            # 1. Inserisci la riga in elaborazioni
            cursor = conn.execute("""
                INSERT INTO elaborazioni
                    (data_elaborazione, n_stazioni, totale_litri_rete, totale_euro_rete)
                VALUES (?, ?, ?, ?)
            """, (datetime.now().isoformat(), len(stazioni), totale_litri, totale_euro))

            elaborazione_id = cursor.lastrowid   # id appena creato

            # 2. Inserisci una riga per ogni stazione
            for s in stazioni:
                conn.execute("""
                    INSERT INTO stazioni (
                        elaborazione_id, nome, nome_impianto,
                        verde_litri, diesel_litri, diesel_plus_litri,
                        totale_litri, verde_euro, diesel_euro, totale_euro,
                        pct_verde, pct_diesel, pct_flotte,
                        litri_flotte, litri_carta, litri_cash,
                        prezzo_medio_verde, prezzo_medio_diesel, margine_stimato
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    elaborazione_id, s.nome, s.nome_impianto,
                    s.verde_litri, s.diesel_litri, s.diesel_plus_litri,
                    s.totale_litri, s.verde_euro, s.diesel_euro, s.totale_euro,
                    s.pct_verde, s.pct_diesel, s.pct_flotte,
                    s.litri_flotte, s.litri_carta_credito, s.litri_cash_bancomat,
                    s.prezzo_medio_verde, s.prezzo_medio_diesel, s.margine_stimato_euro
                ))

            conn.commit()

        print(f"Elaborazione #{elaborazione_id} salvata — {len(stazioni)} stazioni")
        return elaborazione_id
    
    def storico_stazione(self, nome: str) -> list:
        """Restituisce lo storico di una stazione specifica."""
        with sqlite3.connect(self.percorso_db) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT
                    e.data_elaborazione,
                    s.totale_litri,
                    s.totale_euro,
                    s.pct_verde,
                    s.pct_diesel,
                    s.pct_flotte,
                    s.margine_stimato
                FROM stazioni s
                JOIN elaborazioni e ON s.elaborazione_id = e.id
                WHERE s.nome = ?
                ORDER BY e.data_elaborazione ASC
            """, (nome,))
            return [dict(row) for row in cursor.fetchall()]

    def storico_rete(self) -> list:
        """Restituisce lo storico aggregato di tutta la rete."""
        with sqlite3.connect(self.percorso_db) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT
                    data_elaborazione,
                    n_stazioni,
                    totale_litri_rete,
                    totale_euro_rete
                FROM elaborazioni
                ORDER BY data_elaborazione ASC
            """)
            return [dict(row) for row in cursor.fetchall()]

    def lista_elaborazioni(self) -> list:
        """Restituisce la lista di tutte le elaborazioni salvate."""
        with sqlite3.connect(self.percorso_db) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT id, data_elaborazione, n_stazioni,
                    totale_litri_rete, totale_euro_rete
                FROM elaborazioni
                ORDER BY data_elaborazione DESC
            """)
            return [dict(row) for row in cursor.fetchall()]
        

    def storico_stazione_per_elaborazione(self, elaborazione_id: int) -> list:
        """Restituisce tutte le stazioni di una specifica elaborazione."""
        with sqlite3.connect(self.percorso_db) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT nome, totale_litri, totale_euro,
                       pct_verde, pct_diesel, pct_flotte,
                       margine_stimato
                FROM stazioni
                WHERE elaborazione_id = ?
            """, (elaborazione_id,))
            return [dict(row) for row in cursor.fetchall()]