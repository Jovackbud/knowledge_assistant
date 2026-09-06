"""
Email service for outbound ticket replies.
Uses Python stdlib smtplib — no new dependencies required.
Supports STARTTLS (port 587) on any SMTP provider (Gmail, Outlook, etc.).
Thread continuity is maintained via Message-ID / In-Reply-To headers.
"""
import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr, formatdate, make_msgid
from typing import Optional

logger = logging.getLogger(__name__)

# --- SMTP Configuration (from env) ---
SMTP_HOST     = os.getenv("SMTP_HOST", "")
SMTP_PORT     = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER     = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
EMAIL_FROM    = os.getenv("SMTP_USER", "")          # reuse SMTP_USER as From address
EMAIL_FROM_NAME = os.getenv("EMAIL_FROM_NAME", "AI4AI Support")

_EMAIL_CONFIGURED = bool(SMTP_HOST and SMTP_USER and SMTP_PASSWORD)
if not _EMAIL_CONFIGURED:
    logger.warning(
        "Email is not configured (SMTP_HOST / SMTP_USER / SMTP_PASSWORD missing). "
        "Ticket replies will be stored but NOT sent."
    )


def _thread_message_id(ticket_id: int) -> str:
    """Deterministic Message-ID for ticket root — keeps replies in one thread."""
    domain = (EMAIL_FROM.split("@")[1] if "@" in EMAIL_FROM else "ai4ai.internal")
    return f"<ticket-{ticket_id}@{domain}>"


def send_ticket_reply(
    ticket_id: int,
    to_email: str,
    subject: str,
    reply_text: str,
    admin_name: Optional[str] = None,
) -> bool:
    """
    Send a plain-text reply email to the ticket creator.

    Parameters
    ----------
    ticket_id   : Ticket ID — used to build consistent thread headers.
    to_email    : Recipient address (the user who raised the ticket).
    subject     : Email subject — prefixed with 'Re:' automatically if missing.
    reply_text  : Plain-text body of the reply.
    admin_name  : Optional display name of the replying admin.

    Returns True on success, False on any SMTP error.
    """
    if not _EMAIL_CONFIGURED:
        logger.warning(
            f"Email not sent for ticket #{ticket_id} — SMTP is not configured. "
            "Set SMTP_HOST, SMTP_USER, and SMTP_PASSWORD env vars."
        )
        return False

    # Build subject
    if not subject.lower().startswith("re:"):
        subject = f"Re: {subject}"

    # Build message
    msg = MIMEMultipart("alternative")
    msg["From"]    = formataddr((EMAIL_FROM_NAME, EMAIL_FROM))
    msg["To"]      = to_email
    msg["Subject"] = subject
    msg["Date"]    = formatdate(localtime=True)

    # Thread headers — standard RFC 2822 / RFC 5321 threading
    root_mid = _thread_message_id(ticket_id)
    msg["Message-ID"] = make_msgid(domain=EMAIL_FROM.split("@")[-1] if "@" in EMAIL_FROM else "ai4ai.internal")
    msg["In-Reply-To"] = root_mid
    msg["References"]  = root_mid

    # Plain-text body
    from_label = admin_name or EMAIL_FROM_NAME
    plain_body = f"{reply_text}\n\n—\n{from_label}\nAI4AI Support  |  Ticket #{ticket_id}"
    msg.attach(MIMEText(plain_body, "plain", "utf-8"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(EMAIL_FROM, [to_email], msg.as_string())
        logger.info(f"Reply sent for ticket #{ticket_id} to {to_email}")
        return True
    except smtplib.SMTPAuthenticationError:
        logger.error(
            f"SMTP authentication failed for ticket #{ticket_id}. "
            "Check SMTP_USER and SMTP_PASSWORD (Gmail requires an App Password, not account password)."
        )
        return False
    except smtplib.SMTPException as e:
        logger.error(f"SMTP error sending reply for ticket #{ticket_id}: {e}", exc_info=True)
        return False
    except OSError as e:
        logger.error(f"Network error sending reply for ticket #{ticket_id}: {e}", exc_info=True)
        return False
