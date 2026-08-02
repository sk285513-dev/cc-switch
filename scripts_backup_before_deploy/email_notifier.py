import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

def send_alert_email(subject: str, body: str, to_email: str = "sk285513@gmail.com"):
    """
    寄送通知信。需要 .env 內有 SMTP_EMAIL 與 SMTP_PASSWORD (例如 Gmail 應用程式密碼)
    """
    # 讀取 .env
    script_dir = os.path.dirname(os.path.abspath(__file__))
    potential_paths = [
        os.path.join(script_dir, ".env"),
        os.path.join(script_dir, "..", ".env"),
        os.path.join(os.getcwd(), ".env")
    ]
    for p in potential_paths:
        if os.path.exists(p):
            load_dotenv(p)
            break

    smtp_email = os.environ.get("SMTP_EMAIL")
    smtp_password = os.environ.get("SMTP_PASSWORD")

    if not smtp_email or not smtp_password:
        print("[ERROR] [Email Notifier] 尚未設定 SMTP_EMAIL 或 SMTP_PASSWORD。無法寄信。")
        return False

    msg = MIMEMultipart()
    msg['From'] = smtp_email
    msg['To'] = to_email
    msg['Subject'] = f"[LexMind-Omni AI 警報] {subject}"
    
    msg.attach(MIMEText(body, 'plain', 'utf-8'))

    try:
        # 使用 Gmail SMTP 伺服器作為預設
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(smtp_email, smtp_password)
        server.send_message(msg)
        server.quit()
        print(f"[OK] [Email Notifier] 已成功寄送警報信件至 {to_email}")
        return True
    except Exception as e:
        print(f"[ERROR] [Email Notifier] 寄送失敗: {e}")
        return False

if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 3:
        send_alert_email(sys.argv[1], sys.argv[2])
    else:
        print("Usage: python email_notifier.py 'Subject' 'Body'")
