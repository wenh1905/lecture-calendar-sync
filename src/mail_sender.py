"""邮件发送模块 - 通过 SMTP 发送 iTIP 日历邀请邮件

关键：使用 MIMEText('calendar') + inline 内联方式触发 QQ 邮箱/Outlook 的日程卡片识别。
"""
import logging
import smtplib
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
    发送包含 ICS 日历邀请的邮件（iTIP REQUEST 格式）。

    Args:
        smtp_host: SMTP 服务器地址
        smtp_port: SMTP 端口
        user: 发件邮箱
        password: 发件密码/授权码
        recipient: 收件邮箱
        subject: 邮件主题
        body_text: 邮件正文
        ics_content: ICS 日历文件内容（必须包含 METHOD:REQUEST）
    """
    # 使用 alternative 结构：邮件客户端会优先渲染 calendar part
    msg = MIMEMultipart("alternative")
    msg["From"] = user
    msg["To"] = recipient
    msg["Subject"] = subject

    # Part 1: 纯文本正文（不支持日历解析的客户端会显示这段）
    text_part = MIMEText(body_text, "plain", "utf-8")
    msg.attach(text_part)

    # Part 2: ICS 日历内容（核心 - 触发日程卡片识别）
    # 使用 MIMEText 的 'calendar' 子类型，而非 MIMEBase
    cal_part = MIMEText(ics_content, "calendar", "utf-8")

    # 强制覆盖 Content-Type，确保包含 method=REQUEST 参数
    # 这是 QQ 邮箱和 Outlook 识别日历邀请的关键 Header
    cal_part.replace_header(
        "Content-Type",
        'text/calendar; charset="utf-8"; method=REQUEST',
    )

    # Content-Class: Outlook 系列邮箱用于识别日历消息的 Header
    cal_part.add_header("Content-Class", "urn:content-classes:calendarmessage")

    # Content-Disposition: 必须是 inline（内联），不能是 attachment（附件）
    # inline 才能让邮箱客户端直接解析日历内容并渲染卡片
    cal_part.add_header("Content-Disposition", "inline", filename="event.ics")

    msg.attach(cal_part)

    conn = smtplib.SMTP_SSL(smtp_host, smtp_port)
    try:
        conn.login(user, password)
        conn.sendmail(user, recipient, msg.as_string())
        logger.info("邮件已发送至 %s: %s", recipient, subject)
    finally:
        conn.quit()
