import imaplib
import email
from bs4 import BeautifulSoup
import requests
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ✅ Your Gmail credentials (App Password, no spaces)
EMAIL = "skypropertydeals@gmail.com"
PASSWORD = "gmnitmkedwwvkorj"
IMAP_SERVER = "imap.gmail.com"

# ✅ Keywords to detect renovation potential
KEYWORDS = [
    "renovation required", "fixer-upper", "TLC", "needs work",
    "bargain", "unfinished", "foreclosure", "needs repairs", "distressed", "divorce",
    "urgent sale", "motivated seller"
]

def send_summary_report(total_p24, total_pprop, match_details):
    sender = EMAIL
    recipient = "scylagh@yahoo.com"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "🏘️ Daily Property Alert Summary"
    msg["From"] = sender
    msg["To"] = recipient

    body = f"""
    <h3>Daily Property Filter Summary</h3>
    <ul>
      <li><b>Property24 emails scanned:</b> {total_p24}</li>
      <li><b>PrivateProperty emails scanned:</b> {total_pprop}</li>
      <li><b>Total Hot Properties:</b> {len(match_details)}</li>
    </ul>
    """

    if match_details:
        body += "<h4>Matched Listings:</h4><ul>"
        for url, keywords in match_details.items():
            body += f"<li><a href='{url}'>{url}</a><br><small>Matched keywords: {', '.join(keywords)}</small></li>"
        body += "</ul>"
    else:
        body += "<p>No matching properties today.</p>"

    msg.attach(MIMEText(body, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender, PASSWORD)
            server.sendmail(sender, recipient, msg.as_string())
            print("✅ Summary email sent.")
    except Exception as e:
        print(f"⚠️ Failed to send summary email: {e}")

def get_matching_property_links():
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(EMAIL, PASSWORD)
    mail.select("inbox")

    matches = []
    match_details = {}

    # 🔍 Search unread emails from both sources
    status1, data1 = mail.search(None, '(UNSEEN FROM "no-reply@property24.com")')
    status2, data2 = mail.search(None, '(UNSEEN FROM "noreply@privateproperty.co.za")')

    all_ids = data1[0].split() + data2[0].split()

    for num in all_ids:
        status, msg_data = mail.fetch(num, '(RFC822)')

        raw_email = None
        for part in msg_data:
            if isinstance(part, tuple):
                raw_email = part[1]
                break

        if raw_email is None:
            print(f"⚠️ Skipping email {num.decode()} — unable to parse")
            continue

        msg = email.message_from_bytes(raw_email)

        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/html":
                    try:
                        body = part.get_payload(decode=True).decode(errors="ignore")
                        break
                    except:
                        continue
        else:
            try:
                body = msg.get_payload(decode=True).decode(errors="ignore")
            except:
                continue

        soup = BeautifulSoup(body, "html.parser")
        links = [a["href"] for a in soup.find_all("a", href=True)
                 if "property24.com" in a["href"] or "privateproperty.co.za" in a["href"]]

        is_hot = False

        for url in links:
            try:
                resp = requests.get(url, timeout=10)
                text = resp.text.lower()
                keywords_found = [k for k in KEYWORDS if k.lower() in text]
                if keywords_found:
                    matches.append(url)
                    match_details[url] = keywords_found
                    is_hot = True
            except:
                continue

        if is_hot:
            result = mail.copy(num.decode(), '"Hot Property"')
            if result[0] == 'OK':
                print(f"✅ Copied email {num.decode()} to 'Hot Property'")
                # ❗ Do NOT mark as read — keep unread in inbox
            else:
                print(f"⚠️ COPY failed for email {num.decode()}: {result}")
                # Still mark it as read so it's not stuck
                mail.store(num.decode(), '+FLAGS', '\\Seen')
        else:
            # Not hot, mark as read
            mail.store(num.decode(), '+FLAGS', '\\Seen')


    mail.logout()

    # Totals per source
    total_p24 = len(data1[0].split())
    total_pprop = len(data2[0].split())

    # Send email summary
    send_summary_report(total_p24, total_pprop, match_details)

    return matches

# 🔁 Run it
matches = get_matching_property_links()
if matches:
    print("\n🔥 Matching Listings:")
    for link in matches:
        print("Matched:", link)
else:
    print("\n✅ No matching listings found this time.")
