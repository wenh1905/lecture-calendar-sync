"""主调度器 - 串联邮件获取、LLM 提取、全局日历更新"""
import logging
import os
import sys

from src.mail_fetcher import fetch_recent_mails
from src.llm_extractor import extract_lecture_info
from src.ics_generator import load_calendar, make_event, upsert_event, save_calendar

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

ICS_PATH = "lectures.ics"


def main() -> None:
    # 从环境变量读取配置
    imap_host = os.environ.get("IMAP_HOST") or "mails.tsinghua.edu.cn"
    imap_user = os.environ["IMAP_USER"]
    imap_pass = os.environ["IMAP_PASS"]
    imap_folder = os.environ.get("IMAP_FOLDER") or "INBOX"

    llm_base_url = os.environ["LLM_BASE_URL"]
    llm_api_key = os.environ["LLM_API_KEY"]
    llm_model = os.environ.get("LLM_MODEL") or "deepseek-chat"

    # Step 1: 获取近 1 天内所有邮件（不限已读/未读，靠 UID 去重）
    logger.info("=== 开始获取近 1 天邮件 ===")
    mails = fetch_recent_mails(
        host=imap_host, user=imap_user, password=imap_pass,
        days=1, folder=imap_folder,
    )
    if not mails:
        logger.info("没有新的学术报告邮件，退出")
        return

    logger.info("共获取 %d 封邮件，开始处理", len(mails))

    # Step 2: 加载现有日历
    cal = load_calendar(ICS_PATH)

    success_count = 0
    for mail in mails:
        try:
            # Step 3: LLM 提取讲座信息
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

            # Step 4: 构造事件并 upsert 到全局日历
            event = make_event(info)
            upsert_event(cal, event)
            success_count += 1

        except Exception as e:
            logger.error("处理邮件失败 [%s]: %s", mail.subject, e)
            continue

    # Step 5: 保存日历文件
    save_calendar(cal, ICS_PATH)
    logger.info("=== 完成: 成功处理 %d/%d 封邮件 ===", success_count, len(mails))


if __name__ == "__main__":
    main()
