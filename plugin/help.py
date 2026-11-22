from . import wizard

HELP = ("Wizard poker (Jacks or Better, wizardTREQ tripcode only): "
        "!poker <bet> deals 5 cards, !drop 1 3 swaps cards 1 and 3, "
        "!drop 0 keeps all. !wizcoins [name] shows a balance, "
        "!wizards shows the richest wizards. Every command also works "
        "with # instead of !.")


def cmd(player, msg):
    command, _ = wizard.parse(msg)
    if command == "help":
        return [HELP]
    return []


print("Help plugin loaded")
