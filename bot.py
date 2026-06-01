import logging
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

logging.basicConfig(level=logging.INFO)

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

# In-memory storage (later upgrade to SQLite)
users = {}  # user_id: {"balance": 1000, "current_game": None}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in users:
        users[user_id] = {"balance": 1000}
    await update.message.reply_text(
        f"Welcome to Blackjack, {update.effective_user.first_name}!\n"
        f"Your balance: ${users[user_id]['balance']}\n"
        "Use /play [bet] to start a game."
    )

async def play(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in users:
        users[user_id] = {"balance": 1000}

    try:
        bet = int(context.args[0]) if context.args else 100
    except:
        bet = 100

    if bet > users[user_id]["balance"] or bet <= 0:
        await update.message.reply_text("Invalid bet!")
        return

    game = BlackjackGame()
    player_hand = [game.deal(), game.deal()]
    dealer_hand = [game.deal(), game.deal()]

    users[user_id]["current_game"] = {
        "bet": bet,
        "player_hand": player_hand,
        "dealer_hand": dealer_hand,
        "game": game
    }
    users[user_id]["balance"] -= bet

    keyboard = [
        [InlineKeyboardButton("Hit", callback_data="hit"),
         InlineKeyboardButton("Stand", callback_data="stand")]
    ]

    await update.message.reply_text(
        f"Bet: ${bet}\n"
        f"Your hand: {player_hand} (Value: {game.hand_value(player_hand)})\n"
        f"Dealer shows: {dealer_hand[0]}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data
    game_data = users.get(user_id, {}).get("current_game")

    if not game_data:
        await query.answer("No active game!")
        return

    game = game_data["game"]
    player_hand = game_data["player_hand"]
    dealer_hand = game_data["dealer_hand"]
    bet = game_data["bet"]

    if data == "hit":
        player_hand.append(game.deal())
        player_val = game.hand_value(player_hand)

        if player_val > 21:
            await query.edit_message_text(f"Bust! You lose ${bet}.")
            users[user_id]["current_game"] = None
            return

        await query.edit_message_text(
            f"Your hand: {player_hand} (Value: {player_val})\nDealer shows: {dealer_hand[0]}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Hit", callback_data="hit"), InlineKeyboardButton("Stand", callback_data="stand")]])
        )

    elif data == "stand":
        # Dealer plays
        while game.hand_value(dealer_hand) < 17:
            dealer_hand.append(game.deal())

        player_val = game.hand_value(player_hand)
        dealer_val = game.hand_value(dealer_hand)

        if dealer_val > 21 or player_val > dealer_val:
            users[user_id]["balance"] += bet * 2
            result = f"You win ${bet*2}!"
        elif player_val == dealer_val:
            users[user_id]["balance"] += bet
            result = "Push! Bet returned."
        else:
            result = f"Dealer wins. You lost ${bet}."

        await query.edit_message_text(
            f"Your hand: {player_hand} ({player_val})\n"
            f"Dealer hand: {dealer_hand} ({dealer_val})\n{result}\n"
            f"New balance: ${users[user_id]['balance']}"
        )
        users[user_id]["current_game"] = None

if __name__ == '__main__':
    TOKEN = "YOUR_BOT_TOKEN_HERE"  # Get from @BotFather
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("play", play))
    app.add_handler(CallbackQueryHandler(button_callback))

    print("Bot running...")
    app.run_polling()
