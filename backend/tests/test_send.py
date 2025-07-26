import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail


FROM_ADDRESS = "zhurong878@gmail.com"
TO_ADDRESS   = "your.email@yourdomain.com" 

sg = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
message = Mail(
    from_email=FROM_ADDRESS,
    to_emails=TO_ADDRESS,
    subject="Crawlernaut SendGrid test",
    html_content="<p>If you see this, SendGrid is configured correctly!</p>"
)
resp = sg.send(message)
print("status:", resp.status_code)
print("body:  ", resp.body)
print("headers:", resp.headers)
