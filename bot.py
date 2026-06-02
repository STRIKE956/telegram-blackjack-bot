import asyncio
import json
import logging
import os
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import solana_wallet
import storage

logging.basicConfig(level=logging.INFO)

CURRENCY_NAME = "STRIKECOINS"
STARTING_STRIKECOINS = 1000
DEFAULT_BET = 100
WEBAPP_URL = os.environ.get(
    "WEBAPP_URL",
    "https://strike956.github.io/telegram-blackjack-bot/",
)


def wallet_connect_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "🔗 Connect Telegram Wallet",
            web_app=WebAppInfo(url=WEBAPP_URL),
        )]
    ])

class BlackjackGame:
    def __init__(self):
        self.deck = [2,3,4,5,6,7,8,9,10,10,10,10,11] * 4
        random.shuffle(self.deck)

    def deal(self):
        return self.deck.pop()

    def hand_value(self, hand):
        value = sum(hand)
        aces = hand.count(11)
        while value > 21 and aces > 0:
            value -= 10
            aces -= 1
        return value

# Active hands in memory; STRIKECOINS persisted in SQLite (storage.py)
users = {}  # user_id: {"strikecoins": int, "current_game": None|dict}

def format_coins(amount: int) -> str:
    return f"{amount:,} {CURRENCY_NAME}"

def get_user(user_id: int) -> dict:
    if user_id not in users:
        users[user_id] = {
            "strikecoins": storage.get_strikecoins(user_id),
            "current_game": None,
        }
    elif "balance" in users[user_id]:
        users[user_id]["strikecoins"] = users[user_id].pop("balance")
        storage.set_strikecoins(user_id, users[user_id]["strikecoins"])
    return users[user_id]


def save_strikecoins(user_id: int, amount: int) -> None:
    users[user_id]["strikecoins"] = amount
    storage.set_strikecoins(user_id, amount)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    await update.message.reply_text(
        f"Welcome to Blackjack, {update.effective_user.first_name}!\n\n"
        f"🪙 In-game currency: **{CURRENCY_NAME}**\n"
        f"Balance: {format_coins(user['strikecoins'])}\n\n"
        "/play [amount] — bet STRIKECOINS\n"
        "/balance — STRIKECOINS balance\n"
        "/connect — link **Telegram Wallet** (TON)\n"
        "/ton\\_wallet — view linked TON address\n"
        "/wallet — Solana devnet (separate)\n"
        "/help — rules & commands",
        reply_markup=wallet_connect_keyboard(),
        parse_mode="Markdown",
    )

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    await update.message.reply_text(f"🪙 {format_coins(user['strikecoins'])}")

async def connect_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Tap the button to open the Mini App and connect "
        "**Telegram Wallet** or any TON wallet via TON Connect.",
        reply_markup=wallet_connect_keyboard(),
        parse_mode="Markdown",
    )


async def ton_wallet_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    address = storage.get_ton_wallet(user_id)
    if not address:
        await update.message.reply_text(
            "No Telegram Wallet linked yet. Use /connect.",
            reply_markup=wallet_connect_keyboard(),
        )
        return
    await update.message.reply_text(
        f"◎ **Telegram Wallet (TON)**\n\n`{address}`",
        parse_mode="Markdown",
    )


async def on_web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        data = json.loads(update.effective_message.web_app_data.data)
    except json.JSONDecodeError:
        await update.message.reply_text("Invalid wallet data from Mini App.")
        return

    if data.get("action") != "wallet_connected":
        return

    address = data.get("address")
    if not address:
        await update.message.reply_text("Wallet connect failed — no address returned.")
        return

    storage.set_ton_wallet(user_id, address)
    await update.message.reply_text(
        f"✅ **Telegram Wallet linked**\n\n"
        f"TON address: `{address}`\n\n"
        f"STRIKECOINS blackjack still uses `/balance`. "
        f"On-chain TON deposits → STRIKECOINS can be added next.",
        parse_mode="Markdown",
    )


async def wallet_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    pubkey = await asyncio.to_thread(solana_wallet.get_pubkey, user_id)
    await update.message.reply_text(
        f"◎ **Solana wallet** ({solana_wallet.NETWORK_LABEL})\n\n"
        f"Address:\n`{pubkey}`\n\n"
        "This is a bot-managed devnet wallet for testing.\n"
        "Use /sol\\_balance and /sol\\_airdrop on devnet.\n"
        "Do not send mainnet funds here.",
        parse_mode="Markdown",
    )

async def sol_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    pubkey = await asyncio.to_thread(solana_wallet.get_pubkey, user_id)
    try:
        sol = await asyncio.to_thread(solana_wallet.get_sol_balance, pubkey)
    except Exception as e:
        await update.message.reply_text(f"Could not fetch balance: {e}")
        return
    await update.message.reply_text(
        f"◎ SOL balance ({solana_wallet.NETWORK_LABEL})\n"
        f"`{pubkey}`\n\n"
        f"**{sol:.4f} SOL**"
    )

