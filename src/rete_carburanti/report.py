"""
ReportGenerator — genera CSV, HTML e PDF dai dati del ReteAnalyzer.
"""

import os
from datetime import datetime
from typing import Optional
import matplotlib
matplotlib.use('Agg')   # backend non interattivo — salva file senza aprire finestre
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import io
import base64

from .analyzer import ReteAnalyzer


class ReportGenerator:
    """
    Genera report in vari formati dai dati di un ReteAnalyzer.

    Uso:
        gen = ReportGenerator(analyzer, output_dir="output")
        gen.genera_csv()
        gen.genera_html()
        gen.genera_pdf()
    """

    def __init__(self, analyzer: ReteAnalyzer, output_dir: str = "output"):
        self.analyzer = analyzer
        self.output_dir = output_dir
        self.kpi = analyzer.kpi_rete()
        self.ranking = analyzer.ranking()
        self.anomalie = analyzer.anomalie()
        os.makedirs(output_dir, exist_ok=True)
        self._timestamp = datetime.now().strftime("%Y%m%d_%H%M")

    # =============================================
    # CSV
    # =============================================

    def genera_csv(self) -> str:
        """Genera un CSV con il ranking completo delle stazioni."""
        path = os.path.join(self.output_dir, f"ranking_{self._timestamp}.csv")
        self.ranking.to_csv(path, index=False, encoding='utf-8')
        print(f"CSV generato: {path}")
        return path

    # =============================================
    # HTML
    # =============================================

    def genera_html(self) -> str:
        """Genera una dashboard HTML con grafici embedded."""
        grafici = self._genera_grafici_base64()
        html = self._template_html(grafici)
        path = os.path.join(self.output_dir, f"dashboard_{self._timestamp}.html")
        with open(path, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"HTML generato: {path}")
        return path

    def _genera_grafici_base64(self) -> dict:
        """Genera i grafici Matplotlib e li converte in base64 per l'HTML."""
        grafici = {}

        # --- Grafico 1: Bar chart ranking litri ---
        fig, ax = plt.subplots(figsize=(10, 4))
        nomi    = self.ranking['nome'].tolist()
        litri   = self.ranking['totale_litri'].tolist()
        colori  = ['#185FA5' if i == 0 else '#5B9BD5' for i in range(len(nomi))]
        ax.barh(nomi, litri, color=colori)
        ax.set_title('Litri totali per stazione', fontsize=14, pad=10)
        ax.set_xlabel('Litri')
        ax.invert_yaxis()
        for i, v in enumerate(litri):
            ax.text(v * 0.01, i, f'{v:,.0f}', va='center', fontsize=9)
        plt.tight_layout()
        grafici['ranking'] = self._fig_to_base64(fig)
        plt.close(fig)

        # --- Grafico 2: Pie chart mix prodotto rete ---
        fig, ax = plt.subplots(figsize=(5, 4))
        valori  = [self.kpi['pct_verde_rete'],
                   self.kpi['pct_diesel_rete'],
                   100 - self.kpi['pct_verde_rete'] - self.kpi['pct_diesel_rete']]
        labels  = ['Verde', 'Diesel', 'Diesel+']
        colori  = ['#185FA5', '#0F6E56', '#BA7517']
        ax.pie(valori, labels=labels, colors=colori,
               autopct='%.1f%%', startangle=90)
        ax.set_title('Mix prodotto rete', fontsize=14)
        grafici['mix_prodotto'] = self._fig_to_base64(fig)
        plt.close(fig)

        return grafici

    @staticmethod
    def _fig_to_base64(fig) -> str:
        """Converte una figura Matplotlib in stringa base64 per HTML."""
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=120, bbox_inches='tight')
        buf.seek(0)
        return base64.b64encode(buf.read()).decode('utf-8')

    def _template_html(self, grafici: dict) -> str:
        """Genera il template HTML completo."""
        now = datetime.now().strftime('%d/%m/%Y %H:%M')
        n   = self.kpi['n_stazioni']

        # Righe tabella ranking
        righe = ''
        for _, row in self.ranking.iterrows():
            righe += f"""
            <tr>
                <td>{row['nome']}</td>
                <td>{row['totale_litri']:,.0f}</td>
                <td>€{row['totale_euro']:,.0f}</td>
                <td>{row['pct_verde']:.1f}%</td>
                <td>{row['pct_diesel']:.1f}%</td>
                <td>{row['pct_flotte']:.1f}%</td>
                <td>{row['quota_rete_pct']:.1f}%</td>
                <td>€{row['margine_stimato']:,.0f}</td>
            </tr>"""

        return f"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<title>Dashboard Rete Carburanti</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif;
         background:#f5f5f3; color:#2c2c2a; margin:0; padding:2rem; }}
  h1   {{ font-size:24px; color:#185FA5; border-bottom:2px solid #185FA5;
         padding-bottom:.5rem; }}
  .subtitle {{ color:#888; font-size:13px; margin-bottom:2rem; }}
  .kpi-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr));
               gap:12px; margin-bottom:2rem; }}
  .kpi {{ background:#fff; border-radius:8px; padding:1rem;
          border:.5px solid rgba(0,0,0,.1); }}
  .kpi-label {{ font-size:12px; color:#888; }}
  .kpi-value {{ font-size:22px; font-weight:500; }}
  .charts {{ display:grid; grid-template-columns:2fr 1fr; gap:16px;
             margin-bottom:2rem; }}
  .chart-card {{ background:#fff; border-radius:8px; padding:1rem;
                 border:.5px solid rgba(0,0,0,.1); text-align:center; }}
  table {{ width:100%; border-collapse:collapse; background:#fff;
           border-radius:8px; overflow:hidden; }}
  th {{ background:#185FA5; color:#fff; padding:10px 12px;
        font-size:13px; text-align:left; }}
  td {{ padding:8px 12px; font-size:13px; border-bottom:.5px solid #eee; }}
  tr:hover td {{ background:#f0f5ff; }}
</style>
</head>
<body>
<h1>Dashboard Rete Distributori</h1>
<p class="subtitle">Generato il {now} — {n} stazioni analizzate</p>

<div class="kpi-grid">
  <div class="kpi">
    <div class="kpi-label">Totale litri rete</div>
    <div class="kpi-value">{self.kpi['totale_litri']:,.0f}</div>
  </div>
  <div class="kpi">
    <div class="kpi-label">Fatturato rete</div>
    <div class="kpi-value">€{self.kpi['totale_euro']:,.0f}</div>
  </div>
  <div class="kpi">
    <div class="kpi-label">Margine stimato</div>
    <div class="kpi-value">€{self.kpi['margine_stimato_rete']:,.0f}</div>
  </div>
  <div class="kpi">
    <div class="kpi-label">Stazione top</div>
    <div class="kpi-value">{self.kpi['stazione_top']}</div>
  </div>
  <div class="kpi">
    <div class="kpi-label">% Diesel rete</div>
    <div class="kpi-value">{self.kpi['pct_diesel_rete']:.1f}%</div>
  </div>
  <div class="kpi">
    <div class="kpi-label">% Flotte rete</div>
    <div class="kpi-value">{self.kpi['pct_flotte_rete']:.1f}%</div>
  </div>
</div>

<div class="charts">
  <div class="chart-card">
    <img src="data:image/png;base64,{grafici['ranking']}"
         style="width:100%;">
  </div>
  <div class="chart-card">
    <img src="data:image/png;base64,{grafici['mix_prodotto']}"
         style="width:100%;">
  </div>
</div>

<table>
  <thead>
    <tr>
      <th>Stazione</th><th>Litri</th><th>Fatturato</th>
      <th>% Verde</th><th>% Diesel</th><th>% Flotte</th>
      <th>% Rete</th><th>Margine est.</th>
    </tr>
  </thead>
  <tbody>{righe}</tbody>
</table>
</body>
</html>"""

    # =============================================
    # PDF
    # =============================================

    def genera_pdf(self) -> str:
        """Genera un PDF con reportlab."""
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib import colors
            from reportlab.lib.units import cm
            from reportlab.platypus import (SimpleDocTemplate, Paragraph,
                                             Spacer, Table, TableStyle)
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        except ImportError:
            print("reportlab non installato. Esegui: pip install reportlab")
            return ''

        path = os.path.join(self.output_dir, f"report_{self._timestamp}.pdf")
        doc  = SimpleDocTemplate(path, pagesize=A4,
                                  leftMargin=2*cm, rightMargin=2*cm,
                                  topMargin=2*cm, bottomMargin=2*cm)
        styles = getSampleStyleSheet()
        elementi = []

        # Titolo
        titolo_style = ParagraphStyle('titolo', parent=styles['Title'],
                                       fontSize=20, textColor=colors.HexColor('#185FA5'))
        elementi.append(Paragraph("Report Rete Distributori Carburante", titolo_style))
        elementi.append(Paragraph(
            f"Generato il {datetime.now().strftime('%d/%m/%Y %H:%M')} — "
            f"{self.kpi['n_stazioni']} stazioni",
            styles['Normal']))
        elementi.append(Spacer(1, 0.5*cm))

        # KPI tabella
        elementi.append(Paragraph("KPI Rete", styles['Heading2']))
        kpi_data = [
            ['Metrica', 'Valore'],
            ['Totale litri', f"{self.kpi['totale_litri']:,.0f}"],
            ['Fatturato', f"€{self.kpi['totale_euro']:,.0f}"],
            ['Margine stimato', f"€{self.kpi['margine_stimato_rete']:,.0f}"],
            ['% Verde rete', f"{self.kpi['pct_verde_rete']:.1f}%"],
            ['% Diesel rete', f"{self.kpi['pct_diesel_rete']:.1f}%"],
            ['% Flotte rete', f"{self.kpi['pct_flotte_rete']:.1f}%"],
            ['Stazione top', self.kpi['stazione_top']],
        ]
        t = Table(kpi_data, colWidths=[8*cm, 8*cm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#185FA5')),
            ('TEXTCOLOR',  (0,0), (-1,0), colors.white),
            ('FONTNAME',   (0,0), (-1,0), 'Helvetica-Bold'),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f0f5ff')]),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cccccc')),
            ('FONTSIZE', (0,0), (-1,-1), 10),
            ('PADDING', (0,0), (-1,-1), 6),
        ]))
        elementi.append(t)
        elementi.append(Spacer(1, 0.5*cm))

        # Ranking tabella
        elementi.append(Paragraph("Ranking stazioni", styles['Heading2']))
        rank_data = [['Stazione', 'Litri', 'Fatturato', '% Verde', '% Diesel', '% Rete']]
        for _, row in self.ranking.iterrows():
            rank_data.append([
                row['nome'],
                f"{row['totale_litri']:,.0f}",
                f"€{row['totale_euro']:,.0f}",
                f"{row['pct_verde']:.1f}%",
                f"{row['pct_diesel']:.1f}%",
                f"{row['quota_rete_pct']:.1f}%",
            ])
        t2 = Table(rank_data, colWidths=[4*cm, 3.5*cm, 3.5*cm, 2*cm, 2.5*cm, 2*cm])
        t2.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#185FA5')),
            ('TEXTCOLOR',  (0,0), (-1,0), colors.white),
            ('FONTNAME',   (0,0), (-1,0), 'Helvetica-Bold'),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f0f5ff')]),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cccccc')),
            ('FONTSIZE', (0,0), (-1,-1), 9),
            ('PADDING', (0,0), (-1,-1), 5),
        ]))
        elementi.append(t2)

        doc.build(elementi)
        print(f"PDF generato: {path}")
        return path