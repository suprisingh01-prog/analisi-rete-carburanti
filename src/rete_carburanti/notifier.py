"""
EmailNotifier — manda alert email quando rileva anomalie.
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional
from .config import Config
from .logger import get_logger

logger = get_logger(__name__)


class EmailNotifier:
    """
    Manda email di alert quando vengono rilevate anomalie.

    Uso:
        notifier = EmailNotifier()
        notifier.invia_alert(report_anomalie)
    """

    def __init__(self):
        self.mittente    = Config.EMAIL_MITTENTE
        self.password    = Config.EMAIL_APP_PASSWORD
        self.destinatario = Config.EMAIL_DESTINATARIO

    def invia_alert(self, report: dict) -> bool:
        """
        Manda un'email con il report delle anomalie.
        Restituisce True se l'email è stata mandata, False altrimenti.
        """
        if not self._config_valida():
            logger.warning("Email non configurata — alert saltato")
            return False

        n_mom    = len(report.get('anomalie_mom', []))
        n_zscore = len(report.get('anomalie_zscore', []))

        if n_mom == 0 and n_zscore == 0:
            logger.info("Nessuna anomalia — email non necessaria")
            return False

        try:
            msg = self._costruisci_email(report)
            self._invia(msg)
            logger.info(f"Alert email inviata a {self.destinatario}")
            return True
        except Exception as e:
            logger.error(f"Errore invio email: {e}")
            return False

    def _config_valida(self) -> bool:
        """Verifica che la configurazione email sia completa."""
        return all([self.mittente, self.password, self.destinatario])

    def _costruisci_email(self, report: dict) -> MIMEMultipart:
        """Costruisce il messaggio email in formato HTML."""
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"⚠️ Alert Rete Carburanti — {datetime.now().strftime('%d/%m/%Y')}"
        msg['From']    = self.mittente
        msg['To']      = self.destinatario

        html = self._template_html(report)
        msg.attach(MIMEText(html, 'html'))
        return msg

    def _template_html(self, report: dict) -> str:
        """Genera il corpo HTML dell'email."""
        anomalie_mom    = report.get('anomalie_mom', [])
        anomalie_zscore = report.get('anomalie_zscore', [])
        summary         = report.get('summary', '')

        # Righe tabella MoM
        righe_mom = ''
        for a in anomalie_mom:
            colore = '#D85A30' if a['var_pct'] < 0 else '#0F6E56'
            righe_mom += f"""
            <tr>
                <td>{a['nome']}</td>
                <td>{a['litri_attuale']:,.0f}</td>
                <td>{a['litri_precedente']:,.0f}</td>
                <td style="color:{colore};font-weight:bold">{a['var_pct']:+.1f}%</td>
                <td>{a['tipo']}</td>
            </tr>"""

        # Righe tabella z-score
        righe_z = ''
        for a in anomalie_zscore:
            righe_z += f"""
            <tr>
                <td>{a['nome']}</td>
                <td>{a['totale_litri']:,.0f}</td>
                <td>{a['zscore']:+.2f}</td>
                <td>{a['tipo']}</td>
            </tr>"""

        sezione_mom = ''
        if anomalie_mom:
            sezione_mom = f"""
            <h2 style="color:#185FA5;">Anomalie MoM</h2>
            <table border="1" cellpadding="8" cellspacing="0"
                   style="border-collapse:collapse;width:100%;">
                <tr style="background:#185FA5;color:white;">
                    <th>Stazione</th><th>Litri attuale</th>
                    <th>Litri precedente</th><th>Variazione</th><th>Tipo</th>
                </tr>
                {righe_mom}
            </table>"""

        sezione_z = ''
        if anomalie_zscore:
            sezione_z = f"""
            <h2 style="color:#185FA5;">Anomalie Z-Score</h2>
            <table border="1" cellpadding="8" cellspacing="0"
                   style="border-collapse:collapse;width:100%;">
                <tr style="background:#185FA5;color:white;">
                    <th>Stazione</th><th>Litri</th><th>Z-Score</th><th>Tipo</th>
                </tr>
                {righe_z}
            </table>"""

        return f"""
        <html><body style="font-family:sans-serif;padding:20px;">
            <h1 style="color:#D85A30;">⚠️ Alert Rete Carburanti</h1>
            <p style="color:#888;">
                Generato il {datetime.now().strftime('%d/%m/%Y %H:%M')}
            </p>
            <p style="font-size:16px;">{summary}</p>
            {sezione_mom}
            {sezione_z}
            <hr>
            <p style="color:#888;font-size:12px;">
                Sistema analisi rete carburanti — alert automatico
            </p>
        </body></html>"""

    def _invia(self, msg: MIMEMultipart) -> None:
        """Connette a Gmail e manda il messaggio."""
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(self.mittente, self.password)
            server.sendmail(self.mittente, self.destinatario, msg.as_string())