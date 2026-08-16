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

### 2. Set Up the Repository

**Option A: Fork this repository**

1. Click the **Fork** button at the top right of this page
2. In your forked repository, go to **Settings → Actions → General**, and set **Workflow permissions** to **Read and write permissions**

**Option B: Create a new repository from scratch**

1. Create a new repository on GitHub (public or private)
2. Clone and push all files:

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

### 4. (Optional) Delete Existing Cache Files

The repository includes pre-existing cache files in the `cache/` directory. If you keep them, you will not receive any notifications until the next index rebalance announcement is published. To receive an initial notification for testing purposes, delete `cache/spglobal.json` and `cache/nasdaq.json` from your repository before the first run.

### 5. Enable Actions

- Go to the **Actions** tab and confirm the workflow is enabled
- Click "Run workflow" to trigger a manual test run
- After that, the workflow runs automatically every 30 minutes

## Notes

- **First run** does not send notifications — it only caches current page content as a baseline
- Cache files are stored in `cache/` and auto-committed by Actions
- GitHub Actions cron scheduling may have a few minutes of delay — this is normal
- If a page structure change causes parsing to fail, the script falls back to full-page hash comparison and alerts you to check manually
- Public repositories have unlimited Actions minutes; private repositories get 2,000 free minutes per month