async def sol_airdrop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    pubkey = await asyncio.to_thread(solana_wallet.get_pubkey, user_id)
    await update.message.reply_text("Requesting 1 SOL from devnet faucet…")
    try:
        sig = await asyncio.to_thread(solana_wallet.request_airdrop, pubkey, 1.0)
        sol = await asyncio.to_thread(solana_wallet.get_sol_balance, pubkey)
    except Exception as e:
        await update.message.reply_text(
            f"Airdrop failed (devnet rate limits are common): {e}\n"
            "Try again in a minute or use https://faucet.solana.com"
        )
        return
    await update.message.reply_text(
        f"◎ Airdrop sent on {solana_wallet.NETWORK_LABEL}\n"
        f"Tx: `{sig}`\n"
        f"Balance: **{sol:.4f} SOL**",
        parse_mode="Markdown",
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"**{CURRENCY_NAME}** — in-game chips for blackjack\n"
        f"• `/play` or `/play 50` — bet (default {DEFAULT_BET})\n"
        f"• `/balance` — STRIKECOINS stack\n\n"
        "**Telegram Wallet (TON)**\n"
        "• `/connect` — open Mini App, link @wallet / Tonkeeper\n"
        "• `/ton_wallet` — your linked TON address\n\n"
        "**Solana (devnet)** — optional, separate from Telegram Wallet\n"
        "• `/wallet`, `/sol_balance`, `/sol_airdrop`\n\n"
        "Depositing TON to credit STRIKECOINS is not enabled yet.",
        parse_mode="Markdown",
    )

async def play(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)

    try:
        bet = int(context.args[0]) if context.args else DEFAULT_BET
    except ValueError:
        bet = DEFAULT_BET

    if bet > user["strikecoins"] or bet <= 0:
        await update.message.reply_text(
            f"Invalid bet! You have {format_coins(user['strikecoins'])}."
        )
        return

    game = BlackjackGame()
    player_hand = [game.deal(), game.deal()]
    dealer_hand = [game.deal(), game.deal()]

    user["current_game"] = {
        "bet": bet,
        "player_hand": player_hand,
        "dealer_hand": dealer_hand,
        "game": game,
    }
    save_strikecoins(user_id, user["strikecoins"] - bet)

    keyboard = [
        [InlineKeyboardButton("Hit", callback_data="hit"),
         InlineKeyboardButton("Stand", callback_data="stand")]
    ]

    await update.message.reply_text(
        f"Bet: {format_coins(bet)}\n"
        f"Your hand: {player_hand} (Value: {game.hand_value(player_hand)})\n"
        f"Dealer shows: {dealer_hand[0]}",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user = get_user(user_id)
    game_data = user.get("current_game")

    if not game_data:
        await query.edit_message_text("No active game! Use /play to start.")
        return

    game = game_data["game"]
    player_hand = game_data["player_hand"]
    dealer_hand = game_data["dealer_hand"]
    bet = game_data["bet"]

    if query.data == "hit":
        player_hand.append(game.deal())
        player_val = game.hand_value(player_hand)

        if player_val > 21:
            save_strikecoins(user_id, user["strikecoins"])
            await query.edit_message_text(
                f"Bust! You lose {format_coins(bet)}.\n"
                f"Balance: {format_coins(user['strikecoins'])}"
            )
            user["current_game"] = None
            return

        await query.edit_message_text(
            f"Your hand: {player_hand} (Value: {player_val})\nDealer shows: {dealer_hand[0]}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Hit", callback_data="hit"), InlineKeyboardButton("Stand", callback_data="stand")]]),
        )

    elif query.data == "stand":
        while game.hand_value(dealer_hand) < 17:
            dealer_hand.append(game.deal())

        player_val = game.hand_value(player_hand)
        dealer_val = game.hand_value(dealer_hand)

        if dealer_val > 21 or player_val > dealer_val:
            save_strikecoins(user_id, user["strikecoins"] + bet * 2)
            result = f"You win {format_coins(bet * 2)}!"
        elif player_val == dealer_val:
            save_strikecoins(user_id, user["strikecoins"] + bet)
            result = f"Push! {format_coins(bet)} returned."
        else:
            result = f"Dealer wins. You lost {format_coins(bet)}."

        await query.edit_message_text(
            f"Your hand: {player_hand} ({player_val})\n"
            f"Dealer hand: {dealer_hand} ({dealer_val})\n{result}\n"
            f"Balance: {format_coins(user['strikecoins'])}"
        )
        user["current_game"] = None

if __name__ == '__main__':
    TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not TOKEN:
        raise SystemExit("Set TELEGRAM_BOT_TOKEN (from @BotFather) and run again.")
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(CommandHandler("connect", connect_wallet))
    app.add_handler(CommandHandler("ton_wallet", ton_wallet_cmd))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, on_web_app_data))
    app.add_handler(CommandHandler("wallet", wallet_cmd))
    app.add_handler(CommandHandler("sol_balance", sol_balance))
    app.add_handler(CommandHandler("sol_airdrop", sol_airdrop))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("play", play))
    app.add_handler(CallbackQueryHandler(button_callback))

    print("Bot running...")
    app.run_polling()
