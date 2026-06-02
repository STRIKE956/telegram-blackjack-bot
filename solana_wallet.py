import json
import os
import urllib.error
import urllib.request
from pathlib import Path

from solders.keypair import Keypair

_DATA = Path(os.environ.get("DATA_DIR", "data"))
WALLET_DIR = _DATA / "wallets"
DEFAULT_RPC = os.environ.get("SOLANA_RPC_URL", "https://api.devnet.solana.com")
NETWORK_LABEL = "devnet" if "devnet" in DEFAULT_RPC else "mainnet-beta"


def _rpc(method: str, params: list) -> dict:
    payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    req = urllib.request.Request(
        DEFAULT_RPC,
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
    if "error" in data:
        raise RuntimeError(data["error"].get("message", str(data["error"])))
    return data["result"]


def wallet_path(user_id: int) -> Path:
    WALLET_DIR.mkdir(parents=True, exist_ok=True)
    return WALLET_DIR / f"{user_id}.json"


def load_or_create_wallet(user_id: int) -> Keypair:
    path = wallet_path(user_id)
    if path.exists():
        secret = json.loads(path.read_text())
        return Keypair.from_bytes(bytes(secret))
    kp = Keypair()
    path.write_text(json.dumps(list(bytes(kp))))
    os.chmod(path, 0o600)
    return kp


def get_pubkey(user_id: int) -> str:
    return str(load_or_create_wallet(user_id).pubkey())


def get_sol_balance(pubkey: str) -> float:
    result = _rpc("getBalance", [pubkey, {"commitment": "confirmed"}])
    lamports = result["value"]
    return lamports / 1_000_000_000


def request_airdrop(pubkey: str, sol_amount: float = 1.0) -> str:
    lamports = int(sol_amount * 1_000_000_000)
    sig = _rpc("requestAirdrop", [pubkey, lamports, {"commitment": "confirmed"}])
    return sig
