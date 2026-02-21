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
            f'<a href="{u}" style="display:inline-block;margin:4px;"><img src="{u}" alt="Artwork" style="width:110px;height:110px;object-fit:cover;border-radius:8px;border:1px solid #e5e7eb;" /></a>'
            for u in thumbs
        )
        body = f"""
        <div style="font-family:Arial,Helvetica,sans-serif;background:#f7f7fb;padding:24px;color:#111827;">
          <div style="max-width:680px;margin:0 auto;background:#ffffff;border:1px solid #e5e7eb;border-radius:14px;overflow:hidden;">
            <div style="padding:24px 24px 8px 24px;">
              <div style="font-size:24px;font-weight:700;color:#1e3a5f;">🎨 Your Artify gallery is ready</div>
              <div style="margin-top:8px;color:#4b5563;">Style: <strong>{style_name or 'Master Artist'}</strong></div>
              <div style="margin-top:4px;color:#6b7280;font-size:14px;">Order ID: {order_id}</div>
            </div>
            {"<div style='padding:0 24px 16px 24px;'><img src='" + hero + "' alt='Main artwork' style='width:100%;max-height:360px;object-fit:contain;background:#f9fafb;border-radius:10px;border:1px solid #e5e7eb;'></div>" if hero else ""}
            <div style="padding:0 24px 8px 24px;color:#374151;font-size:14px;">Preview your set:</div>
            <div style="padding:0 20px 12px 20px;">{thumbs_html}</div>
            <div style="padding:8px 24px 24px 24px;">
              <a href="{download_all_link}" style="display:inline-block;padding:12px 18px;background:#1e3a5f;color:#fff;text-decoration:none;border-radius:10px;font-weight:600;margin-right:8px;">Download all pictures (.zip)</a>
              <a href="{order_link}" style="display:inline-block;padding:12px 18px;background:#ffffff;color:#1e3a5f;text-decoration:none;border-radius:10px;font-weight:600;border:1px solid #cbd5e1;">Open order page</a>
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
        if settings.sendgrid_api_key:
            self._send_sendgrid(to, subject, html_body)
        elif settings.smtp_host:
            self._send_smtp(to, subject, html_body)
        else:
            logger.warning(f"No email provider configured. Would send to {to}: {subject}")

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
