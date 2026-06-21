"""
ReteAnalyzer — aggrega i dati di più stazioni e calcola KPI di rete.
"""

from typing import List
import pandas as pd
import numpy as np
from .models import StazioneFortech


class ReteAnalyzer:
    """
    Aggrega i dati di una lista di StazioneFortech e produce KPI di rete.

    Uso:
        analyzer = ReteAnalyzer([stazione1, stazione2, ...])
        kpi = analyzer.kpi_rete()
        ranking = analyzer.ranking()
    """

    def __init__(self, stazioni: List[StazioneFortech]):
        self.stazioni = stazioni
        self._df = self._build_dataframe()

    def _build_dataframe(self) -> pd.DataFrame:
        """Costruisce un DataFrame da lista di StazioneFortech."""
        righe = []
        for s in self.stazioni:
            righe.append({
                'nome':                s.nome,
                'nome_impianto':       s.nome_impianto,
                'verde_litri':         s.verde_litri,
                'diesel_litri':        s.diesel_litri,
                'diesel_plus_litri':   s.diesel_plus_litri,
                'totale_litri':        s.totale_litri,
                'verde_euro':          s.verde_euro,
                'diesel_euro':         s.diesel_euro,
                'totale_euro':         s.totale_euro,
                'prezzo_medio_verde':  s.prezzo_medio_verde,
                'prezzo_medio_diesel': s.prezzo_medio_diesel,
                'pct_verde':           s.pct_verde,
                'pct_diesel':          s.pct_diesel,
                'litri_flotte':        s.litri_flotte,
                'litri_carta_credito': s.litri_carta_credito,
                'litri_cash_bancomat': s.litri_cash_bancomat,
                'pct_flotte':          s.pct_flotte,
                'margine_stimato':     s.margine_stimato_euro,
            })
        return pd.DataFrame(righe)

    # =============================================
    # KPI DI RETE
    # =============================================

    def kpi_rete(self) -> dict:
        """Restituisce i KPI principali dell'intera rete."""
        df = self._df
        return {
            'n_stazioni':           len(self.stazioni),
            'totale_litri':         df['totale_litri'].sum(),
            'totale_euro':          df['totale_euro'].sum(),
            'media_litri_stazione': df['totale_litri'].mean(),
            'std_litri_stazione':   df['totale_litri'].std(),
            'pct_verde_rete':       round(df['verde_litri'].sum() / df['totale_litri'].sum() * 100, 1),
            'pct_diesel_rete':      round(df['diesel_litri'].sum() / df['totale_litri'].sum() * 100, 1),
            'pct_flotte_rete':      round(df['litri_flotte'].sum() / df['totale_litri'].sum() * 100, 1),
            'margine_stimato_rete': df['margine_stimato'].sum(),
            'stazione_top':         df.loc[df['totale_litri'].idxmax(), 'nome'],
            'stazione_bottom':      df.loc[df['totale_litri'].idxmin(), 'nome'],
        }

    def ranking(self) -> pd.DataFrame:
        """Restituisce le stazioni ordinate per litri totali."""
        df = self._df[['nome', 'totale_litri', 'totale_euro',
                        'pct_verde', 'pct_diesel', 'pct_flotte',
                        'margine_stimato']].copy()
        df['quota_rete_pct'] = round(
            df['totale_litri'] / df['totale_litri'].sum() * 100, 1
        )
        return df.sort_values('totale_litri', ascending=False).reset_index(drop=True)

    def anomalie(self, soglia_zscore: float = 1.5) -> pd.DataFrame:
        """
        Rileva stazioni anomale usando lo z-score sui litri totali.
        Una stazione è anomala se il suo z-score è > soglia o < -soglia.
        """
        df = self._df.copy()
        media = df['totale_litri'].mean()
        std   = df['totale_litri'].std()

        if std == 0:
            df['zscore'] = 0.0
        else:
            df['zscore'] = (df['totale_litri'] - media) / std

        anomale = df[abs(df['zscore']) > soglia_zscore][
            ['nome', 'totale_litri', 'zscore']
        ].copy()
        anomale['tipo'] = anomale['zscore'].apply(
            lambda z: '🔺 Sopra media' if z > 0 else '🔻 Sotto media'
        )
        return anomale.reset_index(drop=True)

    def dataframe(self) -> pd.DataFrame:
        """Restituisce il DataFrame completo."""
        return self._df.copy()