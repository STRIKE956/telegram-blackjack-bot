# telegram-blackjack-bot

Telegram Blackjack bot with STRIKECOINS and Solana devnet wallets.

**Play:** https://t.me/StrikeBlackJackBot

## Deploy on Render (24/7 hosting)

1. Push this repo to GitHub (already at `STRIKE956/telegram-blackjack-bot`).
2. Go to [render.com](https://render.com) → **New** → **Blueprint**.
3. Connect GitHub and select this repository.
4. Set environment variable **`TELEGRAM_BOT_TOKEN`** (from @BotFather).
5. Deploy. Render runs the **worker** from `render.yaml` (Docker).
6. **Stop any local copy** of the bot — only one instance may poll Telegram.

## Run locally

```bash
export TELEGRAM_BOT_TOKEN="your-token"
pip install -r requirements.txt
python bot.py
```
