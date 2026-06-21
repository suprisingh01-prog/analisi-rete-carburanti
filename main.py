"""
Analisi Rete Carburanti
Entry point principale del progetto.
"""

if __name__ == "__main__":
    print("Sistema analisi rete carburanti — avvio...")



"""
Analisi Rete Carburanti — Entry point principale.

Uso:
    python3 main.py

Cosa fa:
    1. Legge tutti i file XLS da data/raw/
    2. Parsa ogni stazione con FortechParser
    3. Salva nel database SQLite
    4. Calcola KPI e genera report (CSV, HTML, PDF)
    5. Rileva anomalie
    6. Manda email alert se ci sono anomalie
"""

import os
import glob
import sys

from src.rete_carburanti.config import Config
from src.rete_carburanti.logger import get_logger
from src.rete_carburanti.parser import FortechParser
from src.rete_carburanti.analyzer import ReteAnalyzer
from src.rete_carburanti.database import DatabaseManager
from src.rete_carburanti.anomaly import AnomalyDetector
from src.rete_carburanti.report import ReportGenerator
from src.rete_carburanti.notifier import EmailNotifier

logger = get_logger(__name__)


def leggi_stazioni() -> list:
    """
    Legge tutti i file XLS da data/raw/ e li parsa.
    Restituisce lista di StazioneFortech.
    """
    pattern = os.path.join(Config.DATA_RAW_DIR, "*.xls")
    files   = sorted(glob.glob(pattern))

    if not files:
        logger.error(f"Nessun file XLS trovato in {Config.DATA_RAW_DIR}")
        sys.exit(1)

    logger.info(f"Trovati {len(files)} file XLS")

    stazioni = []
    errori   = []

    for path in files:
        nome = os.path.basename(path)
        try:
            stazione = FortechParser(path).parse()
            stazioni.append(stazione)
            logger.info(f"  ✅ {nome} — {stazione.totale_litri:,.0f} L")
        except Exception as e:
            logger.error(f"  ❌ {nome} — {e}")
            errori.append(nome)

    if errori:
        logger.warning(f"{len(errori)} file saltati per errori")

    if not stazioni:
        logger.error("Nessuna stazione parsata correttamente — uscita")
        sys.exit(1)

    return stazioni


def main():
    logger.info("=" * 55)
    logger.info("  ANALISI RETE CARBURANTI — AVVIO")
    logger.info("=" * 55)

    # ── 1. Leggi e parsa tutti i file XLS ──────────────────
    logger.info("STEP 1 — Parsing file Fortech")
    stazioni = leggi_stazioni()
    logger.info(f"Stazioni caricate: {len(stazioni)}")

    # ── 2. Salva nel database ───────────────────────────────
    logger.info("STEP 2 — Salvataggio nel database")
    db          = DatabaseManager(Config.DB_PATH)
    id_elab     = db.salva_elaborazione(stazioni)
    logger.info(f"Elaborazione #{id_elab} salvata")

    # ── 3. Calcola KPI e genera report ─────────────────────
    logger.info("STEP 3 — Calcolo KPI e generazione report")
    analyzer = ReteAnalyzer(stazioni)
    kpi      = analyzer.kpi_rete()

    logger.info(f"  Totale litri rete: {kpi['totale_litri']:,.0f}")
    logger.info(f"  Fatturato rete:    €{kpi['totale_euro']:,.0f}")
    logger.info(f"  Stazione top:      {kpi['stazione_top']}")
    logger.info(f"  Mix diesel:        {kpi['pct_diesel_rete']:.1f}%")
    logger.info(f"  % Flotte:          {kpi['pct_flotte_rete']:.1f}%")

    gen = ReportGenerator(analyzer, output_dir=Config.OUTPUT_DIR)
    path_csv  = gen.genera_csv()
    path_html = gen.genera_html()
    path_pdf  = gen.genera_pdf()

    logger.info(f"  CSV:  {path_csv}")
    logger.info(f"  HTML: {path_html}")
    logger.info(f"  PDF:  {path_pdf}")

    # ── 4. Anomaly detection ────────────────────────────────
    logger.info("STEP 4 — Anomaly detection")
    detector = AnomalyDetector(db)
    report   = detector.analizza()
    logger.info(f"  {report['summary']}")

    if report['anomalie_mom']:
        logger.warning("  Anomalie MoM:")
        for a in report['anomalie_mom']:
            logger.warning(
                f"    {a['nome']}: {a['var_pct']:+.1f}% {a['tipo']}"
            )

    if report['anomalie_zscore']:
        logger.warning("  Anomalie z-score:")
        for a in report['anomalie_zscore']:
            logger.warning(
                f"    {a['nome']}: zscore={a['zscore']:+.2f} {a['tipo']}"
            )

    # ── 5. Email alert ──────────────────────────────────────
    logger.info("STEP 5 — Email alert")
    notifier = EmailNotifier()
    inviata  = notifier.invia_alert(report)
    if inviata:
        logger.info("  Alert email inviata")
    else:
        logger.info("  Nessun alert necessario")

    # ── Fine ────────────────────────────────────────────────
    logger.info("=" * 55)
    logger.info("  ANALISI COMPLETATA")
    logger.info("=" * 55)


if __name__ == "__main__":
    main()
