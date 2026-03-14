"""ics_generator 模块测试"""
import os
import tempfile
import pytest

from icalendar import Calendar

from src.ics_generator import (
    load_calendar,
    make_event,
    make_uid,
    upsert_event,
    save_calendar,
)
from src.llm_extractor import LectureInfo


def _make_info(**kwargs) -> LectureInfo:
    """构造测试用 LectureInfo，支持覆盖默认值"""
    defaults = dict(
        title="Quantum Optics Frontiers",
        start_time="2026-03-15 10:00",
        end_time="2026-03-15 11:30",
        location="理科楼 C302",
        speaker="Prof. Zhang Wei",
        summary="Recent advances in quantum optics.",
        is_relevant=False,
    )
    defaults.update(kwargs)
    return LectureInfo(**defaults)


class TestLoadCalendar:
    """测试日历文件加载"""

    def test_file_not_exists(self, tmp_path) -> None:
        """文件不存在时返回新 Calendar"""
        cal = load_calendar(str(tmp_path / "nonexistent.ics"))
        assert cal is not None
        assert cal.get("version") == "2.0"
        assert cal.get("method") == "PUBLISH"

    def test_load_existing_file(self, tmp_path) -> None:
        """正常加载已有的 .ics 文件"""
        info = _make_info()
        cal = load_calendar(str(tmp_path / "new.ics"))
        event = make_event(info)
        cal.add_component(event)
        path = str(tmp_path / "test.ics")
        save_calendar(cal, path)

        loaded = load_calendar(path)
        events = list(loaded.walk("VEVENT"))
        assert len(events) == 1

    def test_corrupted_file(self, tmp_path) -> None:
        """损坏的文件返回新 Calendar"""
        path = tmp_path / "bad.ics"
        path.write_text("THIS IS NOT A VALID ICS FILE")

        cal = load_calendar(str(path))
        assert cal is not None
        assert cal.get("version") == "2.0"


class TestMakeEvent:
    """测试事件构造"""

    def test_basic_event(self) -> None:
        """构造基本事件"""
        info = _make_info()
        event = make_event(info)

        assert "Quantum Optics Frontiers" in str(event.get("summary"))
        assert "理科楼 C302" in str(event.get("location"))

    def test_relevant_event_has_star(self) -> None:
        """is_relevant=True 时标题前加 ★"""
        info = _make_info(title="2D Semiconductor Spectroscopy", is_relevant=True)
        event = make_event(info)

        assert str(event.get("summary")).startswith("★")

    def test_non_relevant_no_star(self) -> None:
        """is_relevant=False 时无 ★"""
        info = _make_info(is_relevant=False)
        event = make_event(info)

        assert "★" not in str(event.get("summary"))

    def test_uid_deterministic(self) -> None:
        """相同 title+start_time 生成相同 UID"""
        info = _make_info()
        assert make_uid(info) == make_uid(info)

    def test_timezone_asia_shanghai(self) -> None:
        """时间应使用 Asia/Shanghai 时区"""
        info = _make_info()
        event = make_event(info)
        dtstart = event.get("dtstart").dt
        assert str(dtstart.tzinfo) == "Asia/Shanghai"


class TestUpsertEvent:
    """测试去重与覆盖"""

    def test_add_new_event(self) -> None:
        """添加新事件"""
        cal = load_calendar("/nonexistent")
        info = _make_info()
        event = make_event(info)
        upsert_event(cal, event)

        events = list(cal.walk("VEVENT"))
        assert len(events) == 1

    def test_duplicate_uid_overwrites(self) -> None:
        """相同 UID 的事件会被覆盖"""
        cal = load_calendar("/nonexistent")

        info1 = _make_info(location="Room A")
        event1 = make_event(info1)
        upsert_event(cal, event1)

        # 同 title+start_time，不同 location
        info2 = _make_info(location="Room B")
        event2 = make_event(info2)
        upsert_event(cal, event2)

        events = list(cal.walk("VEVENT"))
        assert len(events) == 1
        assert "Room B" in str(events[0].get("location"))

    def test_different_events_both_kept(self) -> None:
        """不同 UID 的事件都保留"""
        cal = load_calendar("/nonexistent")

        info1 = _make_info(title="Talk A", start_time="2026-03-15 10:00")
        info2 = _make_info(title="Talk B", start_time="2026-03-16 14:00")
        upsert_event(cal, make_event(info1))
        upsert_event(cal, make_event(info2))

        events = list(cal.walk("VEVENT"))
        assert len(events) == 2


class TestSaveCalendar:
    """测试日历保存"""

    def test_save_and_reload(self, tmp_path) -> None:
        """保存后能正确重新加载"""
        cal = load_calendar("/nonexistent")
        upsert_event(cal, make_event(_make_info(title="Talk 1")))
        upsert_event(cal, make_event(_make_info(title="Talk 2", start_time="2026-04-01 09:00")))

        path = str(tmp_path / "out.ics")
        save_calendar(cal, path)

        reloaded = load_calendar(path)
        events = list(reloaded.walk("VEVENT"))
        assert len(events) == 2
