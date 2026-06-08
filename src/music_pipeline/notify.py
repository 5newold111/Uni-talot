"""通知（半自動配信のリマインド）。

SMTP 設定があればメール送信、無ければログ出力にフォールバックする。
"""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from .config import Settings

logger = logging.getLogger(__name__)


class Notifier:
    def __init__(self, settings: Settings):
        self.settings = settings

    def send(self, subject: str, body: str) -> None:
        s = self.settings
        if not (s.notify_email and s.smtp_host and s.smtp_user and s.smtp_password):
            logger.info("[notify] %s\n%s", subject, body)
            return
        try:
            msg = EmailMessage()
            msg["Subject"] = subject
            msg["From"] = s.smtp_user
            msg["To"] = s.notify_email
            msg.set_content(body)
            with smtplib.SMTP(s.smtp_host, s.smtp_port) as server:
                server.starttls()
                server.login(s.smtp_user, s.smtp_password)
                server.send_message(msg)
            logger.info("[notify] email sent to %s", s.notify_email)
        except Exception as exc:  # pragma: no cover
            logger.warning("[notify] email failed (%s); body:\n%s", exc, body)
