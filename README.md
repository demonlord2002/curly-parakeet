# Telegram MEGA File-to-Link Bot 🤖

This bot allows you to **forward/upload any file** in Telegram and get a **permanent MEGA download link**.  
Supports **multi-MEGA account rotation**, owner-only access, and Heroku deployment.

---

## Features

- Forward files → get MEGA direct download link ✅
- Supports documents, videos, and audio files ✅
- Multi-MEGA accounts rotation (up to 10 accounts) ✅
- Owner-only access for security ✅
- Heroku & VPS compatible ✅
- Premium inline buttons on `/start`:
  - Owner
  - Source Code
  - Support Channel

---

## Deploy to Heroku

Click the button below to deploy automatically:

[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy?template=https://github.com/demonlord2002/curly-parakeet)

---

### Heroku Config Vars

| Variable | Description | Example |
|----------|-------------|---------|
| `API_ID` | Telegram API ID | `1234567` |
| `API_HASH` | Telegram API HASH | `abcdef1234567890abcdef1234567890` |
| `BOT_TOKEN` | Bot token from BotFather | `1234567890:AAExxxxxxYourBotToken` |
| `OWNER_IDS` | Telegram user IDs allowed to use bot (comma-separated) | `123456789,987654321` |
| `MEGA_EMAILS` | MEGA account emails (comma-separated) | `mega1@example.com,mega2@example.com` |
| `MEGA_PASSWORDS` | Passwords of MEGA accounts (comma-separated, order must match emails) | `password1,password2` |

---

### Usage

1. Start the bot with `/start`  
2. Forward any file → the bot downloads and uploads it to MEGA  
3. Receive **permanent MEGA link** instantly  

---

### Buttons on /start

- **Owner** → `https://t.me/SunsetOfMe`  
- **Source Code** → `https://github.com/YourGitHubRepoHere`  
- **Support Channel** → `https://t.me/Fallen_Angels_Team`

---

### Requirements

- Python 3.11+  
- Dependencies in `requirements.txt`:

