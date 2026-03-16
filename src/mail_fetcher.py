"""邮件获取模块 - 通过 IMAP 读取清华物理系学术报告邮件"""
import email
import email.message
import imaplib
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from email.header import decode_header
from typing import Optional

logger = logging.getLogger(__name__)

# 目标发件人
TARGET_SENDER = "research_phys@mail.tsinghua.edu.cn"


@dataclass
class MailMessage:
    """解析后的邮件数据"""
    subject: str
    sender: str
    date: str
    body: str
    uid: str  # IMAP 邮件序号，用于标记已读


def _decode_header_value(raw: str) -> str:
    """解码邮件头部（支持 RFC 2047 编码）"""
    parts = decode_header(raw)
    decoded = []
    for content, charset in parts:
        if isinstance(content, bytes):
            decoded.append(content.decode(charset or "utf-8", errors="replace"))
        else:
            decoded.append(content)
    return "".join(decoded)


def _extract_text_body(msg: email.message.Message) -> str:
    """从邮件中提取纯文本正文，支持多种编码"""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    return payload.decode(charset, errors="replace")
        return ""
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            return payload.decode(charset, errors="replace")
        return ""


def fetch_recent_mails(
    host: str,
    user: str,
    password: str,
    days: int = 1,
    port: int = 993,
    sender: str = TARGET_SENDER,
) -> list[MailMessage]:
    """
    获取过去 N 天内指定发件人的所有邮件（不限已读/未读，readonly 不修改邮件状态）。

    去重由下游 ics_generator 的 UID 机制保证。

    Args:
        host: IMAP 服务器地址
        user: 邮箱账号
        password: 邮箱密码
        days: 回溯天数 (默认 1)
        port: IMAP 端口 (默认 993)
        sender: 目标发件人地址

    Returns:
        解析后的邮件列表
    """
    conn: Optional[imaplib.IMAP4_SSL] = None
    results: list[MailMessage] = []

    since_date = (datetime.now() - timedelta(days=days)).strftime("%d-%b-%Y")

    try:
        conn = imaplib.IMAP4_SSL(host, port)
        conn.login(user, password)
        logger.info("IMAP 登录成功: %s", user)

        conn.select("INBOX", readonly=True)
        search_criteria = f'(FROM "{sender}" SINCE {since_date})'
        status, data = conn.search(None, search_criteria)

        if status != "OK" or not data[0]:
            logger.info("过去 %d 天内无来自 %s 的邮件", days, sender)
            return results

        mail_ids = data[0].split()
        logger.info("找到 %d 封邮件（过去 %d 天）", len(mail_ids), days)

        for mid in mail_ids:
            mid_str = mid.decode() if isinstance(mid, bytes) else mid
            try:
                status, msg_data = conn.fetch(mid, "(RFC822)")
                if status != "OK" or not msg_data[0]:
                    continue

                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)

                mail = MailMessage(
                    subject=_decode_header_value(msg.get("Subject", "")),
                    sender=msg.get("From", ""),
                    date=msg.get("Date", ""),
                    body=_extract_text_body(msg),
                    uid=mid_str,
                )
                results.append(mail)
                logger.info("已读取邮件: %s", mail.subject)

            except Exception as e:
                logger.error("读取邮件 %s 失败: %s", mid_str, e)
                continue

    except imaplib.IMAP4.error as e:
        logger.error("IMAP 连接/认证失败: %s", e)
        raise
    finally:
        if conn:
            try:
                conn.logout()
            except Exception:
                pass

    return results
