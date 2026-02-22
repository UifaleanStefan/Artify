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
        hero = result_urls[0] if result_urls else ""
        thumbs = result_urls[:15]
        n = len(thumbs)
        labels = result_labels[:n] if result_labels and len(result_labels) >= n else None
        if labels and len(labels) != n:
            labels = None
        hero_title, hero_artist = (labels[0][0], labels[0][1]) if labels and labels else ("", "")
        # Use table layout so each thumbnail + caption stays in its own cell (email-client safe)
        COLS = 3
        CELL_WIDTH_PX = 120
        if labels:
            rows_html = []
            for i in range(0, n, COLS):
                cells = []
                for j in range(COLS):
                    idx = i + j
                    if idx < n:
                        u, (title, artist) = thumbs[idx], labels[idx]
                        cells.append(
                            f'<td style="width:{CELL_WIDTH_PX}px;max-width:{CELL_WIDTH_PX}px;padding:10px 6px;vertical-align:top;text-align:center;">'
                            f'<a href="{u}" style="display:block;text-decoration:none;"><img src="{u}" alt="{_escape_html(title)}" style="width:90px;height:90px;object-fit:cover;border-radius:8px;border:2px solid #d4c4a8;box-shadow:0 4px 12px rgba(0,0,0,0.08);display:block;margin:0 auto;" /></a>'
                            f'<div style="margin-top:8px;font-size:11px;color:#5c5248;line-height:1.4;width:90px;margin-left:auto;margin-right:auto;word-wrap:break-word;">{_escape_html(title)}<br/><span style="color:#8b7355;font-style:italic;">{_escape_html(artist)}</span></div>'
                            f'</td>'
                        )
                    else:
                        cells.append(f'<td style="width:{CELL_WIDTH_PX}px;padding:10px 6px;"></td>')
                rows_html.append(f'<tr>{"".join(cells)}</tr>')
            thumbs_html = f'<table role="presentation" cellspacing="0" cellpadding="0" border="0" style="margin:0 auto;border-collapse:collapse;"><tbody>{"".join(rows_html)}</tbody></table>'
        else:
            rows_html = []
            for i in range(0, n, COLS):
                cells = []
                for j in range(COLS):
                    idx = i + j
                    if idx < n:
                        u = thumbs[idx]
                        cells.append(
                            f'<td style="width:{CELL_WIDTH_PX}px;padding:10px 6px;vertical-align:top;text-align:center;">'
                            f'<a href="{u}"><img src="{u}" alt="Operă" style="width:90px;height:90px;object-fit:cover;border-radius:8px;border:2px solid #d4c4a8;box-shadow:0 4px 12px rgba(0,0,0,0.08);display:block;margin:0 auto;" /></a>'
                            f'</td>'
                        )
                    else:
                        cells.append(f'<td style="width:{CELL_WIDTH_PX}px;padding:10px 6px;"></td>')
                rows_html.append(f'<tr>{"".join(cells)}</tr>')
            thumbs_html = f'<table role="presentation" cellspacing="0" cellpadding="0" border="0" style="margin:0 auto;border-collapse:collapse;"><tbody>{"".join(rows_html)}</tbody></table>'
        hero_block = ""
        if hero:
            hero_caption = f'<div style="margin-top:10px;font-size:13px;color:#6b5d4f;"><span style="font-weight:600;color:#4a4035;">{_escape_html(hero_title)}</span><br/><span style="font-style:italic;color:#8b7355;">{_escape_html(hero_artist)}</span></div>' if (hero_title or hero_artist) else ""
            hero_block = f"""
            <div style="padding:28px 24px 24px 24px;background:#faf7f2;">
              <div style="font-size:12px;text-transform:uppercase;letter-spacing:0.12em;color:#9a8f7f;margin-bottom:12px;">Primul tău portret</div>
              <div style="border:4px solid #c9a96e;border-radius:8px;padding:8px;background:#fff;box-shadow:0 8px 32px rgba(0,0,0,0.1);">
                <img src="{hero}" alt="Portretul tău" style="width:100%;max-height:320px;object-fit:contain;display:block;" />
              </div>
              {hero_caption}
            </div>"""
        body = f"""
        <div style="font-family:'Segoe UI',Georgia,'Times New Roman',serif;background:#e0d9ce;padding:32px 16px;color:#2c2419;">
          <div style="max-width:580px;margin:0 auto;background:#fdfcf9;border:1px solid #d4cdc0;border-radius:12px;overflow:hidden;box-shadow:0 12px 40px rgba(0,0,0,0.12);">
            <div style="padding:32px 28px 24px 28px;background:#fff;border-bottom:3px solid #c9a96e;">
              <div style="text-align:center;">
                <div style="font-size:28px;font-weight:700;color:#1e3a5f;letter-spacing:-0.01em;line-height:1.2;">Galeria ta e gata</div>
                <div style="margin-top:8px;font-size:16px;color:#6b5d4f;">Tu, pictat în stilul <strong style="color:#8b7355;">{_escape_html(style_name or 'Maeștri')}</strong></div>
                <div style="margin-top:12px;font-size:12px;color:#9a8f7f;">Comandă {_escape_html(order_id)}</div>
              </div>
            </div>
            {hero_block}
            <div style="padding:24px 24px 12px 24px;">
              <div style="font-size:12px;text-transform:uppercase;letter-spacing:0.1em;color:#8b7355;margin-bottom:16px;font-weight:600;">Toate cele {n} portrete din galeria ta</div>
              <div style="padding:8px 0 8px 0;">{thumbs_html}</div>
            </div>
            <div style="padding:28px 28px 32px 28px;background:linear-gradient(180deg,#f5f0e8 0%,#ebe5dc 100%);border-top:2px solid #e8dcc8;">
              <p style="margin:0 0 8px 0;font-size:15px;font-weight:600;color:#4a4035;">Salvează galeria completă</p>
              <p style="margin:0 0 20px 0;font-size:14px;color:#6b5d4f;line-height:1.5;">Un singur clic — toate cele {n} imagini în rezoluție mare, gata de print sau de partajat.</p>
              <table role="presentation" cellspacing="0" cellpadding="0" border="0"><tr>
                <td style="padding-right:12px;"><a href="{download_all_link}" style="display:inline-block;padding:14px 28px;background:linear-gradient(135deg,#1e3a5f 0%,#2d5a8e 100%);color:#fff !important;text-decoration:none;border-radius:8px;font-weight:600;font-size:15px;box-shadow:0 4px 14px rgba(30,58,95,0.35);">Descarcă toate</a></td>
                <td><a href="{order_link}" style="display:inline-block;padding:14px 28px;background:#fff;color:#1e3a5f;text-decoration:none;border-radius:8px;font-weight:600;font-size:15px;border:2px solid #c9a96e;">Vezi galeria online</a></td>
              </tr></table>
            </div>
            <div style="padding:20px 28px;text-align:center;font-size:13px;color:#9a8f7f;border-top:1px solid #eee8de;background:#faf7f2;">
              Mulțumim că ai ales Artify.<br/>
              <span style="color:#b5a898;">Făcut cu drag pentru iubitorii de artă.</span>
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
