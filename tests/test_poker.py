import tempfile
import unittest
from pathlib import Path
from unittest import mock

from plugin import help as help_plugin
from plugin import poker, wizard, wizcoins

WIZ = "akai◆wizardTREQ"
MUGGLE = "akai◆notTheTrip"
SPOOF = "akai◇wizardTREQ"  # what a typed ◆ turns into on the server


def card(text):
    """'H10' -> ('♥', 10), 'SA' -> ('♠', 1)."""
    suits = {"H": "♥", "S": "♠", "C": "♣", "D": "♦"}
    faces = {"A": 1, "J": 11, "Q": 12, "K": 13}
    rank = text[1:]
    return suits[text[0]], faces.get(rank) or int(rank)


def hand(*cards):
    return [card(c) for c in cards]


def rigged_deck(first_five, draws=()):
    """A deck that deals first_five, then hands out draws in order."""
    filler = [c for c in (card(s + r) for s in "HSCD"
                          for r in ["A", *map(str, range(2, 11)), "J", "Q", "K"])
              if c not in hand(*first_five, *draws)]
    # deal() and draw() pop from the end.
    return filler + list(reversed(hand(*draws))) + list(reversed(hand(*first_five)))


class BankTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.bank = Path(self.tmp.name) / "wizcoins.json"
        patches = [mock.patch.object(wizcoins, "BANK_FILE", self.bank),
                   mock.patch.object(wizcoins, "_accounts", None)]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        poker.games.clear()
        self.addCleanup(poker.games.clear)
        self.addCleanup(self.tmp.cleanup)


class TestParse(unittest.TestCase):
    def test_hash_commands(self):
        self.assertEqual(wizard.parse("#poker 10"), ("poker", ["10"]))
        self.assertEqual(wizard.parse("#POKER"), ("poker", []))

    def test_non_commands(self):
        for msg in ["", "   ", "!", "#", "poker 10", "hello #poker",
                    "!poker 10", "!drop 1", "!wizcoins", "!help"]:
            self.assertEqual(wizard.parse(msg), (None, []), msg)


class TestGate(BankTestCase):
    def test_is_wizard(self):
        self.assertTrue(wizard.is_wizard(WIZ))
        self.assertTrue(wizard.is_wizard("◆wizardTREQ"))
        self.assertFalse(wizard.is_wizard(MUGGLE))
        self.assertFalse(wizard.is_wizard(SPOOF))
        self.assertFalse(wizard.is_wizard("wizardTREQ"))
        self.assertFalse(wizard.is_wizard("Spy"))

    def test_non_wizards_cannot_play(self):
        for who in [MUGGLE, SPOOF, "Spy"]:
            for msg in ["#poker 5", "#drop 1", "#drop 0"]:
                out = poker.cmd(who, msg)
                self.assertEqual(len(out), 1)
                self.assertIn("wizards only", out[0])
        self.assertEqual(poker.games, {})
        self.assertFalse(self.bank.exists())

    def test_non_wizard_has_no_account(self):
        self.assertIn("wizards only", wizcoins.cmd(MUGGLE, "#wizcoins")[0])
        with self.assertRaises(ValueError):
            wizcoins.balance(MUGGLE)

    def test_full_name(self):
        for typed in ["akai", "akai◆wizardTREQ", "akai◇wizardTREQ", " akai "]:
            self.assertEqual(wizard.full_name(typed), WIZ)


class TestEvaluate(unittest.TestCase):
    cases = {
        "royal flush": ["HA", "HK", "HQ", "HJ", "H10"],
        "straight flush": ["S9", "S8", "S7", "S6", "S5"],
        "four of a kind": ["H3", "S3", "C3", "D3", "HK"],
        "full house": ["H3", "S3", "C3", "DK", "HK"],
        "flush": ["C2", "C5", "C9", "CJ", "CK"],
        "straight": ["HA", "S2", "C3", "D4", "H5"],
        "three of a kind": ["H7", "S7", "C7", "D2", "HK"],
        "two pair": ["H2", "S2", "C9", "D9", "HK"],
        "pair": ["HJ", "SJ", "C2", "D5", "H9"],
    }

    def test_paying_hands(self):
        for name, cards in self.cases.items():
            self.assertEqual(poker.evaluate(hand(*cards)), name, cards)

    def test_ace_high_straight_without_flush(self):
        self.assertEqual(poker.evaluate(hand("HA", "SK", "CQ", "DJ", "H10")),
                         "straight")

    def test_pair_of_aces_pays(self):
        self.assertEqual(poker.evaluate(hand("HA", "SA", "C2", "D5", "H9")),
                         "pair")

    def test_non_paying_hands(self):
        for cards in [["H10", "S10", "C2", "D5", "H9"],  # low pair
                      ["HQ", "SK", "CA", "D2", "H3"],    # no wraparound
                      ["H2", "S4", "C6", "D8", "H10"]]:
            self.assertIsNone(poker.evaluate(hand(*cards)), cards)

    def test_paytable_covers_every_hand(self):
        self.assertEqual(set(self.cases), set(poker.PAYTABLE))


