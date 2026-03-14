# Lecture Calendar Sync

自动从清华大学物理系学术报告邮件中提取讲座信息，生成 ICS 日历文件并发送到 QQ 邮箱，实现日程自动同步。

## 工作流程

1. IMAP 读取 `research_phys@mail.tsinghua.edu.cn` 的未读邮件
2. 调用 LLM API 提取讲座的主题、时间、地点、主讲人
3. 生成 `.ics` 日历文件（Asia/Shanghai 时区，确定性 UID 支持覆盖更新）
4. 通过 SMTP 发送带日历附件的邮件到 QQ 邮箱

与光谱学、低维半导体相关的讲座会在标题前加 ★ 标记。

## 部署

项目通过 GitHub Actions 每 2 小时自动运行，也支持手动触发。

### 环境变量（GitHub Secrets）

| 变量 | 说明 | 必填 |
|------|------|------|
| `IMAP_HOST` | IMAP 服务器（默认 mails.tsinghua.edu.cn） | 否 |
| `IMAP_USER` | 邮箱地址 | 是 |
| `IMAP_PASS` | 邮箱密码 | 是 |
| `SMTP_HOST` | SMTP 服务器（默认同 IMAP_HOST） | 否 |
| `SMTP_PORT` | SMTP 端口（默认 465） | 否 |
| `SMTP_USER` | 发件账号（默认同 IMAP_USER） | 否 |
| `SMTP_PASS` | 发件密码（默认同 IMAP_PASS） | 否 |
| `RECIPIENT_EMAIL` | QQ 邮箱地址 | 是 |
| `LLM_BASE_URL` | LLM API 地址 | 是 |
| `LLM_API_KEY` | LLM API Key | 是 |
| `LLM_MODEL` | 模型名称（默认 deepseek-chat） | 否 |

## 本地运行

```bash
pip install -r requirements.txt
python main.py
```

## 测试

```bash
pytest tests/ -v
```
