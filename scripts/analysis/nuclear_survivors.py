"""Python mirror of the second-strike survivors measure (nd_survivors_vs_saved).

docs/superpowers/specs/2026-10-28-nuclear-crisis-rework-design.md §3.2: for a
country X facing an enemy Y,

    exposed   = stockpile(X) × (1 − effective survivability(X) ÷ 100)
    reach     = K(Y) × believed stockpile(Y)
    survivors = stockpile(X) − min(exposed, reach) × (1 − launch credit(X))

test_nuclear_survivors.py checks it against the script values, as
nuclear_taboo_sim.py mirrors the taboo. Run it to print a small table.
"""


def survivors(stockpile, survivability, readiness_factor, credit, enemy_k, enemy_believed):
    """Warheads left after the enemy spends its whole arsenal on ours."""
    exposed = stockpile * (1 - survivability * readiness_factor / 100)
    destroyed = min(exposed, enemy_k * enemy_believed) * (1 - credit)
    return max(0.0, stockpile - destroyed)


def main():
    print("| Our warheads | Survivability | Enemy reach | Central | Delegation | Launch on Warning |")
    print("|---|---|---|---|---|---|")
    for stockpile, survivability, reach in ((5, 40, 10), (10, 60, 10), (20, 80, 40), (3, 25, 3)):
        row = [survivors(stockpile, survivability, 1.0, credit, 1.0, reach) for credit in (0, 0.25, 0.6)]
        print(f"| {stockpile} | {survivability} | {reach} | " + " | ".join(f"{s:.1f}" for s in row) + " |")


if __name__ == "__main__":
    main()
