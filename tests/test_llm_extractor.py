"""llm_extractor 模块测试"""
import json
from unittest.mock import patch, MagicMock
import pytest

from src.llm_extractor import LectureInfo, extract_lecture_info


VALID_JSON_RESPONSE = json.dumps({
    "title": "Quantum Optics Frontiers",
    "start_time": "2026-03-15 10:00",
    "end_time": "2026-03-15 11:30",
    "location": "理科楼 C302",
    "speaker": "Prof. Zhang Wei",
    "summary": "Recent advances in quantum optics and photonics.",
    "is_relevant": True,
})


class TestExtractLectureInfo:
    """测试 LLM 信息提取"""

    @patch("src.llm_extractor.requests.post")
    def test_normal_json_response(self, mock_post: MagicMock) -> None:
        """LLM 返回正常 JSON"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": VALID_JSON_RESPONSE}}]
        }
        mock_post.return_value = mock_resp

        result = extract_lecture_info(
            mail_subject="Physics Seminar",
            mail_body="Quantum Optics talk on March 15",
            base_url="https://api.example.com/v1",
            api_key="test-key",
            model="deepseek-chat",
        )

        assert result is not None
        assert result.title == "Quantum Optics Frontiers"
        assert result.start_time == "2026-03-15 10:00"
        assert result.location == "理科楼 C302"
        assert result.is_relevant is True

    @patch("src.llm_extractor.requests.post")
    def test_json_wrapped_in_markdown(self, mock_post: MagicMock) -> None:
        """LLM 返回被 markdown 代码块包裹的 JSON"""
        wrapped = f"```json\n{VALID_JSON_RESPONSE}\n```"
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": wrapped}}]
        }
        mock_post.return_value = mock_resp

        result = extract_lecture_info(
            mail_subject="Seminar",
            mail_body="Some body",
            base_url="https://api.example.com/v1",
            api_key="test-key",
            model="deepseek-chat",
        )

        assert result is not None
        assert result.title == "Quantum Optics Frontiers"

    @patch("src.llm_extractor.requests.post")
    def test_invalid_response_returns_none(self, mock_post: MagicMock) -> None:
        """LLM 返回非 JSON 内容时返回 None"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "I cannot parse this email."}}]
        }
        mock_post.return_value = mock_resp

        result = extract_lecture_info(
            mail_subject="Seminar",
            mail_body="Some body",
            base_url="https://api.example.com/v1",
            api_key="test-key",
            model="deepseek-chat",
        )

        assert result is None

    @patch("src.llm_extractor.requests.post")
    def test_api_error_returns_none(self, mock_post: MagicMock) -> None:
        """API 请求失败时返回 None"""
        mock_post.side_effect = Exception("Connection timeout")

        result = extract_lecture_info(
            mail_subject="Seminar",
            mail_body="Some body",
            base_url="https://api.example.com/v1",
            api_key="test-key",
            model="deepseek-chat",
        )

        assert result is None

    @patch("src.llm_extractor.requests.post")
    def test_is_relevant_false(self, mock_post: MagicMock) -> None:
        """非相关领域讲座 is_relevant=false"""
        data = json.dumps({
            "title": "String Theory Workshop",
            "start_time": "2026-03-20 14:00",
            "end_time": "2026-03-20 15:30",
            "location": "理科楼 A101",
            "speaker": "Prof. Li Ming",
            "summary": "Introduction to string theory.",
            "is_relevant": False,
        })
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": data}}]
        }
        mock_post.return_value = mock_resp

        result = extract_lecture_info(
            mail_subject="String Theory",
            mail_body="Workshop on string theory",
            base_url="https://api.example.com/v1",
            api_key="test-key",
            model="deepseek-chat",
        )

        assert result is not None
        assert result.is_relevant is False
