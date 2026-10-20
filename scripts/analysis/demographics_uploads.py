#!/usr/bin/env python3
"""Demographics: uploaded minds, the pool beside the census (the owner's calls of 2026-10-19).

Spec: docs/superpowers/archive/specs/2026-10-16-demographics-uploaded-minds-design.md. Under Full, in a country with Mind Backups
and at least one level of the Mind Upload Nexus, a person in longevity care who faces death from infection or chronic
illness uploads instead, within the country's hosting capacity (1,000,000 minds a level). The engine counts the death
(the body is gone) and the ring loses the person as before; the census books the upload into the country's pool of
minds. The pool has no ages and no body: 0.1% a year choose to end, and minds over capacity are archived (frozen) until
capacity returns. The Nexus's output follows the active minds over capacity (the utilisation).

The script twin is common/scripted_effects/te_demog_um_effects.txt with te_demog_um_generated_effects.txt
(scripts/generators/gen_demographics_um.py); demographics_model.step calls Sums and book when its inputs carry the
owner's year (Inputs.uploads). This module holds:

    ic_rates(inp)        each age group's infection and chronic death rate at the model's own multipliers
    Sums                 the late sweep's treated infection-and-chronic sums by age group (te_dg_uma_tic<f|m><g>)
    book(...)            a state's step: eligible deaths, uploads, the upload share, Living to 100 counting uploads
    Pool, census(...)    the country's year on 31 December: endings, capacity, restore, archive, the year's share
    nexus_lines(), nexus_output(...)  the production method's lines and a Nexus's output at a utilisation
    scenario(...)        the harness's run (demographics_harness.py uploads)
"""

import dataclasses
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import demographics_model as M  # noqa: E402
import demographics_params as P  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
_LIVING_GROUPS = [g for g, (start, _n) in enumerate(P.GROUPS) if start < P.LX_LIVING_TO]


def ic_rates(inp):
    """(women's, men's) infection and chronic death rate a year per 100,000 by age group at the model's own multipliers
    (the step's rates before the on-top scales, te_demog_um_group_ic): infection at the adults' ages x the adults'
    factor, as rates_from_multipliers has it, and at most the group's whole rate (the 100,000 cap)."""
    mult = M.cause_multipliers(inp)
    adult = M.infection_adult(inp)
    qf, qm, _ = M.group_rates(inp)
    icf, icm = [], []
    for g in range(len(P.GROUPS)):
        inf = mult["infection"] * adult if g in M.INFECTION_ADULT_GROUPS else mult["infection"]
        icf.append(min(qf[g], P.INFECTION["f"][g] * inf + P.CHRONIC["f"][g] * mult["chronic"]))
        icm.append(min(qm[g], P.INFECTION["m"][g] * inf + P.CHRONIC["m"][g] * mult["chronic"]))
    return icf, icm


class Sums:
    """The late sweep's treated parts' infection-and-chronic deaths at the model's own rates, people x rate per 100,000,
    by calendar age group and sex (te_demog_um_slot, te_demog_um_group_flush): the treated's TQ less what isn't
    infection or chronic illness. demographics_model.lx_slot and lx_pool_deaths add to it."""

    def __init__(self, inp):
        self.icf, self.icm = ic_rates(inp)
        n = len(P.GROUPS)
        self.f, self.m = [0.0] * n, [0.0] * n

    def slot(self, g, gt, ft, mt):
        """A treated part at its biological age group gt, in calendar group g."""
        self.f[g] += ft * self.icf[gt]
        self.m[g] += mt * self.icm[gt]


def treated_shares(lx, inp):
    """(infection, chronic): the treated parts' share of the sweep's deaths from each (te_demog_um_step), from the late
    sweep's base-rate sums (te_demog_lx_cause_deaths'): the multipliers cancel, but for infection's adults' factor."""
    adult = M.infection_adult(inp)
    ce = lx["CE"]
    inf_u = inf_ua = chr_u = 0.0
    for g in range(len(P.GROUPS)):
        u = lx["U_f"][g] * P.INFECTION["f"][g] + lx["U_m"][g] * P.INFECTION["m"][g]
        if g in M.INFECTION_ADULT_GROUPS:
            inf_ua += u
        else:
            inf_u += u
        chr_u += lx["U_f"][g] * P.CHRONIC["f"][g] + lx["U_m"][g] * P.CHRONIC["m"][g]
    t_inf = ce["infection"] + ce["infection_adult"] * adult
    all_inf = t_inf + inf_u + inf_ua * adult
    s_inf = min(1.0, t_inf / max(all_inf, 0.00001)) if all_inf > 0 else 0.0
    all_chr = ce["chronic"] + chr_u
    s_chr = min(1.0, ce["chronic"] / max(all_chr, 0.00001)) if all_chr > 0 else 0.0
    return s_inf, s_chr


