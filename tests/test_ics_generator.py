"""ics_generator 模块测试"""
import pytest

from src.ics_generator import generate_ics
from src.llm_extractor import LectureInfo


class TestGenerateICS:
    """测试 ICS 日历生成"""

    def test_basic_event(self) -> None:
        """生成基本的 ICS 事件"""
        info = LectureInfo(
            title="Quantum Optics Frontiers",
            start_time="2026-03-15 10:00",
            end_time="2026-03-15 11:30",
            location="理科楼 C302",
            speaker="Prof. Zhang Wei",
            summary="Recent advances in quantum optics.",
            is_relevant=False,
        )

        ics_text = generate_ics(info)

        assert "BEGIN:VCALENDAR" in ics_text
        assert "BEGIN:VEVENT" in ics_text
        assert "Quantum Optics Frontiers" in ics_text
        assert "理科楼 C302" in ics_text
        assert "END:VCALENDAR" in ics_text

    def test_relevant_event_has_star(self) -> None:
        """is_relevant=True 时标题前加 ★"""
        info = LectureInfo(
            title="Low-dimensional Semiconductor Spectroscopy",
            start_time="2026-03-20 14:00",
            end_time="2026-03-20 15:30",
            location="理科楼 A101",
            speaker="Prof. Li Ming",
            summary="Spectroscopy of 2D materials.",
            is_relevant=True,
        )

        ics_text = generate_ics(info)

        assert "★Low-dimensional Semiconductor Spectroscopy" in ics_text

    def test_non_relevant_event_no_star(self) -> None:
        """is_relevant=False 时标题无 ★"""
        info = LectureInfo(
            title="String Theory Workshop",
            start_time="2026-03-20 14:00",
            end_time="2026-03-20 15:30",
            location="理科楼 A101",
            speaker="Prof. Li Ming",
            summary="String theory intro.",
            is_relevant=False,
        )

        ics_text = generate_ics(info)

        assert "★" not in ics_text
        assert "String Theory Workshop" in ics_text

    def test_uid_deterministic(self) -> None:
        """相同 title+start_time 生成相同 UID"""
        info = LectureInfo(
            title="Test Talk",
            start_time="2026-04-01 09:00",
            end_time="2026-04-01 10:00",
            location="Room 101",
            speaker="Speaker",
            summary="Summary",
            is_relevant=False,
        )

        ics1 = generate_ics(info)
        ics2 = generate_ics(info)

        # 提取 UID 行
        uid_lines_1 = [l for l in ics1.splitlines() if l.startswith("UID:")]
        uid_lines_2 = [l for l in ics2.splitlines() if l.startswith("UID:")]
        assert len(uid_lines_1) == 1
        assert uid_lines_1 == uid_lines_2

    def test_timezone_asia_shanghai(self) -> None:
        """时间应使用 Asia/Shanghai 时区"""
        info = LectureInfo(
            title="TZ Test",
            start_time="2026-03-15 10:00",
            end_time="2026-03-15 11:00",
            location="Room",
            speaker="Speaker",
            summary="Summary",
            is_relevant=False,
        )

        ics_text = generate_ics(info)

        # ICS 中应包含 Asia/Shanghai 时区标识
        assert "Asia/Shanghai" in ics_text
