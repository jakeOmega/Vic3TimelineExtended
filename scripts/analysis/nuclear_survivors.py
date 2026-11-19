"""Python mirror of the second-strike survivors measure (nd_survivors_vs_saved).

docs/superpowers/specs/2026-10-28-nuclear-crisis-rework-design.md §3.2: for a
country X facing an enemy Y,

    exposed   = stockpile(X) × (1 − effective survivability(X) ÷ 100)
    reach     = K(Y) × believed stockpile(Y)
    survivors = stockpile(X) − min(exposed, reach) × (1 − launch credit(X))

Weapons Y bases in a country next to X cut X's warning time (§7.4): against Y
only, X's effective survivability is 10 lower, never below zero.

In the exchange itself (§6.2, §6.3), a Forces salvo that lands L warheads on
the victim's arsenal destroys min(exposed, K x L) x (1 - credit) of it, and the
credit's share gets away first; L warheads on a Central Authorization victim's
capital decapitate it with a chance of max(0, 1 - (R/L)^2) (owner, 2026-11-19;
until then (L - R)/(L + R)). R, the victim's redundancy, is 1 + warheads / 10,
+2 with Satellite Communications, +1 with Mainframe Computers, + survivability
/ 20, +2 a staffed Nuclear Command Center level (at most +6) and + (command
reliability - 50) / 10, never below 1.

test_nuclear_survivors.py checks it against the script values, as
nuclear_taboo_sim.py mirrors the taboo. Run it to print the survivors table
the counterforce calibration (owner, 2026-10-28: keep K, check it here) and
a full Leadership salvo's chance against a range of commands.
"""


WARNING_TIME_PENALTY = 10


def exposed(stockpile, survivability, readiness_factor, based_near=False):
    """Our warheads a first strike could reach (nd_exposed_warheads_vs_saved)."""
    effective = survivability * readiness_factor
    if based_near:
        effective = max(0.0, effective - WARNING_TIME_PENALTY)
    return stockpile * (1 - effective / 100)


def survivors(stockpile, survivability, readiness_factor, credit, enemy_k, enemy_believed, based_near=False):
    """Warheads left after the enemy spends its whole arsenal on ours."""
    destroyed = min(exposed(stockpile, survivability, readiness_factor, based_near),
                    enemy_k * enemy_believed) * (1 - credit)
    return max(0.0, stockpile - destroyed)


def counterforce_destroyed(landed, k, exposed, credit):
    """Warheads a Forces salvo landing `landed` destroys (nd_counterforce_destroyed_raw)."""
    return max(0.0, min(exposed, k * landed) * (1 - credit))


def counterforce_saved(landed, k, exposed, credit):
    """Of those it would destroy, the share that gets away first (nd_counterforce_saved_raw)."""
    return max(0.0, min(exposed, k * landed) * credit)


def redundancy(stockpile, satellite_communications=True, mainframe=True, survivability=0.0,
               command_center=0, reliability=None):
    """A command's redundancy against a Leadership salvo (nd_redundancy).
    `command_center` is staffed Nuclear Command Center levels; `reliability`
    None leaves the reliability term out, as nd_redundancy_believed does."""
    r = 1 + stockpile / 10 + 2 * satellite_communications + mainframe + survivability / 20
    r += min(6, 2 * command_center)
    if reliability is not None:
        r += (reliability - 50) / 10
    return max(1.0, r)


def decapitation_chance(landed, redundancy):
    """Percent chance that `landed` warheads on the command decapitate (nd_decapitation_chance_value)."""
    if landed <= 0:
        return 0.0
    return max(0.0, 1 - (redundancy / landed) ** 2) * 100


# Commands a full salvo of 25 might face: (label, nd_redundancy's arguments).
DECAPITATION_ROWS = (
    ("5 warheads, survivability 40, reliability 72", dict(stockpile=5, survivability=40, reliability=72)),
    ("20 warheads, survivability 50, reliability 72", dict(stockpile=20, survivability=50, reliability=72)),
    ("20 warheads, as above, comms sabotaged (reliability 62)", dict(stockpile=20, survivability=50, reliability=62)),
    ("50 warheads, survivability 70, reliability 84", dict(stockpile=50, survivability=70, reliability=84)),
    ("100 warheads, survivability 80, reliability 98", dict(stockpile=100, survivability=80, reliability=98)),
    ("50 warheads, survivability 80, reliability 98, Command Center x3",
     dict(stockpile=50, survivability=80, reliability=98, command_center=3)),
)


def calibration():
    """Warheads left after a Forces salvo landing half as many warheads as the
    victim holds, against arsenals the AI builds (about 5 to 20), under Central
    Authorization. A salvo as large as the arsenal reaches all of its exposure
    at any K, so K matters only against a larger victim."""
    rows = []
    for stockpile in (5, 10, 20):
        for survivability in (0, 40, 72):
            exposed = stockpile * (1 - survivability / 100)
            left = [stockpile - counterforce_destroyed(stockpile / 2, k, exposed, 0) for k in (1.0, 1.5, 2.0)]
            rows.append((stockpile, survivability, left))
    return rows


def main():
    print("| Our warheads | Survivability | Enemy reach | Central | Delegation | Launch on Warning |")
    print("|---|---|---|---|---|---|")
    for stockpile, survivability, reach in ((5, 40, 10), (10, 60, 10), (20, 80, 40), (3, 25, 3)):
        row = [survivors(stockpile, survivability, 1.0, credit, 1.0, reach) for credit in (0, 0.25, 0.6)]
        print(f"| {stockpile} | {survivability} | {reach} | " + " | ".join(f"{s:.1f}" for s in row) + " |")
    print()
    print("Left after a Forces salvo landing half as many warheads (Central Authorization)")
    print("| Warheads | Effective survivability | K 1 | K 1.5 | K 2 |")
    print("|---|---|---|---|---|")
    for stockpile, survivability, left in calibration():
        print(f"| {stockpile} | {survivability} | " + " | ".join(f"{x:.1f}" for x in left) + " |")
    print()
    print("A Leadership salvo, warheads landed on the command (Central Authorization, both technologies)")
    print("| Command | R | 10 landed | 25 landed |")
    print("|---|---|---|---|")
    for label, kwargs in DECAPITATION_ROWS:
        r = redundancy(**kwargs)
        print(f"| {label} | {r:.1f} | {decapitation_chance(10, r):.0f}% | {decapitation_chance(25, r):.0f}% |")


if __name__ == "__main__":
    main()
