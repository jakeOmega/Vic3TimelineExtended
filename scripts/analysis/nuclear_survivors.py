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
capital decapitate it with a chance of max(0, (L - R)/(L + R)).

test_nuclear_survivors.py checks it against the script values, as
nuclear_taboo_sim.py mirrors the taboo. Run it to print the survivors table
and the counterforce calibration (owner, 2026-10-28: keep K, check it here).
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


def decapitation_chance(landed, redundancy):
    """Percent chance that `landed` warheads on the capital decapitate (nd_decapitation_chance_value)."""
    return max(0.0, (landed - redundancy) / (landed + redundancy)) * 100


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


if __name__ == "__main__":
    main()
