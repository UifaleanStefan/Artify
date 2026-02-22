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


class EmailService:
    def __init__(self):
        self.settings = get_settings()

    def send_result_ready(
        self, order_id: str, email: str, result_urls: list[str], style_name: Optional[str] = None
    ):
        subject = "Your Artify Portrait is Ready!"
        base = (self.settings.public_base_url or "").rstrip("/")
        order_link = f"{base}/order/{order_id}" if base else "#"
        download_all_link = f"{base}/api/orders/{order_id}/download-all" if base else "#"
        hero = result_urls[0] if result_urls else ""
        thumbs = result_urls[:6]
        thumbs_html = "".join(
            f'<a href="{u}" style="display:inline-block;margin:6px;"><img src="{u}" alt="Artwork" style="width:90px;height:90px;object-fit:cover;border-radius:4px;border:2px solid #e8dcc8;box-shadow:0 2px 8px rgba(0,0,0,0.08);" /></a>'
            for u in thumbs
        )
        body = f"""
        <div style="font-family:Georgia,'Times New Roman',serif;background:linear-gradient(180deg,#f5f0e6 0%,#ebe5db 100%);padding:32px 20px;color:#2c2419;">
          <div style="max-width:620px;margin:0 auto;background:#fdfbf7;border:1px solid #ddd6c8;border-radius:4px;overflow:hidden;box-shadow:0 8px 32px rgba(0,0,0,0.06);">
            <div style="padding:28px 28px 12px 28px;border-bottom:1px solid #eee8de;">
              <div style="font-size:26px;font-weight:600;color:#1e3a5f;letter-spacing:0.02em;">Your Artify gallery is ready</div>
              <div style="margin-top:6px;font-size:15px;color:#6b5d4f;">Style: <strong style="color:#8b7355;">{style_name or 'Master Artist'}</strong></div>
              <div style="margin-top:2px;font-size:13px;color:#9a8f7f;">Order {order_id}</div>
            </div>
            {"<div style='padding:20px 28px;background:#f8f5ef;'><div style='border:3px solid #c9a96e;border-radius:2px;padding:8px;background:#fff;box-shadow:inset 0 0 0 1px #e8dcc8;'><img src='" + hero + "' alt='Your artwork' style='width:100%;max-height:340px;object-fit:contain;display:block;' /></div></div>" if hero else ""}
            <div style="padding:12px 28px 4px 28px;font-size:12px;color:#8b7355;text-transform:uppercase;letter-spacing:0.12em;">Preview your set</div>
            <div style="padding:8px 24px 20px 24px;text-align:center;">{thumbs_html}</div>
            <div style="padding:20px 28px 28px 28px;background:#f8f5ef;border-top:1px solid #eee8de;">
              <a href="{download_all_link}" style="display:inline-block;padding:14px 24px;background:linear-gradient(135deg,#1e3a5f 0%,#2d5a8e 100%);color:#fff;text-decoration:none;border-radius:4px;font-weight:600;font-size:15px;margin-right:10px;box-shadow:0 4px 12px rgba(30,58,95,0.25);">Download all pictures</a>
              <a href="{order_link}" style="display:inline-block;padding:14px 24px;background:#fff;color:#1e3a5f;text-decoration:none;border-radius:4px;font-weight:600;font-size:15px;border:2px solid #c9a96e;">View order page</a>
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