def l100_counting(lx, sums, qf0, qm0, u):
    """Living to 100 with an upload counting as living (§4): the state's blended table (demographics_model.lx_tables) with
    the treated's infection-and-chronic deaths x (1 - u), u the share of them that uploaded; women's and men's averaged."""
    out = []
    for sx, qu, tic in (("f", qf0, sums.f), ("m", qm0, sums.m)):
        q = []
        for g in range(len(P.GROUPS)):
            un, t, tq = lx[f"U_{sx}"][g], lx[f"T_{sx}"][g], lx[f"TQ_{sx}"][g]
            q.append((un * qu[g] + tq - u * tic[g]) / max(un + t, 0.00001) if un + t > 0 else qu[g])
        out.append(M.survivors_at(q, P.LX_LIVING_TO))
    return (out[0] + out[1]) / 2


def book(lx, causes, inp, qf0, qm0):
    """A state's step under Full with uploads (te_demog_um_step), after its deaths by cause (demographics_model.
    cause_deaths): eligible = cover x the treated parts' share of the infection and chronic deaths, each slice the step's
    own; uploads = min(the owner's share phi x eligible, its capacity still free); u, the share of the treated's
    infection and chronic deaths that uploaded; the women's share of the uploads (the treated's sums by sex); Living to
    100 counting uploads. The caller takes the uploads off the owner's free capacity."""
    um = inp.uploads
    s_inf, s_chr = treated_shares(lx, inp)
    treated = s_inf * causes["infection"] + s_chr * causes["chronic"]
    eligible = lx["c"] * treated
    uploads = min(um["phi"] * eligible, max(0.0, um["free"]))
    u = uploads / max(treated, 0.00001) if treated > 0 else 0.0
    sums = lx["um"]
    sf, sm = sum(sums.f), sum(sums.m)
    women = sf / max(sf + sm, 0.00001) if sf + sm > 0 else 0.5
    return {"eligible": eligible, "uploads": uploads, "u": u, "women": women, "s_inf": s_inf, "s_chr": s_chr,
            "l100": l100_counting(lx, sums, qf0, qm0, u)}


# ---- The country's year (te_demog_um_country, on 31 December) -------------------------------------------------------

@dataclasses.dataclass
class Pool:
    """A country's minds (te_dg_um_*): active and archived by sex, and last year's figures."""
    f: float = 0.0          # active women's minds (te_dg_um_f)
    m: float = 0.0          # active men's (te_dg_um_m)
    af: float = 0.0         # archived (te_dg_um_af, te_dg_um_am)
    am: float = 0.0
    levels: float = 0.0     # Nexus levels (te_dg_um_lv)
    cap: float = 0.0        # minds it can host (te_dg_um_cap)
    free: float = 0.0       # capacity still free this year (te_dg_um_free)
    phi: float = 1.0        # the share of eligible deaths this year's free capacity hosts (te_dg_um_phi)
    uploaded: float = 0.0   # last year's uploads (te_dg_um_new)
    ended: float = 0.0      # last year's chosen endings (te_dg_um_end)
    demand: float = 0.0     # last year's eligible deaths (te_dg_um_dem)
    util: float = 0.0       # active over capacity (te_dg_um_util)
    share: float = 0.0      # minds over people and minds (te_dg_um_share)

    @property
    def active(self):
        return self.f + self.m

    @property
    def archived(self):
        return self.af + self.am


def _move(n, a, b):
    """n taken from a pair (a, b) in proportion: (taken from a, taken from b)."""
    total = a + b
    if total <= 0 or n <= 0:
        return 0.0, 0.0
    n = min(n, total)
    return n * a / total, n * b / total


def take_uploads(pool, uploads, women):
    """A state's step books its uploads (te_demog_um_step): into the active minds, off the year's free capacity."""
    pool.f += uploads * women
    pool.m += uploads * (1 - women)
    pool.free = max(0.0, pool.free - uploads)


