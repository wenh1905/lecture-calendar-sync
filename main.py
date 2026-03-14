"""主调度器 - 串联邮件获取、LLM 提取、ICS 生成、邮件发送"""
import logging
import os
import sys

from src.mail_fetcher import fetch_unseen_mails
from src.llm_extractor import extract_lecture_info
from src.ics_generator import generate_ics
from src.mail_sender import send_calendar_mail

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


def main() -> None:
    # 从环境变量读取配置
    imap_host = os.environ.get("IMAP_HOST", "mails.tsinghua.edu.cn")
    imap_user = os.environ["IMAP_USER"]
    imap_pass = os.environ["IMAP_PASS"]

    smtp_host = os.environ.get("SMTP_HOST", "mails.tsinghua.edu.cn")
    smtp_port = int(os.environ.get("SMTP_PORT", "465"))
    smtp_user = os.environ.get("SMTP_USER", imap_user)
    smtp_pass = os.environ.get("SMTP_PASS", imap_pass)

    recipient = os.environ["RECIPIENT_EMAIL"]

    llm_base_url = os.environ["LLM_BASE_URL"]
    llm_api_key = os.environ["LLM_API_KEY"]
    llm_model = os.environ.get("LLM_MODEL", "deepseek-chat")

    # Step 1: 获取未读邮件
    logger.info("=== 开始获取未读邮件 ===")
    mails = fetch_unseen_mails(host=imap_host, user=imap_user, password=imap_pass)
    if not mails:
        logger.info("没有新的学术报告邮件，退出")
        return

    logger.info("共获取 %d 封邮件，开始处理", len(mails))

    success_count = 0
    for mail in mails:
        try:
            # Step 2: LLM 提取讲座信息
            logger.info("--- 处理邮件: %s ---", mail.subject)
            info = extract_lecture_info(
                mail_subject=mail.subject,
                mail_body=mail.body,
                base_url=llm_base_url,
                api_key=llm_api_key,
                model=llm_model,
            )
            if info is None:
                logger.warning("未能提取讲座信息，跳过: %s", mail.subject)
                continue

            # Step 3: 生成 ICS
            ics_content = generate_ics(info)

            # Step 4: 发送邮件
            star = "★" if info.is_relevant else ""
            email_subject = f"讲座日程: {star}{info.title}"
            body_text = (
                f"讲座: {star}{info.title}\n"
                f"主讲人: {info.speaker}\n"
                f"时间: {info.start_time} ~ {info.end_time}\n"
                f"地点: {info.location}\n\n"
                f"{info.summary}"
            )

            send_calendar_mail(
                smtp_host=smtp_host,
                smtp_port=smtp_port,
                user=smtp_user,
                password=smtp_pass,
                recipient=recipient,
                subject=email_subject,
                body_text=body_text,
                ics_content=ics_content,
            )
            success_count += 1

        except Exception as e:
            logger.error("处理邮件失败 [%s]: %s", mail.subject, e)
            continue

    logger.info("=== 完成: 成功处理 %d/%d 封邮件 ===", success_count, len(mails))


if __name__ == "__main__":
    main()
