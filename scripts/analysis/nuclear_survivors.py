"""Python mirror of the second-strike survivors measure (nd_survivors_vs_saved).

docs/superpowers/specs/2026-10-28-nuclear-crisis-rework-design.md §3.2: for a
country X facing an enemy Y,

    exposed   = stockpile(X) × (1 − effective survivability(X) ÷ 100)
    reach     = K(Y) × believed stockpile(Y)
    survivors = stockpile(X) − min(exposed, reach) × (1 − launch credit(X))

Weapons Y bases in a country next to X cut X's warning time (§7.4): against Y
only, X's effective survivability is 10 lower, never below zero.

Survivability climbs toward a target (2026-11-20 delivery spec §3.1): each part
of a force removes a share of what is still exposed, so the target is 100 x (1
- the product of the parts' factors), a factor of 1 for a part not held.

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

# nd_exposure_factor_*: the share of what is still exposed that each part
# leaves exposed. Bombers are always held.
EXPOSURE_FACTORS = {"bombers": 0.75, "radar": 0.80, "icbms": 0.70, "submarines": 0.50, "missile_defense": 0.85}


def exposure_factor(part, held=True):
    """One part's factor (nd_exposure_factor_<part>): 1 while it isn't held."""
    return EXPOSURE_FACTORS[part] if held or part == "bombers" else 1.0


def survivability_target(radar=True, icbms=True, submarines=True, missile_defense=True):
    """Where hardening takes survivability (nd_survivability_target)."""
    share = exposure_factor("bombers")
    for part, held in (("radar", radar), ("icbms", icbms), ("submarines", submarines),
                       ("missile_defense", missile_defense)):
        share *= exposure_factor(part, held)
    return 100 * (1 - share)


def full_strike_lost_share(target, credit):
    """The share of a force a full first strike destroys, at its target and
    High Alert, from a rival large enough to reach every exposed warhead (spec
    §3.3): the exposed share, less what launch credit gets away first."""
    return (1 - target / 100) * (1 - credit)


# The spec's §3.1 rows: (label, survivability_target's arguments).
TARGET_ROWS = (
    ("Bombers", dict(radar=False, icbms=False, submarines=False, missile_defense=False)),
    ("+ Radar", dict(icbms=False, submarines=False, missile_defense=False)),
    ("+ ICBMs", dict(submarines=False, missile_defense=False)),
    ("+ missile submarines", dict(missile_defense=False)),
    ("+ Missile Defense Systems", dict()),
    ("Bombers, Radar, ICBMs, missile defense (no submarines)", dict(submarines=False)),
)


def accuracy_mult(enemy_penetration, fields_icbms=True):
    """How much more of our force an enemy's precision weapons reach (spec
    §3.4; nd_accuracy_mult_saved): our silos leave the silo factor plus its
    penetration exposed. 1 when we field no silos or it has none."""
    if not fields_icbms or enemy_penetration <= 0:
        return 1.0
    silo = EXPOSURE_FACTORS["icbms"]
    return (silo + enemy_penetration) / silo


def exposed(stockpile, survivability, readiness_factor, based_near=False, accuracy=1.0):
    """Our warheads a first strike could reach (nd_exposed_warheads_vs_saved):
    the warning penalty, then the enemy's accuracy, the share held at 1."""
    effective = survivability * readiness_factor
    if based_near:
        effective = max(0.0, effective - WARNING_TIME_PENALTY)
    return stockpile * min(1.0, (1 - effective / 100) * accuracy)


def survivors(stockpile, survivability, readiness_factor, credit, enemy_k, enemy_believed, based_near=False,
              accuracy=1.0):
    """Warheads left after the enemy spends its whole arsenal on ours."""
    destroyed = min(exposed(stockpile, survivability, readiness_factor, based_near, accuracy),
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


# The world's view's other end (2026-11-20 delivery spec §5.2, plan D8): a
# force left unhardened decays to this share of its target, and safeguards at
# their highest (three levels) cut a fast authority's credit by this much.
FLOOR_SHARE = 0.3
SAFEGUARDS_CREDIT_CUT_MAX = 0.15


def forces_preview(estimate, target, readiness_factor, credit, k, landed, based_near=False, accuracy=1.0,
                   fires_first=False):
    """The Strike section's Forces preview (nd_pv_*, plan D14): what `landed`
    warheads, each destroying `k`, do to an arsenal the world estimates at
    `estimate`. Each figure is a range (low, high) from the world's view: one
    end a force at its target with its authority's full credit, the other at
    its floor with the credit cut by every safeguards level. Returns
    (destroyed, flown first, kept): flown first only under Launch on Warning,
    at most 3; kept is what the salvo leaves them, those flown first among it."""
    low_credit = max(0.0, credit - SAFEGUARDS_CREDIT_CUT_MAX)
    at_target = exposed(estimate, target, readiness_factor, based_near, accuracy)
    at_floor = exposed(estimate, target * FLOOR_SHARE, readiness_factor, based_near, accuracy)
    low = min(estimate, counterforce_destroyed(landed, k, at_target, credit))
    high = min(estimate, counterforce_destroyed(landed, k, at_floor, low_credit))
    flown = (0.0, 0.0)
    if fires_first:
        a = min(3.0, counterforce_saved(landed, k, at_target, credit))
        b = min(3.0, counterforce_saved(landed, k, at_floor, low_credit))
        flown = (min(a, b), max(a, b))
    return (low, high), flown, (max(0.0, estimate - high), max(0.0, estimate - low))


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
    Authorization: unhardened, part hardened, and at the highest target at
    Heightened. A salvo as large as the arsenal reaches all of its exposure at
    any K, so K matters only against a larger victim."""
    rows = []
    for stockpile in (5, 10, 20):
        for survivability in (0, 40, round(survivability_target() * 0.9, 1)):
            exposed = stockpile * (1 - survivability / 100)
            left = [stockpile - counterforce_destroyed(stockpile / 2, k, exposed, 0) for k in (1.0, 1.5, 2.0)]
            rows.append((stockpile, survivability, left))
    return rows


def main():
    print("Survivability target and a full first strike's losses at it (High Alert, no safeguards)")
    print("| Forces | Target | Central | Delegation | Launch on Warning |")
    print("|---|---|---|---|---|")
    for label, kwargs in TARGET_ROWS:
        target = survivability_target(**kwargs)
        lost = [full_strike_lost_share(target, credit) * 100 for credit in (0, 0.25, 0.6)]
        print(f"| {label} | {target:.1f} | " + " | ".join(f"{x:.1f}%" for x in lost) + " |")
    print()
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