def census(pool, levels, has_tech, demand, uploaded, people):
    """The country's year (te_demog_um_country): 0.1% of the active minds choose to end (call 5); capacity is the Nexus
    levels x UM_PER_LEVEL with Mind Backups, else 0 (call 3); archived minds come back first, into the free capacity, then
    any active minds over capacity are archived (call 7); then the year's free capacity, its share of last year's
    eligible deaths phi (1 with none), the utilisation and the pool's share of people. demand and uploaded are the year's
    sums of the states' steps; people the census's (bodies)."""
    ef, em = pool.f * P.UM_END_RATE, pool.m * P.UM_END_RATE
    pool.f, pool.m = pool.f - ef, pool.m - em
    pool.ended = ef + em
    pool.levels = levels
    pool.cap = levels * P.UM_PER_LEVEL if has_tech else 0.0
    room = max(0.0, pool.cap - pool.active)
    rf, rm = _move(room, pool.af, pool.am)
    pool.af, pool.am, pool.f, pool.m = pool.af - rf, pool.am - rm, pool.f + rf, pool.m + rm
    over = pool.active - pool.cap
    if over > 0:
        xf, xm = _move(over, pool.f, pool.m)
        pool.f, pool.m, pool.af, pool.am = pool.f - xf, pool.m - xm, pool.af + xf, pool.am + xm
    pool.free = max(0.0, pool.cap - pool.active)
    pool.demand, pool.uploaded = demand, uploaded
    pool.phi = min(1.0, pool.free / max(demand, 0.00001)) if demand > 0 else 1.0
    pool.util = min(1.0, pool.active / max(pool.cap, 0.00001)) if pool.cap > 0 else 0.0
    minds = pool.active + pool.archived
    pool.share = minds / max(people + minds, 1.0)
    return pool


def research_multiplier(pool, staffed_levels):
    """The census's cancel of the Nexus's research line (te_demog_um_research): -UM_RESEARCH_PER_LEVEL x the levels x
    their staffing x (1 - utilisation), so the line nets to UM_RESEARCH_PER_LEVEL a staffed level x the utilisation."""
    return staffed_levels * (1 - pool.util)


def devout_on(pool):
    """Call 8, behind P.UM_POLITICS: the Devout's approval falls while the minds pass UM_DEVOUT_SHARE of the people."""
    return P.UM_POLITICS and pool.share > P.UM_DEVOUT_SHARE


# ---- The Nexus's output (call 6) ------------------------------------------------------------------------------------

def nexus_lines(root=ROOT):
    """pm_mind_upload_nexus's goods lines a level at full staffing, {"in": {good: units}, "out": {good: units}}, read from
    the game files (common/production_methods/extra_pms.txt), and its staff a level."""
    text = (root / "common" / "production_methods" / "extra_pms.txt").read_text(encoding="utf-8-sig")
    body = re.search(r"^pm_mind_upload_nexus = \{(.*?)^\}", text, re.S | re.M).group(1)
    lines = {"in": {}, "out": {}, "staff": 0}
    for side, good, n in re.findall(r"goods_(input|output)_([a-z_]+)_add = ([\d.]+)", body):
        lines["in" if side == "input" else "out"][good] = float(n)
    lines["staff"] = sum(int(n) for n in re.findall(r"building_employment_[a-z_]+_add = (\d+)", body))
    return lines


def goods_prices(root=ROOT):
    """Base prices of the Nexus's goods, from the game files and the vanilla snapshot."""
    import json
    prices = {}
    van = json.loads((root / "vanilla_parsed" / "common" / "goods.json").read_text(encoding="utf-8"))
    for good, block in van.items():
        try:
            prices[good] = float(block[1]["cost"][1])
        except (KeyError, TypeError, ValueError, IndexError):
            pass
    for f in sorted((root / "common" / "goods").glob("*.txt")):
        text = f.read_text(encoding="utf-8-sig")
        for good, body in re.findall(r"^(?:[A-Z_]+:)?([a-z_]+) = \{(.*?)^\}", text, re.S | re.M):
            m = re.search(r"\bcost = ([\d.]+)", body)
            if m:
                prices[good] = float(m.group(1))
    return prices