class TestGame(BankTestCase):
    def play(self, first_five, draws, bet, drop):
        deck = rigged_deck(first_five, draws)
        with mock.patch.object(poker, "new_deck", return_value=deck):
            dealt = poker.cmd(WIZ, f"#poker {bet}")
        settled = poker.cmd(WIZ, f"#drop {drop}")
        return dealt, settled

    def test_new_wizard_starts_with_20(self):
        self.assertEqual(wizcoins.cmd(WIZ, "#wizcoins"),
                         ["akai has 20 Wizcoins."])

    def test_win_pays_bet_times_multiplier(self):
        dealt, settled = self.play(["HA", "HK", "HQ", "HJ", "S2"], ["H10"],
                                   bet=10, drop="5")
        self.assertEqual(dealt, ["akai's hand is now (♥A/♥K/♥Q/♥J/♠2), "
                                 "enter some cards to discard (0 or 1-5)"])
        self.assertEqual(settled, [
            "akai's hand is now (♥A/♥K/♥Q/♥J/♥10).",
            "Congrats on the royal flush akai, you won 8000 "
            "and now have 8020 Wizcoins!"])
        self.assertEqual(wizcoins.balance(WIZ), 20 + 8000)
        self.assertEqual(poker.games, {})

    def test_loss_costs_the_bet(self):
        _, settled = self.play(["H2", "S4", "C6", "D8", "H10"], [],
                               bet=7, drop="0")
        self.assertEqual(settled[1],
                         "Sorry akai, you lost 7 and now have 13 Wizcoins.")
        self.assertEqual(wizcoins.balance(WIZ), 13)

    def test_drop_replaces_in_place(self):
        _, settled = self.play(["H2", "S4", "C6", "D8", "H10"], ["SK", "CK"],
                               bet=1, drop="1 3")
        self.assertEqual(settled[0], "akai's hand is now (♠K/♠4/♣K/♦8/♥10).")

    def test_bet_is_capped_by_balance(self):
        _, settled = self.play(["H2", "S4", "C6", "D8", "H10"], [],
                               bet=999999, drop="0")
        self.assertEqual(settled[1],
                         "Sorry akai, you lost 20 and now have 0 Wizcoins.")

    def test_bad_bet_defaults_to_one(self):
        for bet in ["lots", "-50", "0"]:
            poker.games.clear()
            poker.cmd(WIZ, f"#poker {bet}")
            self.assertEqual(poker.games[WIZ]["bet"], 1, bet)

    def test_broke_wizard_gets_pity_coins(self):
        wizcoins.withdraw(WIZ, 20)
        out = poker.cmd(WIZ, "#poker 100")
        self.assertEqual(out[0], "akai is broke, here's 5 Wizcoins.")
        self.assertEqual(poker.games[WIZ]["bet"], 5)

    def test_new_hand_forfeits_old_bet(self):
        poker.cmd(WIZ, "#poker 4")
        out = poker.cmd(WIZ, "#poker 1")
        self.assertEqual(out[0], "You forfeit 4 and begin a new game...")
        self.assertEqual(wizcoins.balance(WIZ), 16)

    def test_drop_without_hand(self):
        self.assertIn("you need to start a game with #poker",
                      poker.cmd(WIZ, "#drop 1")[0])

    def test_bad_drop_keeps_hand(self):
        poker.cmd(WIZ, "#poker 1")
        self.assertEqual(poker.cmd(WIZ, "#drop two"), [poker.DROP_USAGE])
        self.assertIn(WIZ, poker.games)

    def test_balances_persist(self):
        self.play(["HJ", "SJ", "C2", "D5", "H9"], [], bet=3, drop="0")
        with mock.patch.object(wizcoins, "_accounts", None):
            self.assertEqual(wizcoins.peek(WIZ), 23)

    def test_leaderboard_and_lookup(self):
        wizcoins.deposit("bob◆wizardTREQ", 500)
        wizcoins.balance(WIZ)
        self.assertEqual(wizcoins.cmd(MUGGLE, "#wizards"),
                         ["Richest wizards: bob: 520 / akai: 20"])
        self.assertEqual(wizcoins.cmd(MUGGLE, "#wizcoins bob◇wizardTREQ"),
                         ["bob has 520 Wizcoins."])
        self.assertEqual(wizcoins.cmd(MUGGLE, "#wizcoins nobody"),
                         ["nobody has no Wizcoins yet."])

    def test_bang_commands_are_ignored(self):
        for msg in ["!poker 5", "!drop 0", "!wizcoins", "!wizards"]:
            self.assertEqual(poker.cmd(WIZ, msg) + wizcoins.cmd(WIZ, msg), [], msg)
        self.assertEqual(help_plugin.cmd(WIZ, "!help"), [])
        self.assertEqual(poker.games, {})

    def test_help(self):
        self.assertEqual(help_plugin.cmd(MUGGLE, "#help"), [help_plugin.HELP])
        self.assertEqual(help_plugin.cmd(MUGGLE, "help"), [])


if __name__ == "__main__":
    unittest.main()
