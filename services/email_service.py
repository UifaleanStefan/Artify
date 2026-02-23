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

        def ensure_absolute(url: str) -> str:
            if not url or not base:
                return url or ""
            u = (url or "").strip()
            if u.startswith("http://") or u.startswith("https://"):
                return u
            return f"{base}{u}" if u.startswith("/") else f"{base}/{u}"

        order_link = f"{base}/order/{order_id}" if base else "#"
        download_all_link = f"{base}/api/orders/{order_id}/download-all" if base else "#"
        hero = ensure_absolute(result_urls[0]) if result_urls else ""
        n = len(result_urls) if result_urls else 0
        labels = result_labels[:n] if result_labels and len(result_labels) >= n else None
        if labels and len(labels) != n:
            labels = None
        hero_title, hero_artist = (labels[0][0], labels[0][1]) if labels and labels else ("", "")

        # Flow: one hero image (first portrait) + clear link back to site. No thumbnail grid in email.
        hero_block = ""
        if hero:
            hero_caption = f'<div style="margin-top:12px;font-size:14px;color:#64748b;text-align:center;"><span style="font-weight:600;color:#1e293b;">{_escape_html(hero_title)}</span><br/><span style="font-style:italic;color:#64748b;">{_escape_html(hero_artist)}</span></div>' if (hero_title or hero_artist) else ""
            hero_block = f"""
            <div style="padding:24px 20px 28px 20px;background:#f8fafc;">
              <div style="font-size:11px;text-transform:uppercase;letter-spacing:0.14em;color:#64748b;margin-bottom:14px;text-align:center;">Primul tău portret</div>
              <div style="border:1px solid #e2e8f0;border-radius:16px;padding:12px;background:#fff;box-shadow:0 12px 40px rgba(0,0,0,0.1);max-width:100%;">
                <img src="{hero}" alt="Portretul tău" style="width:100%;max-height:380px;object-fit:contain;display:block;border-radius:8px;" />
              </div>
              {hero_caption}
            </div>"""

        body = f"""
        <div style="font-family:'Segoe UI',-apple-system,BlinkMacSystemFont,sans-serif;background:#f1f5f9;padding:32px 16px;color:#1e293b;">
          <div style="max-width:560px;margin:0 auto;background:#ffffff;border:1px solid #e2e8f0;border-radius:12px;overflow:hidden;box-shadow:0 12px 40px rgba(0,0,0,0.08);">
            <div style="padding:28px 24px 20px 24px;background:#fff;border-bottom:3px solid #2563eb;">
              <div style="text-align:center;">
                <div style="font-size:26px;font-weight:700;color:#1e293b;letter-spacing:-0.01em;line-height:1.2;">Galeria ta e gata</div>
                <div style="margin-top:6px;font-size:15px;color:#64748b;">Tu, pictat în stilul <strong style="color:#2563eb;">{_escape_html(style_name or 'Maeștri')}</strong></div>
                <div style="margin-top:10px;font-size:11px;color:#94a3b8;">Comandă {_escape_html(order_id)}</div>
              </div>
            </div>
            {hero_block}
            <div style="padding:28px 24px 32px 24px;background:#fff;text-align:center;">
              <p style="margin:0 0 8px 0;font-size:15px;color:#64748b;line-height:1.5;">Descoperă toate cele {n} portrete și povestea lor pe site.</p>
              <p style="margin:0 0 20px 0;font-size:14px;color:#94a3b8;">Un singur click — galeria completă te așteaptă.</p>
              <a href="{order_link}" style="display:inline-block;padding:16px 32px;background:linear-gradient(135deg,#1d4ed8 0%,#2563eb 100%);color:#ffffff !important;text-decoration:none;border-radius:12px;font-weight:600;font-size:16px;box-shadow:0 4px 14px rgba(37,99,235,0.35);-webkit-text-fill-color:#ffffff;">Vezi galeria pe site</a>
              <p style="margin:20px 0 0 0;font-size:13px;"><a href="{download_all_link}" style="color:#2563eb;text-decoration:none;font-weight:500;">Descarcă toate imaginile (ZIP)</a></p>
            </div>
            <div style="padding:18px 24px;text-align:center;font-size:12px;color:#64748b;border-top:1px solid #e2e8f0;background:#f1f5f9;">
              Mulțumim că ai ales Artify. Făcut cu drag pentru iubitorii de artă.
            </div>
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
