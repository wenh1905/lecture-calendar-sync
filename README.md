# Lecture Calendar Sync

自动从清华大学物理系学术报告邮件中提取讲座信息，维护全局 `lectures.ics` 日历文件并托管在 GitHub 仓库中，通过 URL 订阅实现日程无感同步。

## 工作流程

1. IMAP 连接邮箱，获取近 1 天内所有邮件（readonly 模式，不修改邮件状态）
2. Python 层按发件人 `research_phys@mail.tsinghua.edu.cn` 过滤
3. 调用 LLM API 提取讲座的主题、时间、地点、主讲人及摘要
4. 按 UID（MD5 of 标题+时间）去重，追加或覆盖更新到全局 `lectures.ics`
5. GitHub Actions 自动 commit 更新后的日历文件

与光谱学、低维半导体相关的讲座会在标题前加 ★ 标记。

## 日历订阅

Actions 运行后，通过以下 URL 在任意日历客户端订阅：

```
https://raw.githubusercontent.com/wenh1905/lecture-calendar-sync/main/lectures.ics
```

## 部署

项目通过 GitHub Actions 每 2 小时自动运行，也支持手动触发。

### 环境变量（GitHub Secrets）

| 变量 | 说明 | 必填 |
|------|------|------|
| `IMAP_HOST` | IMAP 服务器（默认 `mails.tsinghua.edu.cn`） | 否 |
| `IMAP_USER` | 邮箱地址 | 是 |
| `IMAP_PASS` | 邮箱密码 | 是 |
| `IMAP_FOLDER` | IMAP 文件夹名（默认 `INBOX`，如有服务器分类规则需指定实际文件夹） | 否 |
| `LLM_BASE_URL` | LLM API 地址 | 是 |
| `LLM_API_KEY` | LLM API Key | 是 |
| `LLM_MODEL` | 模型名称（默认 `deepseek-chat`） | 否 |

> **注意**：如果邮箱服务器有自动分类规则，报告邮件可能不在 INBOX 中。需要通过 IMAP 客户端确认实际文件夹名称，并设置 `IMAP_FOLDER`（文件夹名使用 IMAP modified UTF-7 编码）。

## 本地运行

```bash
pip install -r requirements.txt
# 配置 .env 文件后运行
python main.py
```

## 测试

```bash
pytest tests/ -v
```
