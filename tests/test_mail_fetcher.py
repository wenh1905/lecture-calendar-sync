"""mail_fetcher 模块测试"""
import imaplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from unittest.mock import MagicMock, patch

import pytest

from src.mail_fetcher import MailMessage, fetch_recent_mails


def _build_raw_email(subject: str, from_addr: str, body: str, charset: str = "utf-8") -> bytes:
    """构造一封原始邮件的 bytes"""
    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["Date"] = "Mon, 10 Mar 2026 14:00:00 +0800"
    msg.attach(MIMEText(body, "plain", charset))
    return msg.as_bytes()


class TestFetchRecentMails:
    """测试 IMAP 按日期获取邮件"""

    @patch("src.mail_fetcher.imaplib.IMAP4_SSL")
    def test_fetch_single_mail(self, mock_imap_cls: MagicMock) -> None:
        """正常获取一封邮件"""
        mock_conn = MagicMock()
        mock_imap_cls.return_value = mock_conn
        mock_conn.login.return_value = ("OK", [b"Logged in"])
        mock_conn.select.return_value = ("OK", [b"1"])
        mock_conn.search.return_value = ("OK", [b"1"])
        raw = _build_raw_email(
            subject="Physics Seminar: Quantum Optics",
            from_addr="research_phys@mail.tsinghua.edu.cn",
            body="Title: Quantum Optics\nTime: 2026-03-15 10:00\nLocation: Room 301",
        )
        mock_conn.fetch.return_value = ("OK", [(b"1 (RFC822 {1234})", raw)])

        results = fetch_recent_mails(
            host="mails.tsinghua.edu.cn",
            user="test@mails.tsinghua.edu.cn",
            password="secret",
            days=1,
        )

        assert len(results) == 1
        assert "Quantum Optics" in results[0].subject
        assert "Room 301" in results[0].body
        # readonly 模式不应标记已读
        mock_conn.store.assert_not_called()
        mock_conn.logout.assert_called_once()

    @patch("src.mail_fetcher.imaplib.IMAP4_SSL")
    def test_no_recent_mails(self, mock_imap_cls: MagicMock) -> None:
        """无邮件时返回空列表"""
        mock_conn = MagicMock()
        mock_imap_cls.return_value = mock_conn
        mock_conn.login.return_value = ("OK", [b"Logged in"])
        mock_conn.select.return_value = ("OK", [b"0"])
        mock_conn.search.return_value = ("OK", [b""])

        results = fetch_recent_mails(
            host="mails.tsinghua.edu.cn",
            user="test@mails.tsinghua.edu.cn",
            password="secret",
        )

        assert results == []

    @patch("src.mail_fetcher.imaplib.IMAP4_SSL")
    def test_gbk_encoded_mail(self, mock_imap_cls: MagicMock) -> None:
        """GBK 编码的中文邮件能正确解析"""
        mock_conn = MagicMock()
        mock_imap_cls.return_value = mock_conn
        mock_conn.login.return_value = ("OK", [b"Logged in"])
        mock_conn.select.return_value = ("OK", [b"1"])
        mock_conn.search.return_value = ("OK", [b"1"])
        raw = _build_raw_email(
            subject="物理系学术报告通知",
            from_addr="research_phys@mail.tsinghua.edu.cn",
            body="报告题目：量子光学前沿进展",
            charset="gbk",
        )
        mock_conn.fetch.return_value = ("OK", [(b"1 (RFC822 {1234})", raw)])

        results = fetch_recent_mails(
            host="mails.tsinghua.edu.cn",
            user="test@mails.tsinghua.edu.cn",
            password="secret",
        )

        assert len(results) == 1
        assert "量子光学" in results[0].body

    @patch("src.mail_fetcher.imaplib.IMAP4_SSL")
    def test_multiple_mails(self, mock_imap_cls: MagicMock) -> None:
        """获取多封邮件"""
        mock_conn = MagicMock()
        mock_imap_cls.return_value = mock_conn
        mock_conn.login.return_value = ("OK", [b"Logged in"])
        mock_conn.select.return_value = ("OK", [b"2"])
        mock_conn.search.return_value = ("OK", [b"1 2"])
        raw1 = _build_raw_email("Seminar A", "research_phys@mail.tsinghua.edu.cn", "Body A")
        raw2 = _build_raw_email("Seminar B", "research_phys@mail.tsinghua.edu.cn", "Body B")
        mock_conn.fetch.side_effect = [
            ("OK", [(b"1 (RFC822 {100})", raw1)]),
            ("OK", [(b"2 (RFC822 {100})", raw2)]),
        ]

        results = fetch_recent_mails(
            host="mails.tsinghua.edu.cn",
            user="test@mails.tsinghua.edu.cn",
            password="secret",
        )

        assert len(results) == 2
        # readonly 模式不标记已读
        mock_conn.store.assert_not_called()

    @patch("src.mail_fetcher.imaplib.IMAP4_SSL")
    def test_filters_by_sender_in_python(self, mock_imap_cls: MagicMock) -> None:
        """Python 层按发件人过滤，非目标发件人的邮件被排除"""
        mock_conn = MagicMock()
        mock_imap_cls.return_value = mock_conn
        mock_conn.login.return_value = ("OK", [b"Logged in"])
        mock_conn.select.return_value = ("OK", [b"2"])
        mock_conn.search.return_value = ("OK", [b"1 2"])
        raw_match = _build_raw_email("Seminar A", "research_phys@mail.tsinghua.edu.cn", "Body A")
        raw_other = _build_raw_email("Other", "someone@example.com", "Body B")
        mock_conn.fetch.side_effect = [
            ("OK", [(b"1 (RFC822 {100})", raw_match)]),
            ("OK", [(b"2 (RFC822 {100})", raw_other)]),
        ]

        results = fetch_recent_mails(
            host="mails.tsinghua.edu.cn",
            user="test@mails.tsinghua.edu.cn",
            password="secret",
        )

        assert len(results) == 1
        assert "Seminar A" in results[0].subject

    @patch("src.mail_fetcher.imaplib.IMAP4_SSL")
    def test_search_uses_since_date(self, mock_imap_cls: MagicMock) -> None:
        """验证搜索条件包含 SINCE 日期"""
        mock_conn = MagicMock()
        mock_imap_cls.return_value = mock_conn
        mock_conn.login.return_value = ("OK", [b"Logged in"])
        mock_conn.select.return_value = ("OK", [b"0"])
        mock_conn.search.return_value = ("OK", [b""])

        fetch_recent_mails(
            host="mails.tsinghua.edu.cn",
            user="test@mails.tsinghua.edu.cn",
            password="secret",
            days=3,
        )

        # 验证 IMAP 搜索只用 SINCE（不含 FROM，避免服务器索引延迟问题）
        search_call = mock_conn.search.call_args
        criteria = search_call[0][1]
        assert "SINCE" in criteria
        assert "FROM" not in criteria

    @patch("src.mail_fetcher.imaplib.IMAP4_SSL")
    def test_imap_error_raises(self, mock_imap_cls: MagicMock) -> None:
        """IMAP 连接失败应抛出异常"""
        mock_conn = MagicMock()
        mock_imap_cls.return_value = mock_conn
        mock_conn.login.side_effect = imaplib.IMAP4.error("auth failed")

        with pytest.raises(imaplib.IMAP4.error):
            fetch_recent_mails(
                host="mails.tsinghua.edu.cn",
                user="test@mails.tsinghua.edu.cn",
                password="wrong",
            )