def nexus_multiplier(util, factor, other=0.0):
    """One Nexus good's modifier multiplier under Full (te_demog_um_nexus_good): (1 + the building's other bonuses for the
    good, at least 0) x (utilisation x factor - 1), so with them the good's axis sums to (1 + other) x utilisation x
    factor - 1, and the good comes to the method's line x utilisation x factor x (1 + other): none with no minds."""
    return max(0.0, 1 + other) * (util * factor - 1)


def nexus_output(util, levels=1.0, lines=None, prices=None, other=None):
    """A Nexus's goods a week at full staffing under Full: each line x the utilisation x its factor (P.UM_OUTPUT_FACTORS,
    P.UM_INPUT_FACTORS) x (1 + the building's other bonuses for it, other {good: sum}, none by default), the line x (1 +
    the axis's sum, other + nexus_multiplier); {"out": {good: units}, "in": {...}, "out_value", "in_value"} at base
    prices. Outside Full it is the lines as they are."""
    lines = lines or nexus_lines()
    prices = prices or goods_prices()
    other = other or {}

    def good(g, n, factors):
        o = other.get(g, 0.0)
        return n * (1 + o + nexus_multiplier(util, factors.get(g, 1), o)) * levels
    out = {g: good(g, n, P.UM_OUTPUT_FACTORS) for g, n in lines["out"].items()}
    inp = {g: good(g, n, P.UM_INPUT_FACTORS) for g, n in lines["in"].items()}
    return {"out": out, "in": inp, "out_value": sum(n * prices[g] for g, n in out.items()),
            "in_value": sum(n * prices[g] for g, n in inp.items())}


# ---- The harness's scenario (demographics_harness.py uploads) ---------------------------------------------------------

ERAS = {"era11": "era11", "era12": "era12", "transition": "era12"}


def scenario(era="era11", nexus_levels=5, people=100_000_000, years=60, carriers=None, lines=None, levels_at=None):
    """A rich country as one state (demographics_late's rich state, everyone within reach) at `people`, its late game
    under the era's ladder with Mind Backups and a Nexus of `nexus_levels` full levels from year 0, stepped `years`
    years, the country's census closing each. era11: era 11's ladder (r 0.70) from its own steady state, a counterfactual
    (Mind Backups needs Biological Immortality); era12: Biological Immortality and the pull from their steady state;
    transition: era 11's steady state, then Biological Immortality and Mind Backups at year 0, the way a game reaches
    them. levels_at(t) -> levels overrides the Nexus (a lost or rebuilt Nexus). Returns the yearly rows: people, minds,
    archived, utilisation, uploads, endings, deaths and true deaths per 1,000, Living to 100 and counting uploads, the
    minds' share."""
    import demographics_late as L
    carriers, lines = carriers or L._carriers()[0], lines or L._carriers()[1]
    ladder = L.ERA11 if ERAS[era] == "era11" else L.ERA12
    inp = L.inputs(carriers, lines, techs=ladder | {P.UM_TECH})
    ring = L.start_ring(L.inputs(carriers, lines, techs=L.ERA11) if era == "transition" else inp)
    k = people / ring.people()
    ring.f = [x * k for x in ring.f]
    ring.m = [x * k for x in ring.m]
    ring.pool_f *= k
    ring.pool_m *= k
    M._refresh_denominators(ring)
    ring.total = ring.people()
    levels_at = levels_at or (lambda t: nexus_levels)
    pool = census(Pool(), levels_at(0), True, 0.0, 0.0, ring.people())
    rows = []
    for t in range(years):
        step_inp = dataclasses.replace(inp, uploads={"phi": pool.phi, "free": pool.free})
        out = M.step(ring, step_inp, ring.year + 1)
        um = out.get("um") or {"uploads": 0.0, "eligible": 0.0, "women": 0.5, "l100": None, "u": 0.0}
        take_uploads(pool, um["uploads"], um["women"])
        census(pool, levels_at(t + 1), True, um["eligible"], um["uploads"], ring.people())
        people_now = ring.people()
        lx = out["lx"]
        rows.append({"year": t + 1, "people": people_now, "minds": pool.active, "archived": pool.archived,
                     "util": pool.util, "uploads": um["uploads"], "ended": pool.ended, "eligible": um["eligible"],
                     "cdr": 1000 * out["deaths"] / people_now,
                     "cdr_true": 1000 * (out["deaths"] - um["uploads"]) / people_now,
                     "l100": lx.get("blend", {}).get("l100"), "l100_up": um["l100"], "share": pool.share,
                     "u": um["u"], "elig": lx.get("elig")})
    return rows


