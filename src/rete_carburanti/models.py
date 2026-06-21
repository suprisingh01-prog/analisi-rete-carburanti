from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class StazioneFortech:
    # Identificazione
    nome: str
    nome_impianto: str
    periodo: str
    
    # Prodotti — litri
    verde_litri: float
    diesel_litri: float
    diesel_plus_litri: float
    
    # Prodotti — euro
    verde_euro: float
    diesel_euro: float
    diesel_plus_euro: float
    
    # Totali
    totale_litri: float
    totale_euro: float
    
    # Prezzi medi calcolati
    prezzo_medio_verde: float
    prezzo_medio_diesel: float
    
    # Mix percentuali
    pct_verde: float
    pct_diesel: float
    
    # Pagamenti raggruppati (litri)
    litri_flotte: float
    litri_cash_bancomat: float
    litri_carta_credito: float
    litri_satispay: float
    litri_altro: float
    pct_flotte: float
    
    # Dettaglio pagamenti grezzo
    pagamenti_dettaglio: dict = field(default_factory=dict)
    
    # Metadati
    data_elaborazione: datetime = field(default_factory=datetime.now)
    file_sorgente: str = ""
    # =============================================
    # PROPERTY — attributi calcolati
    # =============================================

    @property
    def fatturato_per_litro(self) -> float:
        """Prezzo medio di vendita su tutti i prodotti."""
        if self.totale_litri > 0:
            return round(self.totale_euro / self.totale_litri, 4)
        return 0.0

    @property
    def is_diesel_heavy(self) -> bool:
        """True se il diesel supera il 60% dei litri totali."""
        return self.pct_diesel > 60.0

    @property
    def margine_stimato_euro(self) -> float:
        """
        Stima del margine lordo.
        Assunzione: margine medio industria ~3 centesimi/litro.
        Da aggiornare con dati reali di acquisto.
        """
        MARGINE_MEDIO = 0.03
        return round(self.totale_litri * MARGINE_MEDIO, 2)

    @property
    def quota_flotte_categoria(self) -> str:
        """Classifica la stazione per dipendenza dalle flotte."""
        if self.pct_flotte >= 25:
            return "Alta dipendenza flotte"
        elif self.pct_flotte >= 10:
            return "Media dipendenza flotte"
        else:
            return "Bassa dipendenza flotte"

    def __str__(self) -> str:
        return (
            f"{self.nome} | "
            f"{self.totale_litri:,.0f} L | "
            f"€{self.totale_euro:,.0f} | "
            f"Verde {self.pct_verde:.1f}% | "
            f"Diesel {self.pct_diesel:.1f}%"
        )