"""mail_sender 模块测试"""
import smtplib
from email import message_from_bytes
from unittest.mock import MagicMock, patch
import pytest

from src.mail_sender import send_calendar_mail


class TestSendCalendarMail:
    """测试 SMTP 邮件发送"""

    @patch("src.mail_sender.smtplib.SMTP_SSL")
    def test_send_with_ics_attachment(self, mock_smtp_cls: MagicMock) -> None:
        """发送包含 ICS 附件的邮件"""
        mock_conn = MagicMock()
        mock_smtp_cls.return_value = mock_conn

        ics_content = "BEGIN:VCALENDAR\nEND:VCALENDAR"
        send_calendar_mail(
            smtp_host="mails.tsinghua.edu.cn",
            smtp_port=465,
            user="test@mails.tsinghua.edu.cn",
            password="secret",
            recipient="user@qq.com",
            subject="讲座日程: Quantum Optics",
            body_text="讲座: Quantum Optics\n时间: 2026-03-15 10:00",
            ics_content=ics_content,
        )

        mock_conn.login.assert_called_once_with("test@mails.tsinghua.edu.cn", "secret")
        mock_conn.sendmail.assert_called_once()
        # 检查发送的邮件内容
        call_args = mock_conn.sendmail.call_args
        raw_msg = call_args[0][2]  # 第三个参数是邮件内容
        msg = message_from_bytes(raw_msg.encode("utf-8") if isinstance(raw_msg, str) else raw_msg)

        # 验证 multipart/alternative 结构（iTIP 要求）
        assert msg.get_content_type() == "multipart/alternative"

        parts = list(msg.walk())
        # 找到 text/calendar part
        cal_parts = [p for p in parts if p.get_content_type() == "text/calendar"]
        assert len(cal_parts) == 1
        cal_part = cal_parts[0]
        # 验证 method=REQUEST 在 Content-Type 中
        assert "method" in cal_part["Content-Type"].lower()
        assert "REQUEST" in cal_part["Content-Type"]
        # 验证 Content-Class header
        assert cal_part["Content-Class"] == "urn:content-classes:calendarmessage"
        # 验证 Content-Disposition 是 inline 而非 attachment
        assert "inline" in cal_part["Content-Disposition"]

        mock_conn.quit.assert_called_once()

    @patch("src.mail_sender.smtplib.SMTP_SSL")
    def test_send_sets_correct_headers(self, mock_smtp_cls: MagicMock) -> None:
        """验证邮件头部正确设置"""
        mock_conn = MagicMock()
        mock_smtp_cls.return_value = mock_conn

        send_calendar_mail(
            smtp_host="mails.tsinghua.edu.cn",
            smtp_port=465,
            user="test@mails.tsinghua.edu.cn",
            password="secret",
            recipient="user@qq.com",
            subject="Test Subject",
            body_text="Test body",
            ics_content="BEGIN:VCALENDAR\nEND:VCALENDAR",
        )

        call_args = mock_conn.sendmail.call_args
        assert call_args[0][0] == "test@mails.tsinghua.edu.cn"  # from
        assert call_args[0][1] == "user@qq.com"  # to

    @patch("src.mail_sender.smtplib.SMTP_SSL")
    def test_smtp_error_propagates(self, mock_smtp_cls: MagicMock) -> None:
        """SMTP 连接失败时抛出异常"""
        mock_smtp_cls.side_effect = smtplib.SMTPConnectError(421, b"Service not available")

        with pytest.raises(smtplib.SMTPConnectError):
            send_calendar_mail(
                smtp_host="mails.tsinghua.edu.cn",
                smtp_port=465,
                user="test@mails.tsinghua.edu.cn",
                password="secret",
                recipient="user@qq.com",
                subject="Test",
                body_text="Test",
                ics_content="BEGIN:VCALENDAR\nEND:VCALENDAR",
            )
