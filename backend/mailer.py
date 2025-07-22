# backend/mailer.py
import os
import sys
from datetime import datetime

from dotenv import load_dotenv
import certifi

load_dotenv()
os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
FROM_ADDRESS = "zhurong878@gmail.com"

print(
    "→ [mailer] SENDGRID_API_KEY set?",
    bool(SENDGRID_API_KEY),
    "length:",
    len(SENDGRID_API_KEY or ""),
    file=sys.stderr,
)

# Helper function
def _send_or_log(message: Mail, dev_fallback: str) -> None:
    """
    Send a message through SendGrid, or log to stderr if SENDGRID_API_KEY
    is missing (development / CI environments).
    """
    if SENDGRID_API_KEY:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        resp = sg.send(message)
        if resp.status_code >= 400:
            raise RuntimeError(f"SendGrid error {resp.status_code}")
        return

    # Dev-mode fallback
    print(dev_fallback, file=sys.stderr)


def send_verification_email(to_email: str, code: str) -> None:
    subject = "Your Crawlernaut verification code"
    html = (
        "<p>Your Crawlernaut verification code is "
        f"<strong>{code}</strong>. It expires in one minute.</p>"
    )

    message = Mail(

        from_email=FROM_ADDRESS,
        to_emails=to_email,
        subject=subject,
        html_content=html,
    )
def send_crawl_finished_email(
    to_email: str,
    job_name: str,
    ran_at: datetime,
    result_url: str | None = None,
) -> None:

    subject = f"Crawlernaut – “{job_name}” finished ✔"

    body = (
        f"<p>Your scheduled crawl <strong>{job_name}</strong> finished at "
        f"{ran_at:%Y-%m-%d %H:%M UTC}.</p>"
    )

    if result_url:
        body += f'<p>View the results <a href="{result_url}">here</a>.</p>'

    message = Mail(
        from_email=FROM_ADDRESS,
        to_emails=to_email,
        subject=subject,
        html_content=body,
    )

    _send_or_log(message, f"[DEV] verification code for {to_email}: {code}")

    _send_or_log(
        message,
        (
            "[DEV] crawl finished email → "
            f"{to_email}: {job_name} at {ran_at.isoformat()} "
            f"{result_url or ''}"
        ),
    )