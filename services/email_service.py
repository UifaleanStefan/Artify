"""
Email service for order notifications.
"""
import logging
import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from config import get_settings

logger = logging.getLogger(__name__)


def _escape_html(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


class EmailService:
    def __init__(self):
        self.settings = get_settings()

    def send_result_ready(
        self,
        order_id: str,
        email: str,
        result_urls: list[str],
        style_name: Optional[str] = None,
        result_labels: Optional[list[tuple[str, str]]] = None,
    ):
        """result_labels: optional list of (painting_title, artist) for each result image (same length as result_urls)."""
        subject = "✨ Galeria ta e gata — descoperă portretele!"
        base = (self.settings.public_base_url or "").rstrip("/")

        order_link = f"{base}/order/{order_id}" if base else "#"
        download_all_link = f"{base}/api/orders/{order_id}/download-all" if base else "#"
        n = len(result_urls) if result_urls else 0

        # No images in email – only the CTA button so users never miss what they paid for
        body = f"""
        <div style="font-family:'Segoe UI',-apple-system,BlinkMacSystemFont,sans-serif;background:#f1f5f9;padding:32px 16px;color:#1e293b;">
          <div style="max-width:560px;margin:0 auto;background:#ffffff;border:1px solid #e2e8f0;border-radius:12px;overflow:hidden;box-shadow:0 12px 40px rgba(0,0,0,0.08);">
            <div style="padding:28px 24px 24px 24px;background:#fff;border-bottom:3px solid #2563eb;">
              <div style="text-align:center;">
                <div style="font-size:26px;font-weight:700;color:#1e293b;letter-spacing:-0.01em;line-height:1.2;">Galeria ta e gata</div>
                <div style="margin-top:6px;font-size:15px;color:#64748b;">Tu, pictat în stilul <strong style="color:#2563eb;">{_escape_html(style_name or 'Maeștri')}</strong></div>
                <div style="margin-top:10px;font-size:11px;color:#94a3b8;">Comandă {_escape_html(order_id)} – {n} portrete</div>
              </div>
            </div>
            <div style="padding:32px 24px 36px 24px;background:#fff;text-align:center;">
              <p style="margin:0 0 24px 0;font-size:16px;color:#1e293b;line-height:1.5;font-weight:600;">Rezultatele tale sunt gata. Apasă butonul de mai jos pentru a vedea galeria.</p>
              <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin:0 auto 24px auto;">
                <tr><td align="center" style="border-radius:12px;background-color:#2563eb;padding:0;">
                  <a href="{order_link}" style="display:inline-block;padding:20px 40px;color:#ffffff !important;text-decoration:none;border-radius:12px;font-weight:700;font-size:18px;background-color:#2563eb;">Vezi galeria pe site</a>
                </td></tr>
              </table>
              <p style="margin:0 0 8px 0;font-size:14px;color:#64748b;">Sau descarcă toate imaginile:</p>
              <p style="margin:0;"><a href="{download_all_link}" style="color:#2563eb;text-decoration:underline;font-weight:600;font-size:14px;">Descarcă toate imaginile (ZIP)</a></p>
            </div>
            <div style="padding:18px 24px;text-align:center;font-size:12px;color:#64748b;border-top:1px solid #e2e8f0;background:#f1f5f9;">
              Mulțumim că ai ales Artify. Făcut cu drag pentru iubitorii de artă.
            </div>
          </div>
        </div>
        """
        self._send(email, subject, body)

    def send_order_failed(self, order_id: str, email: str, error: str):
        subject = "Artify – Problemă la comanda ta"
        body = f"""
        <h2>Ne cerem scuze</h2>
        <p>A apărut o problemă la procesarea operei tale (Comandă: {order_id}).</p>
        <p>Echipa noastră a fost notificată și va verifica situația. Te rugăm să ne contactezi dacă ai nevoie de ajutor.</p>
        <p>Detalii eroare: {error}</p>
        """
        self._send(email, subject, body)

    def _send(self, to: str, subject: str, html_body: str):
        settings = self.settings
        if settings.resend_api_key:
            self._send_resend(to, subject, html_body)
        elif settings.sendgrid_api_key:
            self._send_sendgrid(to, subject, html_body)
        elif settings.smtp_host:
            self._send_smtp(to, subject, html_body)
        else:
            logger.warning("No email provider configured. Set RESEND_API_KEY or SENDGRID_API_KEY (HTTP APIs work on Render; SMTP is blocked).")

    def _send_smtp(self, to: str, subject: str, html_body: str):
        s = self.settings
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{s.from_name} <{s.from_email}>"
        msg["To"] = to
        msg.attach(MIMEText(html_body, "html"))
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                timeout_seconds = 30
                if int(s.smtp_port) == 465:
                    with smtplib.SMTP_SSL(s.smtp_host, s.smtp_port, timeout=timeout_seconds) as server:
                        if s.smtp_user and s.smtp_password:
                            server.login(s.smtp_user, s.smtp_password)
                        server.send_message(msg)
                else:
                    with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=timeout_seconds) as server:
                        server.starttls()
                        if s.smtp_user and s.smtp_password:
                            server.login(s.smtp_user, s.smtp_password)
                        server.send_message(msg)
                logger.info("Email sent to %s via SMTP (attempt %d/%d, port %s)", to, attempt, max_attempts, s.smtp_port)
                return
            except Exception as e:
                if attempt == max_attempts:
                    logger.error("SMTP send failed after %d attempts: %s", max_attempts, e)
                    return
                backoff = 2 ** attempt
                logger.warning(
                    "SMTP send failed (attempt %d/%d): %s. Retrying in %ss",
                    attempt,
                    max_attempts,
                    e,
                    backoff,
                )
                time.sleep(backoff)

    def _send_resend(self, to: str, subject: str, html_body: str):
        """Resend.com – free 100 emails/day, HTTP API (works on Render)."""
        import httpx
        s = self.settings
        payload = {
            "from": f"{s.from_name} <{s.from_email}>",
            "to": [to],
            "subject": subject,
            "html": html_body,
        }
        try:
            r = httpx.post(
                "https://api.resend.com/emails",
                json=payload,
                headers={"Authorization": f"Bearer {s.resend_api_key}"},
                timeout=30,
            )
            if r.status_code < 300:
                logger.info("Email sent to %s via Resend", to)
            else:
                logger.error("Resend error %s: %s", r.status_code, r.text)
        except Exception as e:
            logger.error("Resend send failed: %s", e)

    def _send_sendgrid(self, to: str, subject: str, html_body: str):
        import httpx
        s = self.settings
        data = {
            "personalizations": [{"to": [{"email": to}]}],
            "from": {"email": s.from_email, "name": s.from_name},
            "subject": subject,
            "content": [{"type": "text/html", "value": html_body}],
        }
        try:
            r = httpx.post(
                "https://api.sendgrid.com/v3/mail/send",
                json=data,
                headers={"Authorization": f"Bearer {s.sendgrid_api_key}"},
            )
            if r.status_code < 300:
                logger.info(f"SendGrid email sent to {to}")
            else:
                logger.error(f"SendGrid error {r.status_code}: {r.text}")
        except Exception as e:
            logger.error(f"SendGrid send failed: {e}")
