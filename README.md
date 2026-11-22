# Akai's bot: wizard poker

A poker bot for [Gikopoi](https://play.gikopoi.com), forked from
[153/giko.py](https://github.com/153/giko.py) and cut down to poker only.

**Only players logged in with the `◆wizardTREQ` tripcode can play.**
Winnings are paid in **Wizcoins**.

## Setup

```sh
pip3 install -r requirements.txt
./giko.py          # joins the admin room
./giko.py bar      # or pass another room ID
```

Server, area, room, character and bot name are at the top of `giko.py`.
To give the bot its own tripcode, put a secret on the first line of
`tripcode.txt` (it's gitignored).

## Playing

Every command works with `!` or `#`, so `#poker 10` is the same as `!poker 10`.

| Command | What it does |
| --- | --- |
| `!poker <bet>` | Deal five cards (Jacks or Better). Bet 1 to 1000 Wizcoins. |
| `!drop 2 5` | Swap cards 2 and 5 and settle the hand. `!drop 0` keeps all five. |
| `!wizcoins [name]` | Show your balance, or another wizard's. |
| `!wizards` | Top 5 richest wizards. |
| `!help` | Command summary. |

New wizards start with 20 Wizcoins. A wizard who goes broke gets 5 from
the wizard council on their next `!poker`. Dealing a new hand before
finishing the last one forfeits the old bet.

Payouts (net Wizcoins per Wizcoin bet, same as upstream giko.py):

| Hand | Pays |
| --- | --- |
| Royal Flush | 800 |
| Straight Flush | 50 |
| Four of a Kind | 25 |
| Full House | 9 |
| Flush | 6 |
| Straight | 4 |
| Three of a Kind | 3 |
| Two Pair | 2 |
| Jacks or Better | 1 |

These favor the player heavily, so Wizcoins pile up. Edit `PAYTABLE` in
`plugin/poker.py` to change that.

## How the tripcode gate works

Gikopoi turns any `◆` typed into a name into `◇`, and only adds a real
`◆` when it computes a tripcode from a `name#password` login. So a name
ending in `◆wizardTREQ` can only come from knowing the wizard password.
Balances are stored per full name in `data/wizcoins.json`.

## Tests

```sh
python3 -m unittest discover tests
```

No copyright, public domain, same as upstream.
