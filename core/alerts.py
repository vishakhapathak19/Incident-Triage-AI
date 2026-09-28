"""Escalation: P1/P2 incidents are logged and pushed to Slack and/or email if configured via env vars."""
import json
import os
import smtplib
import urllib.request
from email.message import EmailMessage


def notify(i, inc, cause):
    if inc["severity"] not in ("P1", "P2"):
        return
    text = (f"[{inc['severity']}] Incident #{i} in {inc['service']}: {inc['template']} "
            f"(x{inc['count']}). Likely cause: {cause}")
    with open("alerts.log", "a") as f:
        f.write(text + "\n")
    hook = os.getenv("SLACK_WEBHOOK_URL")
    if hook:
        try:
            req = urllib.request.Request(hook, json.dumps({"text": text}).encode(),
                                         {"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=5)
        except Exception as e:
            print("Slack alert failed:", e)
    if os.getenv("SMTP_HOST") and os.getenv("ALERT_TO"):
        try:
            m = EmailMessage()
            m["Subject"], m["From"], m["To"] = f"[{inc['severity']}] {inc['service']} incident", \
                os.getenv("SMTP_USER", "alerts@localhost"), os.getenv("ALERT_TO")
            m.set_content(text)
            with smtplib.SMTP(os.getenv("SMTP_HOST"), int(os.getenv("SMTP_PORT", 587))) as s:
                s.starttls()
                if os.getenv("SMTP_USER"):
                    s.login(os.getenv("SMTP_USER"), os.getenv("SMTP_PASS", ""))
                s.send_message(m)
        except Exception as e:
            print("Email alert failed:", e)
