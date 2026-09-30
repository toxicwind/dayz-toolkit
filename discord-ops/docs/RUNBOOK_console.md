# Runbook: DayZ Discord Ops (Xbox/Console Edition)

> **Platform**: Xbox (Nitrado Hosted)
> **Mode**: Console Restrictions Enabled

## 🚨 Critical Limitations
This bot is configured for **Xbox**, which lacks many PC features.
1.  **NO RCON**: You cannot kick, ban, or message players from Discord. Use A2S + FTP log review instead.
2.  **NO Real-time Logs**: Logs are delayed (via Webinterface). Data is not instant.
3.  **NO Auto-Restart**: The bot cannot restart the server (requires Nitrado Webinterface).

## 🚀 How to Run
Ensure your `.env` is loaded.

```bash
# 1. Start the bot
python3 -m bot.bot
```

## 🛠 Troubleshooting

### "Bot is online but stats are 0/0"
- **Cause**: Nitrado A2S (Query) port often times out.
- **Fix**: Wait. The bot retries. If it persists >10 mins, check if Nitrado server is actually running.

### "Logs are empty"
- **Cause**: Webinterface scraping is delayed or failed auth.
- **Check**: Run the probe to verify access.
  ```bash
  python3 tools/platform_probe.py
  ```
  - Look for `"ftp": "connected_tls"`. If failed, your Nitrado creds are wrong.

### "RCON not supported" error
- **Cause**: Any legacy RCON command path.
- **Fix**: Not available on console builds; manage via Nitrado panel or A2S/FTP data.

## ⚙️ Configuration
The bot uses `config/ezstreet.yaml`.
- **Platform**: `platform: xbox` (DO NOT CHANGE)
- **Creds**: Mapped to `DAYZ_*` environment variables.