# ---- The calibration and the report ------------------------------------------------------------------------------------

# The late methods the output per mind is set against (P.UM_MIND_OUTPUT): the software and digital access buildings'
# era 10-12 methods, whose staff a level the method's own comment counts.
CALIBRATION_PMS = ("pm_machine_learning_assisted_code_generation", "pm_self_improving_AI_systems", "pm_high_bandwidth",
                   "pm_extreme_bandwidth", "pm_semiinfinite_bandwidth", "pm_mind_upload_nexus")


def calibration(root=ROOT):
    """[(method, output a level a week at base prices, staff a level, output a worker)] from pm_costs' comments in the
    game files (the Nexus's staff from its employment lines)."""
    text = (root / "common" / "production_methods" / "extra_pms.txt").read_text(encoding="utf-8-sig")
    rows = []
    for name in CALIBRATION_PMS:
        body = re.search(rf"^{name} = \{{(.*?)^\}}", text, re.S | re.M).group(1)
        out = float(re.search(r"# Total output cost: ([\d.]+)", body).group(1))
        staff = int(re.search(r"# Employment: (-?\d+)", body).group(1))
        if staff <= 0:
            staff = sum(int(n) for n in re.findall(r"building_employment_[a-z_]+_add = (\d+)", body))
        rows.append((name, out, staff, out / staff))
    return rows


def main(args=None):
    """demographics_harness.py uploads: the calibration, the Nexus at full, and the scenarios."""
    years = getattr(args, "years", 60) if args is not None else 60
    print("Output a worker a week at base prices (pm_costs' comments):")
    for name, out, staff, per in calibration():
        print(f"  {name:46s} £{out:>11,.0f} a level, {staff:>6,} staff: £{per:,.1f} a worker")
    full = nexus_output(1.0)
    print(f"A full Nexus level under Full ({P.UM_PER_LEVEL:,} minds): £{full['out_value']:,.0f} a week "
          f"(£{full['out_value'] / P.UM_PER_LEVEL:.1f} a mind), inputs £{full['in_value']:,.0f}")
    for good, n in full["out"].items():
        print(f"  {good:22s} {n:>10,.0f} a week (x{P.UM_OUTPUT_FACTORS[good]})")
    for good, n in full["in"].items():
        print(f"  in: {good:18s} {n:>10,.0f} a week (x{P.UM_INPUT_FACTORS[good]})")
    print()
    print("A country of 100M as one rich state, everyone within reach of longevity care, with Mind Backups:")
    hdr = "  year  people   minds  util  uploads  ended  deaths  true  L100  L100+up  share"
    for era, levels in (("era11", 5), ("era11", 15), ("transition", 5), ("transition", 15), ("era12", 5)):
        print(f"{era}, {levels} levels ({levels // 5} full Nexus{'es' if levels > 5 else ''}):")
        print(hdr)
        for r in scenario(era, levels, years=years):
            if r["year"] in (1, 5, 10, 20, 30, 40, 50, 60) and r["year"] <= years:
                print(f"  {r['year']:4d} {r['people'] / 1e6:6.1f}M {r['minds'] / 1e6:6.2f}M {r['util']:5.2f} "
                      f"{r['uploads'] / 1e3:7.0f}k {r['ended'] / 1e3:5.0f}k {r['cdr']:6.2f} {r['cdr_true']:5.2f} "
                      f"{r['l100']:5.3f} {r['l100_up']:7.3f} {r['share']:6.3f}")
    print("A lost Nexus: era11, 5 levels, 3 lost in year 10, rebuilt in year 20:")
    for r in scenario("era11", 5, years=25, levels_at=lambda t: 5 if t < 10 or t >= 20 else 2):
        if r["year"] in (9, 10, 11, 19, 20, 21, 25):
            print(f"  {r['year']:4d} minds {r['minds'] / 1e6:5.2f}M archived {r['archived'] / 1e6:5.2f}M "
                  f"util {r['util']:4.2f} uploads {r['uploads'] / 1e3:6.0f}k")
    return 0


if __name__ == "__main__":
    sys.exit(main())
