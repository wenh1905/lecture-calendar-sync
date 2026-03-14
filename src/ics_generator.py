"""ICS 日历生成模块 - 将讲座信息转换为 .ics 日历文件"""
import hashlib
import logging
from datetime import datetime

import pytz
from icalendar import Calendar, Event, vText

from src.llm_extractor import LectureInfo

logger = logging.getLogger(__name__)

TIMEZONE = pytz.timezone("Asia/Shanghai")


def generate_ics(info: LectureInfo) -> str:
    """
    根据讲座信息生成 ICS 日历文件内容。

    Args:
        info: 提取的讲座信息

    Returns:
        ICS 文件内容字符串
    """
    cal = Calendar()
    cal.add("prodid", "-//ReportAutoCal//Lecture Calendar//CN")
    cal.add("version", "2.0")
    cal.add("method", "REQUEST")

    event = Event()

    # 相关领域讲座标题前加 ★
    title = f"★{info.title}" if info.is_relevant else info.title
    event.add("summary", title)

    # 解析时间并绑定 Asia/Shanghai 时区
    start_dt = TIMEZONE.localize(datetime.strptime(info.start_time, "%Y-%m-%d %H:%M"))
    end_dt = TIMEZONE.localize(datetime.strptime(info.end_time, "%Y-%m-%d %H:%M"))
    event.add("dtstart", start_dt)
    event.add("dtend", end_dt)

    event.add("location", info.location)
    event.add("description", f"主讲人: {info.speaker}\n\n{info.summary}")

    # 确定性 UID：相同讲座生成相同 UID，支持日程覆盖更新
    uid_hash = hashlib.md5(f"{info.title}_{info.start_time}".encode()).hexdigest()
    event.add("uid", f"{uid_hash}@reportautocal")

    cal.add_component(event)

    logger.info("已生成 ICS 事件: %s (%s)", title, info.start_time)

    ics_str = cal.to_ical().decode("utf-8")

    # 强制确保 METHOD:REQUEST 存在（iTIP 标准要求）
    # 部分库可能输出 METHOD:PUBLISH 或不输出 METHOD
    if "METHOD:PUBLISH" in ics_str:
        ics_str = ics_str.replace("METHOD:PUBLISH", "METHOD:REQUEST")
    elif "METHOD:" not in ics_str:
        ics_str = ics_str.replace("BEGIN:VCALENDAR\r\n", "BEGIN:VCALENDAR\r\nMETHOD:REQUEST\r\n")

    return ics_str
