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
        subject = "Galeria ta Artify e gata!"
        base = (self.settings.public_base_url or "").rstrip("/")
        order_link = f"{base}/order/{order_id}" if base else "#"
        download_all_link = f"{base}/api/orders/{order_id}/download-all" if base else "#"
        hero = result_urls[0] if result_urls else ""
        thumbs = result_urls[:15]
        n = len(thumbs)
        labels = result_labels[:n] if result_labels and len(result_labels) >= n else None
        if labels and len(labels) != n:
            labels = None
        if labels:
            thumbs_html = "".join(
                f'<div style="display:inline-block;margin:8px;vertical-align:top;text-align:center;">'
                f'<a href="{u}" style="display:block;"><img src="{u}" alt="{_escape_html(title)}" style="width:88px;height:88px;object-fit:cover;border-radius:4px;border:2px solid #e8dcc8;box-shadow:0 2px 6px rgba(0,0,0,0.06);display:block;" /></a>'
                f'<span style="display:block;margin-top:4px;font-size:10px;color:#6b5d4f;line-height:1.2;">{_escape_html(title)} — {_escape_html(artist)}</span>'
                f"</div>"
                for u, (title, artist) in zip(thumbs, labels)
            )
        else:
            thumbs_html = "".join(
                f'<a href="{u}" style="display:inline-block;margin:4px;"><img src="{u}" alt="Operă" style="width:88px;height:88px;object-fit:cover;border-radius:4px;border:2px solid #e8dcc8;box-shadow:0 2px 6px rgba(0,0,0,0.06);display:block;" /></a>'
                for u in thumbs
            )
        body = f"""
        <div style="font-family:Georgia,'Times New Roman',serif;background:#e8e2d8;padding:24px 16px;color:#2c2419;">
          <div style="max-width:560px;margin:0 auto;background:#fdfbf7;border:1px solid #d4cdc0;border-radius:6px;overflow:hidden;box-shadow:0 6px 24px rgba(0,0,0,0.08);">
            <div style="padding:24px 24px 16px 24px;background:linear-gradient(180deg,#fff 0%,#faf7f2 100%);border-bottom:2px solid #e8dcc8;">
              <div style="font-size:24px;font-weight:600;color:#1e3a5f;letter-spacing:0.02em;">Galeria ta Artify e gata</div>
              <div style="margin-top:6px;font-size:14px;color:#6b5d4f;">Stil: <strong style="color:#8b7355;">{_escape_html(style_name or 'Maeștri')}</strong> · Comandă {_escape_html(order_id)}</div>
            </div>
            {"<div style='padding:16px 20px;background:#f5f0e8;'><div style='border:3px solid #c9a96e;border-radius:4px;padding:6px;background:#fff;'><img src='" + hero + "' alt='Opera ta' style='width:100%;max-height:300px;object-fit:contain;display:block;' /></div></div>" if hero else ""}
            <div style="padding:16px 20px 8px 20px;font-size:11px;color:#8b7355;text-transform:uppercase;letter-spacing:0.1em;">Toate cele {n} portrete</div>
            <div style="padding:8px 16px 16px 16px;text-align:center;line-height:0;">{thumbs_html}</div>
            <div style="padding:20px 24px;background:#f5f0e8;border-top:1px solid #e8dcc8;">
              <p style="margin:0 0 14px 0;font-size:14px;color:#6b5d4f;">Salvează setul complet într-un singur clic.</p>
              <a href="{download_all_link}" style="display:inline-block;padding:12px 22px;background:linear-gradient(135deg,#1e3a5f 0%,#2d5a8e 100%);color:#fff;text-decoration:none;border-radius:4px;font-weight:600;font-size:14px;margin-right:8px;">Descarcă toate</a>
              <a href="{order_link}" style="display:inline-block;padding:12px 22px;background:#fff;color:#1e3a5f;text-decoration:none;border-radius:4px;font-weight:600;font-size:14px;border:2px solid #c9a96e;">Vezi online</a>
            </div>
            <div style="padding:12px 24px;text-align:center;font-size:12px;color:#9a8f7f;border-top:1px solid #eee8de;">Mulțumim că ai ales Artify — făcut cu drag pentru iubitorii de artă.</div>
          </div>
        </div>
        """
        self._send(email, subject, body)

    def send_order_failed(self, order_id: str, email: str, error: str):
        subject = "Artify – Issue With Your Order"
        body = f"""
        <h2>We're sorry</h2>
        <p>There was an issue processing your artwork (Order: {order_id}).</p>
        <p>Our team has been notified and will look into it. Please contact support if you need assistance.</p>
        <p>Error details: {error}</p>
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
