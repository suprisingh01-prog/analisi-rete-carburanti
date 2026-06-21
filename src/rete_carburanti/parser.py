"""
FortechParser — legge un file XLS Fortech e produce un StazioneFortech.
"""

import os
import xml.etree.ElementTree as ET
from .models import StazioneFortech

NS = {'ss': 'urn:schemas-microsoft-com:office:spreadsheet'}


class FortechParser:
    """
    Parsea un singolo file XLS esportato da Fortech.
    Uso:
        parser = FortechParser("data/raw/imola_25_26.xls")
        stazione = parser.parse()
    """

    def __init__(self, percorso_file: str):
        self.percorso_file = percorso_file
        self.nome = os.path.basename(percorso_file).replace('.xls', '')
        self._rows = []   # righe del foglio, popolate da _leggi_file()

    def parse(self) -> StazioneFortech:
        """Metodo pubblico principale — restituisce un StazioneFortech."""
        self._leggi_file()
        intestazione = self._estrai_intestazione()
        prodotti     = self._estrai_prodotti()
        pagamenti    = self._estrai_pagamenti()
        return self._costruisci_stazione(intestazione, prodotti, pagamenti)

    # =============================================
    # METODI PRIVATI
    # =============================================
    @staticmethod
    def _get_vals(row) -> list:
        """Estrae i valori testuali dalle celle di una riga XML."""
        cells = row.findall('ss:Cell', NS)
        return [
            c.find('ss:Data', NS).text if c.find('ss:Data', NS) is not None else ''
            for c in cells
        ]

    def _leggi_file(self) -> None:
        """Carica il file XLS e popola self._rows."""
        tree = ET.parse(self.percorso_file)
        root = tree.getroot()
        sheets = root.findall('.//ss:Worksheet', NS)
        if not sheets:
            raise ValueError(f"Nessun foglio trovato in {self.percorso_file}")
        first_sheet = sheets[0]
        self._rows = first_sheet.findall('.//ss:Row', NS)

    def _estrai_intestazione(self) -> dict:
        """Estrae nome impianto e periodo dalle prime righe."""
        nome_impianto = self.nome
        periodo = ''
        for row in self._rows[:6]:
            vals = self._get_vals(row)
            if not vals or not vals[0]:
                continue
            v = vals[0]
            if 'Periodo' in v or 'periodo' in v:
                periodo = v
            elif any(x in v.upper() for x in
                     ['VIALE', 'VIA', 'CORSO', 'PIAZZA', 'SS ', 'SP ', 'SR ']):
                nome_impianto = v
        return {'nome_impianto': nome_impianto, 'periodo': periodo}

    def _estrai_prodotti(self) -> dict:
        """Estrae litri ed euro per Verde, Diesel, Diesel+."""
        prodotti = {'Verde': 0.0, 'Diesel': 0.0, 'Diesel+': 0.0}
        importi  = {'Verde': 0.0, 'Diesel': 0.0, 'Diesel+': 0.0}

        for row in self._rows:
            vals = self._get_vals(row)
            if not vals or vals[0] not in ['Verde', 'Diesel', 'Diesel+']:
                continue
            if len(vals) > 1 and self._is_float(vals[1]):
                prodotto = vals[0]
                numeri = [float(x) for x in vals[1:] if self._is_float(x) and float(x) > 1]
                grandi = [x for x in numeri if x > 100]
                if len(grandi) >= 2:
                    prodotti[prodotto] = grandi[0]
                    importi[prodotto]  = grandi[-1]

        return {'volumi': prodotti, 'importi': importi}

    def _estrai_pagamenti(self) -> dict:
        """Estrae il mix pagamenti in litri."""
        pagamenti = {}
        in_pag = False

        for row in self._rows:
            vals = self._get_vals(row)
            if not vals or not vals[0]:
                continue
            if 'tipo pagamento' in vals[0].lower():
                in_pag = True
                continue
            if in_pag:
                if vals[0] == 'Totale':
                    break
                tipo = vals[0].strip().title()
                for val in vals[1:]:
                    if self._is_float(val) and float(val) > 1:
                        pagamenti[tipo] = round(pagamenti.get(tipo, 0) + float(val), 2)
                        break

        return pagamenti

    def _costruisci_stazione(self,
                              intestazione: dict,
                              prodotti: dict,
                              pagamenti: dict) -> StazioneFortech:
        """Assembla e restituisce il StazioneFortech finale."""
        vol = prodotti['volumi']
        imp = prodotti['importi']

        totale_litri = sum(vol.values())
        totale_euro  = sum(imp.values())

        # Raggruppa pagamenti in categorie
        flotte = ['Dkv', 'Esso', 'Essomb', 'Uta', 'Ar Card', 'Q8 Card']
        cash   = ['Contanti', 'Pagobancomat', 'Codiceresto']

        litri_flotte  = sum(v for k, v in pagamenti.items() if k in flotte)
        litri_cash    = sum(v for k, v in pagamenti.items() if k in cash)
        litri_carta   = pagamenti.get('Carta Di Credito', 0)
        litri_satispay= pagamenti.get('Satispay', 0)
        litri_altro   = sum(v for k, v in pagamenti.items()
                           if k not in flotte + cash + ['Carta Di Credito',
                                                         'Satispay',
                                                         'Prova Erogazione'])

        def pct(parte, totale):
            return round(parte / totale * 100, 1) if totale > 0 else 0.0

        def prezzo_medio(importo, volume):
            return round(importo / volume, 4) if volume > 0 else 0.0

        return StazioneFortech(
            nome             = self.nome,
            nome_impianto    = intestazione['nome_impianto'],
            periodo          = intestazione['periodo'],
            verde_litri      = round(vol['Verde'], 2),
            diesel_litri     = round(vol['Diesel'], 2),
            diesel_plus_litri= round(vol['Diesel+'], 2),
            verde_euro       = round(imp['Verde'], 2),
            diesel_euro      = round(imp['Diesel'], 2),
            diesel_plus_euro = round(imp['Diesel+'], 2),
            totale_litri     = round(totale_litri, 2),
            totale_euro      = round(totale_euro, 2),
            prezzo_medio_verde  = prezzo_medio(imp['Verde'], vol['Verde']),
            prezzo_medio_diesel = prezzo_medio(imp['Diesel'], vol['Diesel']),
            pct_verde        = pct(vol['Verde'], totale_litri),
            pct_diesel       = pct(vol['Diesel'], totale_litri),
            litri_flotte         = round(litri_flotte, 2),
            litri_cash_bancomat  = round(litri_cash, 2),
            litri_carta_credito  = round(litri_carta, 2),
            litri_satispay       = round(litri_satispay, 2),
            litri_altro          = round(litri_altro, 2),
            pct_flotte           = pct(litri_flotte, totale_litri),
            pagamenti_dettaglio  = pagamenti,
            file_sorgente        = self.percorso_file,
        )

    @staticmethod
    def _is_float(s) -> bool:
        """Verifica se una stringa è convertibile a float."""
        try:
            float(s)
            return True
        except (TypeError, ValueError):
            return False