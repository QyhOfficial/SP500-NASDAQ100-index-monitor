# Index Rebalance News Monitor

Automatically monitor S&P Global and Nasdaq index rebalance announcements via GitHub Actions. Sends Telegram notifications when new entries are detected.

## Monitored Sources

- **S&P Global**: S&P index constituent change announcements
- **Nasdaq IR**: Nasdaq index constituent change announcements

## Deployment

### 1. Create a Telegram Bot

1. Search for `@BotFather` in Telegram and send `/newbot`
2. Follow the prompts to set a name and get your **Bot Token** (format: `123456:ABC-DEF...`)
3. Get your **Chat ID**:
   - Send any message to your bot
   - Visit `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
   - Find `chat.id` in the returned JSON (positive for personal chats, negative for groups)

### 2. Create a GitHub Repository

1. Create a new repository on GitHub (public or private)
2. Push all files to the repository:

```bash
git init
git add .
git commit -m "init: index monitor"
git remote add origin https://github.com/<your-username>/<repo-name>.git
git push -u origin main
```

### 3. Configure Secrets

Go to **Settings → Secrets and variables → Actions** and add:

| Secret Name | Value |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Your Bot Token from BotFather |
| `TELEGRAM_CHAT_ID` | Your Chat ID |

### 4. Enable Actions

- Go to the **Actions** tab and confirm the workflow is enabled
- Click "Run workflow" to trigger a manual test run (first run only establishes a baseline, no notifications will be sent)
- After that, the workflow runs automatically every 30 minutes

## Notes

- **First run** does not send notifications — it only caches current page content as a baseline
- Cache files are stored in `cache/` and auto-committed by Actions
- GitHub Actions cron scheduling may have a few minutes of delay — this is normal
- If a page structure change causes parsing to fail, the script falls back to full-page hash comparison and alerts you to check manually
- Public repositories have unlimited Actions minutes; private repositories get 2,000 free minutes per month
