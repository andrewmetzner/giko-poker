"""Wizcoins: the currency wizards win and lose at poker.

Balances are stored in data/wizcoins.json, keyed by full name
(e.g. "akai◆wizardTREQ"). Only wizards can hold an account.
"""

import json
import os
import tempfile
import threading
from pathlib import Path

from . import wizard

BANK_FILE = Path(__file__).resolve().parent.parent / "data" / "wizcoins.json"
STARTING_COINS = 20
LEADERBOARD_SIZE = 5

_lock = threading.RLock()
_accounts = None


def _load():
    global _accounts
    if _accounts is None:
        try:
            raw = json.loads(BANK_FILE.read_text(encoding="utf-8"))
        except FileNotFoundError:
            raw = {}
        # A corrupt file raises here on purpose, so balances never get wiped.
        _accounts = {name: int(coins) for name, coins in raw.items()}
    return _accounts


def _save():
    BANK_FILE.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=BANK_FILE.parent, prefix=".wizcoins-")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(_accounts, f, ensure_ascii=False, indent=1, sort_keys=True)
    os.replace(tmp, BANK_FILE)


def balance(player):
    """A wizard's balance. Opens an account with STARTING_COINS if needed."""
    if not wizard.is_wizard(player):
        raise ValueError(f"{player!r} is not a wizard")
    with _lock:
        accounts = _load()
        if player not in accounts:
            accounts[player] = STARTING_COINS
            _save()
        return accounts[player]


def peek(player):
    """A balance without opening an account; None if there isn't one."""
    with _lock:
        return _load().get(player)


def deposit(player, amount):
    with _lock:
        balance(player)
        _accounts[player] += amount
        _save()
        return _accounts[player]


def withdraw(player, amount):
    with _lock:
        balance(player)
        _accounts[player] -= amount
        _save()
        return _accounts[player]


def leaderboard(n=LEADERBOARD_SIZE):
    with _lock:
        ranked = sorted(_load().items(), key=lambda kv: kv[1], reverse=True)
    return ranked[:n]


def cmd(player, msg):
    command, args = wizard.parse(msg)

    if command == "wizcoins":
        if args:
            target = wizard.full_name(" ".join(args))
            coins = peek(target)
            if coins is None:
                return [f"{wizard.short_name(target)} has no Wizcoins yet."]
            return [f"{wizard.short_name(target)} has {coins} Wizcoins."]
        if not wizard.is_wizard(player):
            return [wizard.denied(player)]
        return [f"{wizard.short_name(player)} has {balance(player)} Wizcoins."]

    if command == "wizards":
        top = leaderboard()
        if not top:
            return ["No wizard has played yet."]
        board = " / ".join(f"{wizard.short_name(name)}: {coins}"
                           for name, coins in top)
        return [f"Richest wizards: {board}"]

    return []


print("Wizcoins plugin loaded")
