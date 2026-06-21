"""
AnomalyDetector — rileva anomalie confrontando dati storici dal database.
"""

import pandas as pd
import numpy as np
from typing import List, Optional
from .database import DatabaseManager


class AnomalyDetector:
    """
    Rileva anomalie sui dati storici delle stazioni.

    Uso:
        detector = AnomalyDetector(db)
        report = detector.analizza()
    """

    # Soglie di allerta
    SOGLIA_MOM_PCT = -10.0   # calo MoM superiore al 10% = anomalia
    SOGLIA_ZSCORE  = 1.5     # z-score fuori da ±1.5 = anomalia

    def __init__(self, db: DatabaseManager):
        self.db = db

    def analizza(self) -> dict:
        """
        Esegue l'analisi completa e restituisce un dizionario con le anomalie.
        """
        df = self._build_dataframe()

        if df is None or df.empty:
            return {'errore': 'Nessun dato storico disponibile nel database.'}

        n_elaborazioni = df['elaborazione_id'].nunique()

        risultato = {
            'n_elaborazioni_analizzate': n_elaborazioni,
            'anomalie_mom':    [],
            'anomalie_zscore': [],
            'summary':         '',
        }

        # MoM solo se abbiamo almeno 2 elaborazioni
        if n_elaborazioni >= 2:
            anomalie_mom = self._anomalie_mom(df)
            risultato['anomalie_mom'] = anomalie_mom.to_dict('records')

        # Z-score sempre
        anomalie_z = self._anomalie_zscore(df)
        risultato['anomalie_zscore'] = anomalie_z.to_dict('records')

        # Summary testuale
        n_mom = len(risultato['anomalie_mom'])
        n_z   = len(risultato['anomalie_zscore'])
        if n_mom == 0 and n_z == 0:
            risultato['summary'] = '✅ Nessuna anomalia rilevata.'
        else:
            risultato['summary'] = (
                f"⚠️ Trovate {n_mom} anomalie MoM e {n_z} anomalie z-score."
            )

        return risultato

    def _build_dataframe(self) -> Optional[pd.DataFrame]:
        """
        Costruisce un DataFrame con tutto lo storico delle stazioni dal DB.
        Ogni riga = una stazione in una elaborazione.
        """
        elaborazioni = self.db.lista_elaborazioni()
        if not elaborazioni:
            return None

        righe = []
        for elab in elaborazioni:
            storico = self.db.storico_stazione_per_elaborazione(elab['id'])
            for s in storico:
                s['elaborazione_id']  = elab['id']
                s['data_elaborazione'] = elab['data_elaborazione']
                righe.append(s)

        if not righe:
            return None

        df = pd.DataFrame(righe)
        df['data_elaborazione'] = pd.to_datetime(df['data_elaborazione'])
        df = df.sort_values(['nome', 'data_elaborazione']).reset_index(drop=True)
        return df

    def _anomalie_mom(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Rileva cali MoM (Month over Month) superiori alla soglia.
        Confronta ogni stazione nell'ultima elaborazione con la penultima.
        """
        # Prendi le ultime due elaborazioni
        elab_ids = sorted(df['elaborazione_id'].unique())
        if len(elab_ids) < 2:
            return pd.DataFrame()

        id_attuale    = elab_ids[-1]
        id_precedente = elab_ids[-2]

        attuale    = df[df['elaborazione_id'] == id_attuale][['nome', 'totale_litri']].copy()
        precedente = df[df['elaborazione_id'] == id_precedente][['nome', 'totale_litri']].copy()

        # Merge per confrontare
        confronto = attuale.merge(precedente, on='nome', suffixes=('_att', '_prec'))
        confronto['var_pct'] = (
            (confronto['totale_litri_att'] - confronto['totale_litri_prec'])
            / confronto['totale_litri_prec'] * 100
        ).round(2)

        # Filtra solo le anomalie
        anomalie = confronto[confronto['var_pct'] <= self.SOGLIA_MOM_PCT].copy()
        anomalie['tipo'] = '🔻 Calo MoM'
        anomalie = anomalie.rename(columns={
            'totale_litri_att':  'litri_attuale',
            'totale_litri_prec': 'litri_precedente',
        })
        return anomalie[['nome', 'litri_attuale', 'litri_precedente',
                          'var_pct', 'tipo']].reset_index(drop=True)

    def _anomalie_zscore(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Rileva stazioni con z-score anomalo nell'ultima elaborazione.
        Z-score misura quanto un valore si discosta dalla media storica.
        """
        # Prendi solo l'ultima elaborazione
        id_ultimo = df['elaborazione_id'].max()
        ultima    = df[df['elaborazione_id'] == id_ultimo].copy()

        media = ultima['totale_litri'].mean()
        std   = ultima['totale_litri'].std()

        if std == 0:
            return pd.DataFrame()

        ultima['zscore'] = ((ultima['totale_litri'] - media) / std).round(3)
        anomalie = ultima[abs(ultima['zscore']) > self.SOGLIA_ZSCORE].copy()
        anomalie['tipo'] = anomalie['zscore'].apply(
            lambda z: '🔺 Sopra media' if z > 0 else '🔻 Sotto media'
        )
        return anomalie[['nome', 'totale_litri', 'zscore',
                          'tipo']].reset_index(drop=True)