"""ICS 日历生成模块 - 维护全局 lectures.ics 文件，支持追加与去重"""
import hashlib
import logging
from datetime import datetime
from pathlib import Path

import pytz
from icalendar import Calendar, Event

from src.llm_extractor import LectureInfo

logger = logging.getLogger(__name__)

TIMEZONE = pytz.timezone("Asia/Shanghai")


def _init_calendar() -> Calendar:
    """初始化一个空的 Calendar 对象"""
    cal = Calendar()
    cal.add("prodid", "-//ReportAutoCal//Lecture Calendar//CN")
    cal.add("version", "2.0")
    # 订阅模式使用 PUBLISH
    cal.add("method", "PUBLISH")
    cal.add("x-wr-calname", "清华物理系学术报告")
    cal.add("x-wr-timezone", "Asia/Shanghai")
    return cal


def load_calendar(path: str) -> Calendar:
    """
    读取现有 .ics 文件，文件不存在或损坏则返回新的 Calendar。

    Args:
        path: .ics 文件路径

    Returns:
        Calendar 对象
    """
    p = Path(path)
    if not p.exists():
        logger.info("日历文件不存在，初始化新日历: %s", path)
        return _init_calendar()

    try:
        raw = p.read_bytes()
        cal = Calendar.from_ical(raw)
        logger.info("已加载现有日历: %s (%d 个事件)", path, len(list(cal.walk("VEVENT"))))
        return cal
    except Exception as e:
        logger.warning("日历文件损坏，重新初始化: %s (%s)", path, e)
        return _init_calendar()


def make_uid(info: LectureInfo) -> str:
    """根据讲座标题和开始时间生成确定性 UID"""
    uid_hash = hashlib.md5(f"{info.title}_{info.start_time}".encode()).hexdigest()
    return f"{uid_hash}@reportautocal"


def make_event(info: LectureInfo) -> Event:
    """
    从 LectureInfo 构造一个 iCalendar Event。

    Args:
        info: 提取的讲座信息

    Returns:
        Event 对象
    """
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

    # 确定性 UID：相同讲座生成相同 UID，支持覆盖更新
    event.add("uid", make_uid(info))

    logger.info("已构造事件: %s (%s)", title, info.start_time)
    return event


def upsert_event(cal: Calendar, event: Event) -> None:
    """
    按 UID 去重：存在则覆盖，不存在则追加。

    Args:
        cal: 全局 Calendar 对象
        event: 待插入/更新的 Event
    """
    new_uid = str(event.get("uid"))

    # 查找并移除同 UID 的旧事件
    to_remove = []
    for component in cal.subcomponents:
        if component.name == "VEVENT" and str(component.get("uid")) == new_uid:
            to_remove.append(component)

    for old in to_remove:
        cal.subcomponents.remove(old)
        logger.info("已覆盖旧事件: UID=%s", new_uid)

    cal.add_component(event)


def save_calendar(cal: Calendar, path: str) -> None:
    """
    将 Calendar 对象序列化并写入文件。

    Args:
        cal: Calendar 对象
        path: 输出文件路径
    """
    Path(path).write_bytes(cal.to_ical())
    event_count = len(list(cal.walk("VEVENT")))
    logger.info("日历已保存: %s (%d 个事件)", path, event_count)
