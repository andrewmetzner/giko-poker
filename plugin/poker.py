"""Five-card draw video poker (Jacks or Better), for wizards only.

#poker <bet> deals five cards. #drop <positions>
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
    "royal flush": 800,
    "straight flush": 50,
    "four of a kind": 25,
    "full house": 9,
    "flush": 6,
    "straight": 4,
    "three of a kind": 3,
    "two pair": 2,
    "pair": 1,  # jacks or better
}

SUITS = "♥♠♣♦"
FACES = {1: "A", 11: "J", 12: "Q", 13: "K"}
HIGH_PAIRS = {1, 11, 12, 13}  # aces, jacks, queens, kings

DROP_USAGE = ("Please type a space separated list of cards to discard, "
              "eg #drop 0 or #drop 2 or #drop 1 2 4")

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
        out.append(f"You forfeit {lost} and begin a new game...")

    coins = wizcoins.balance(player)
    if coins < 1:
        coins = wizcoins.deposit(player, PITY_COINS)
        out.append(f"{name} is broke, here's {PITY_COINS} Wizcoins.")

    try:
        bet = int(bet_arg)
    except ValueError:
        bet = 1
    bet = max(1, min(bet, coins, MAX_BET))

    deck = new_deck()
    hand = [deck.pop() for _ in range(5)]
    games[player] = {"deck": deck, "hand": hand, "bet": bet}

    out.append(f"{name}'s hand is now {show(hand)}, "
               "enter some cards to discard (0 or 1-5)")
    return out


def draw(player, args):
    name = wizard.short_name(player)
    game = games.get(player)
    if game is None:
        return [f"{name}, you need to start a game with #poker "
                "before you can discard cards."]

    try:
        picks = {int(a) for a in args}
    except ValueError:
        return [DROP_USAGE]

    hand, deck, bet = game["hand"], game["deck"], game["bet"]
    for pos in sorted(p for p in picks if 1 <= p <= 5):
        hand[pos - 1] = deck.pop()
    del games[player]

    out = [f"{name}'s hand is now {show(hand)}."]
    rank = evaluate(hand)
    if rank:
        won = bet * PAYTABLE[rank]
        coins = wizcoins.deposit(player, won)
        out.append(f"Congrats on the {rank} {name}, you won {won} "
                   f"and now have {coins} Wizcoins!")
    else:
        coins = wizcoins.withdraw(player, bet)
        out.append(f"Sorry {name}, you lost {bet} and now have "
                   f"{coins} Wizcoins.")
    return out


def evaluate(hand):
    """Name of the best paying hand, or None if it doesn't pay."""
    ranks = sorted(rank for _, rank in hand)
    counts = sorted(Counter(ranks).values(), reverse=True)
    flush = len({suit for suit, _ in hand}) == 1
    distinct = len(set(ranks)) == 5
    royal = ranks == [1, 10, 11, 12, 13]
    straight = distinct and (ranks[4] - ranks[0] == 4 or royal)

    if royal and flush:
        return "royal flush"
    if straight and flush:
        return "straight flush"
    if counts[0] == 4:
        return "four of a kind"
    if counts == [3, 2]:
        return "full house"
    if flush:
        return "flush"
    if straight:
        return "straight"
    if counts[0] == 3:
        return "three of a kind"
    if counts == [2, 2, 1]:
        return "two pair"
    if counts[0] == 2:
        pair = next(r for r, c in Counter(ranks).items() if c == 2)
        if pair in HIGH_PAIRS:
            return "pair"
    return None


def show(hand):
    return "(" + "/".join(f"{suit}{FACES.get(rank, rank)}"
                          for suit, rank in hand) + ")"


print("Poker plugin loaded")
