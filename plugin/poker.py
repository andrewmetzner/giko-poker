"""Five-card draw video poker (Jacks or Better), for wizards only.

!poker <bet> (or #poker <bet>) deals five cards. !drop <positions>
swaps those cards and settles the hand.

The paytable is the same as upstream giko.py: a winning hand pays
bet x multiplier on top of the stake, and a losing hand costs the bet.
That favors the player heavily, which is what lets wizards rack up
Wizcoins. Lower PAYTABLE to give the house an edge.
"""

import random
import threading
from collections import Counter

from . import wizard
from . import wizcoins

MAX_BET = 1000
PITY_COINS = 5

# Net Wizcoins won per Wizcoin bet.
PAYTABLE = {
    "Royal Flush": 800,
    "Straight Flush": 50,
    "Four of a Kind": 25,
    "Full House": 9,
    "Flush": 6,
    "Straight": 4,
    "Three of a Kind": 3,
    "Two Pair": 2,
    "Jacks or Better": 1,
}

SUITS = "♥♠♣♦"
FACES = {1: "A", 11: "J", 12: "Q", 13: "K"}
HIGH_PAIRS = {1, 11, 12, 13}  # aces, jacks, queens, kings

DROP_USAGE = ("Pick cards to swap by position, like !drop 2 5, "
              "or !drop 0 to keep all five.")

_rng = random.SystemRandom()
_lock = threading.RLock()
games = {}  # full name -> {"deck": [...], "hand": [...], "bet": int}


def cmd(player, msg):
    command, args = wizard.parse(msg)
    if command not in ("poker", "drop"):
        return []
    if not wizard.is_wizard(player):
        return [wizard.denied(player)]
    with _lock:
        if command == "poker":
            return deal(player, args[0] if args else "1")
        return draw(player, args)


def new_deck():
    deck = [(suit, rank) for suit in SUITS for rank in range(1, 14)]
    _rng.shuffle(deck)
    return deck


def deal(player, bet_arg):
    name = wizard.short_name(player)
    out = []

    if player in games:
        lost = games.pop(player)["bet"]
        wizcoins.withdraw(player, lost)
        out.append(f"{name} folds the last hand and forfeits {lost} Wizcoins.")

    coins = wizcoins.balance(player)
    if coins < 1:
        coins = wizcoins.deposit(player, PITY_COINS)
        out.append(f"{name} is broke, so the wizard council grants "
                   f"{PITY_COINS} Wizcoins.")

    try:
        bet = int(bet_arg)
    except ValueError:
        bet = 1
    bet = max(1, min(bet, coins, MAX_BET))

    deck = new_deck()
    hand = [deck.pop() for _ in range(5)]
    games[player] = {"deck": deck, "hand": hand, "bet": bet}

    out.append(f"{name} bets {bet} Wizcoins: {show(hand, numbered=True)} "
               f"| {DROP_USAGE}")
    return out


def draw(player, args):
    name = wizard.short_name(player)
    game = games.get(player)
    if game is None:
        return [f"{name}, start a hand with !poker <bet> first."]

    try:
        picks = {int(a) for a in args}
    except ValueError:
        return [DROP_USAGE]

    hand, deck, bet = game["hand"], game["deck"], game["bet"]
    for pos in sorted(p for p in picks if 1 <= p <= 5):
        hand[pos - 1] = deck.pop()
    del games[player]

    rank = evaluate(hand)
    if rank:
        won = bet * PAYTABLE[rank]
        coins = wizcoins.deposit(player, won)
        result = f"{rank}! {name} wins {won} Wizcoins and now has {coins}."
    else:
        coins = wizcoins.withdraw(player, bet)
        result = f"No luck, {name} loses {bet} Wizcoins and now has {coins}."
    return [f"{show(hand)} {result}"]


def evaluate(hand):
    """Name of the best paying hand, or None if it doesn't pay."""
    ranks = sorted(rank for _, rank in hand)
    counts = sorted(Counter(ranks).values(), reverse=True)
    flush = len({suit for suit, _ in hand}) == 1
    distinct = len(set(ranks)) == 5
    royal = ranks == [1, 10, 11, 12, 13]
    straight = distinct and (ranks[4] - ranks[0] == 4 or royal)

    if royal and flush:
        return "Royal Flush"
    if straight and flush:
        return "Straight Flush"
    if counts[0] == 4:
        return "Four of a Kind"
    if counts == [3, 2]:
        return "Full House"
    if flush:
        return "Flush"
    if straight:
        return "Straight"
    if counts[0] == 3:
        return "Three of a Kind"
    if counts == [2, 2, 1]:
        return "Two Pair"
    if counts[0] == 2:
        pair = next(r for r, c in Counter(ranks).items() if c == 2)
        if pair in HIGH_PAIRS:
            return "Jacks or Better"
    return None


def show(hand, numbered=False):
    cards = [f"{suit}{FACES.get(rank, rank)}" for suit, rank in hand]
    if numbered:
        return " ".join(f"[{i}]{c}" for i, c in enumerate(cards, 1))
    return "(" + " ".join(cards) + ")"


print("Poker plugin loaded")
