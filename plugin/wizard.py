"""The tripcode gate: only ◆wizardTREQ wizards may play.

Gikopoi turns any ◆ a user types into ◇ and only adds a real ◆ when it
works out a tripcode from the name#password login. So a name ending in
◆wizardTREQ can't be faked.
"""

WIZARD_TRIP = "◆wizardTREQ"

# The server also swaps ◆ for ◇ inside chat messages, so a typed name
# like "#wizcoins akai◆wizardTREQ" reaches the bot as "akai◇wizardTREQ".
_TYPED_TRIP = "◇" + WIZARD_TRIP[1:]

PREFIX = "#"


def is_wizard(name):
    return name.endswith(WIZARD_TRIP)


def short_name(name):
    """Name without the tripcode, since every wizard has the same one."""
    return name.split("◆", 1)[0].strip() or "Nameless wizard"


def full_name(typed):
    """Turn a typed name ("akai", "akai◇wizardTREQ") into its account key."""
    typed = typed.strip()
    for trip in (WIZARD_TRIP, _TYPED_TRIP):
        if typed.endswith(trip):
            typed = typed[: -len(trip)]
            break
    return typed + WIZARD_TRIP


def parse(msg):
    """Split a chat message into (command, args).

    "#poker 10" gives ("poker", ["10"]). Anything that isn't a # command,
    including the old !poker style, gives (None, []).
    """
    words = msg.split()
    if not words or len(words[0]) < 2 or words[0][0] != PREFIX:
        return None, []
    return words[0][1:].lower(), words[1:]


def denied(player):
    # Written without the ◆ because the server would show it as ◇.
    return (f"Sorry {short_name(player)}, poker is for wizards only. "
            "Log in with the wizardTREQ tripcode to play.")
