import os
import sqlite3
from pathlib import Path

DATA_DIR = Path(os.environ.get("DATA_DIR", "data"))
DB_PATH = DATA_DIR / "bot.db"
STARTING_STRIKECOINS = 1000


def _connect():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, strikecoins INTEGER NOT NULL)"
    )
    return conn


def ensure_user(user_id: int) -> int:
    with _connect() as conn:
        row = conn.execute(
            "SELECT strikecoins FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()
        if row is None:
            conn.execute(
                "INSERT INTO users (user_id, strikecoins) VALUES (?, ?)",
                (user_id, STARTING_STRIKECOINS),
            )
            return STARTING_STRIKECOINS
        return row[0]


def get_strikecoins(user_id: int) -> int:
    return ensure_user(user_id)


def set_strikecoins(user_id: int, amount: int) -> None:
    ensure_user(user_id)
    with _connect() as conn:
        conn.execute(
            "UPDATE users SET strikecoins = ? WHERE user_id = ?",
            (amount, user_id),
        )
