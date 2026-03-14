"""邮件发送模块 - 通过 SMTP 发送带 ICS 附件的日历邮件"""
import logging
import smtplib
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)


def send_calendar_mail(
    smtp_host: str,
    smtp_port: int,
    user: str,
    password: str,
    recipient: str,
    subject: str,
    body_text: str,
    ics_content: str,
) -> None:
    """
    发送包含 ICS 日历附件的邮件。

    Args:
        smtp_host: SMTP 服务器地址
        smtp_port: SMTP 端口
        user: 发件邮箱
        password: 发件密码/授权码
        recipient: 收件邮箱
        subject: 邮件主题
        body_text: 邮件正文
        ics_content: ICS 日历文件内容
    """
    msg = MIMEMultipart("mixed")
    msg["From"] = user
    msg["To"] = recipient
    msg["Subject"] = subject

    # 正文部分
    msg.attach(MIMEText(body_text, "plain", "utf-8"))

    # ICS 附件 - Content-Type 设为 text/calendar; method=REQUEST
    # 这是 QQ 邮箱自动识别日历卡片的关键
    ics_part = MIMEBase("text", "calendar", method="REQUEST", charset="UTF-8")
    ics_part.set_payload(ics_content.encode("utf-8"))
    ics_part.add_header("Content-Disposition", "attachment", filename="lecture.ics")
    msg.attach(ics_part)

    conn = smtplib.SMTP_SSL(smtp_host, smtp_port)
    try:
        conn.login(user, password)
        conn.sendmail(user, recipient, msg.as_string())
        logger.info("邮件已发送至 %s: %s", recipient, subject)
    finally:
        conn.quit()
