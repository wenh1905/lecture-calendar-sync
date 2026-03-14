"""LLM 信息提取模块 - 调用大模型 API 从邮件中提取讲座信息"""
import json
import logging
import re
from dataclasses import dataclass
from typing import Optional

import requests

logger = logging.getLogger(__name__)


@dataclass
class LectureInfo:
    """提取的讲座信息"""
    title: str
    start_time: str  # YYYY-MM-DD HH:MM
    end_time: str     # YYYY-MM-DD HH:MM
    location: str
    speaker: str
    summary: str
    is_relevant: bool  # 是否与光谱学/低维半导体相关


# System prompt for LLM
SYSTEM_PROMPT = """你是一个学术日程提取助手。你的任务是从清华大学物理系的学术报告通知邮件中提取讲座信息。

背景信息：
- 邮件来自清华大学物理系 (research_phys@mail.tsinghua.edu.cn)
- 时间通常为北京时间 (Asia/Shanghai, UTC+8)
- 如果邮件中只给出了开始时间没有结束时间，默认讲座时长为 1.5 小时

请严格以如下 JSON 格式输出，不要输出任何其他内容：
{"title": "讲座标题", "start_time": "YYYY-MM-DD HH:MM", "end_time": "YYYY-MM-DD HH:MM", "location": "地点", "speaker": "主讲人", "summary": "一句话摘要", "is_relevant": true/false}

is_relevant 字段说明：如果讲座内容与以下领域相关，设为 true，否则设为 false：
- 光谱学 (spectroscopy)，包括各类光谱技术
- 低维半导体 (low-dimensional semiconductors)，包括二维材料、量子点、纳米线等"""


def _parse_json_response(text: str) -> Optional[dict]:
    """
    从 LLM 响应中解析 JSON，支持 markdown 代码块包裹的情况。

    Args:
        text: LLM 原始响应文本

    Returns:
        解析后的字典，失败返回 None
    """
    # 先尝试直接解析
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    # 尝试从 markdown 代码块中提取
    md_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if md_match:
        try:
            return json.loads(md_match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # 最后兜底：正则提取第一个 JSON 对象
    json_match = re.search(r"\{.*\}", text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass

    return None


def extract_lecture_info(
    mail_subject: str,
    mail_body: str,
    base_url: str,
    api_key: str,
    model: str = "deepseek-chat",
) -> Optional[LectureInfo]:
    """
    调用 LLM API 从邮件内容中提取讲座信息。

    Args:
        mail_subject: 邮件主题
        mail_body: 邮件正文
        base_url: LLM API base URL
        api_key: API Key
        model: 模型名称

    Returns:
        LectureInfo 或 None（解析失败时）
    """
    user_content = f"邮件主题：{mail_subject}\n\n邮件正文：\n{mail_body}"

    try:
        resp = requests.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                "temperature": 0.1,
            },
            timeout=30,
        )
        resp.raise_for_status()

        content = resp.json()["choices"][0]["message"]["content"]
        logger.info("LLM 原始响应: %s", content[:200])

        data = _parse_json_response(content)
        if data is None:
            logger.warning("无法从 LLM 响应中解析 JSON，跳过该邮件")
            return None

        required_keys = {"title", "start_time", "end_time", "location", "speaker", "summary"}
        if not required_keys.issubset(data.keys()):
            logger.warning("JSON 缺少必要字段: %s", required_keys - data.keys())
            return None

        return LectureInfo(
            title=data["title"],
            start_time=data["start_time"],
            end_time=data["end_time"],
            location=data["location"],
            speaker=data["speaker"],
            summary=data["summary"],
            is_relevant=bool(data.get("is_relevant", False)),
        )

    except Exception as e:
        logger.error("LLM 提取失败: %s", e)
        return None
