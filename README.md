# 指数调整新闻监控

通过 GitHub Actions 自动监控 S&P Global 和 Nasdaq 的指数调整新闻，检测到新消息时通过 Telegram 推送通知。

## 监控目标

- **S&P Global**: 标普指数成分股调整公告
- **Nasdaq IR**: 纳斯达克指数成分股调整公告

## 部署步骤

### 1. 创建 Telegram Bot

1. 在 Telegram 中搜索 `@BotFather`，发送 `/newbot`
2. 按提示设置名称，获得 **Bot Token**（格式如 `123456:ABC-DEF...`）
3. 创建一个频道或群组（或直接给 Bot 发消息），然后获取 **Chat ID**：
   - 给 Bot 发一条消息
   - 访问 `https://api.telegram.org/bot<你的Token>/getUpdates`
   - 在返回的 JSON 中找到 `chat.id`（个人聊天是正数，群组是负数）

### 2. 创建 GitHub 仓库

1. 在 GitHub 创建一个新仓库（公开或私有均可）
2. 将本目录下所有文件推送到仓库：

```bash
git init
git add .
git commit -m "init: index monitor"
git remote add origin https://github.com/<你的用户名>/<仓库名>.git
git push -u origin main
```

### 3. 配置 Secrets

在仓库的 **Settings → Secrets and variables → Actions** 中添加：

| Secret 名称 | 值 |
|---|---|
| `TELEGRAM_BOT_TOKEN` | BotFather 给你的 Token |
| `TELEGRAM_CHAT_ID` | 你的 Chat ID |

### 4. 启用 Actions

- 进入仓库的 **Actions** 标签页，确认 workflow 已启用
- 点击 "Run workflow" 手动触发一次测试（首次运行只建立基线，不会发通知）
- 之后每 30 分钟自动运行

## 注意事项

- **首次运行**不会发送通知，仅缓存当前页面内容作为基线
- 缓存文件保存在 `cache/` 目录，由 Actions 自动提交
- GitHub Actions 的 cron 调度可能有几分钟的延迟，这是正常的
- 如果页面结构发生变化导致解析失败，脚本会回退到整页哈希比较，并提醒你手动查看
- 公开仓库的 Actions 分钟数无限制；私有仓库免费账户每月 2000 分钟
