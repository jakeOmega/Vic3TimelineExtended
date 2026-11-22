#!/usr/bin/env python3
"""The settler draw's Python twin (colony people design § 6.3; the owner,
2026-11-22: "Spread by population"). The script is sr_emig_month in
common/scripted_effects/sr_colony_population_effects.txt; test_sr_settler_draw.py
holds both to this rule.

Each month a country sends the step's amount, never more than the open
colonies' free room (the caller's) or 1% of its people, in batches of 500:

1. The share: the month's settlers / the country's people.
2. Each state's due: the share x its people + its carry (what it owed before).
3. The floors, largest due first: each state gives its whole batches while the
   month has batches left; a state the month runs out before keeps its whole
   due, so it comes earlier next month.
4. The remainders (the final review of #1958): the batches the floors leave go
   one each to the largest dues left, and each state keeps what it still owes
   as its carry, below 0 for one that gave a batch more than it owed.

So every month sends its settlers, the carries sum to 0, and each state's
running total stays within a batch of its share. With the floors alone a
country of 48 states at 500 a month sent nothing for a year.

Usage: python3 scripts/analysis/sr_settler_draw.py [AMOUNT] [MONTHS] [POP ...]
"""

import math
import sys

BATCH = 500          # sr_emig_batch_people: 250 middle strata and 250 lower
PEOPLE_CAP = 0.01    # sr_emig_people_cap: at most 1% of the people a month


def month_batches(amount: float, people: float, cap: float = PEOPLE_CAP, batch: int = BATCH) -> int:
    """The month's batches: the amount's, at most `cap` of the people
    (sr_emig_month_batches; the free room is the caller's)."""
    if people <= 0:
        return 0
    return int(min(math.floor(amount / batch), math.floor(people * cap / batch)))


def draw(amount: float, states: list[tuple[float, float]], cap: float = PEOPLE_CAP,
         batch: int = BATCH) -> tuple[list[int], list[float]]:
    """(takes, carries) for one month: the people each state gives (whole
    batches) and what each still owes. `states` is [(people, carry)]."""
    people = sum(p for p, _ in states)
    left = month_batches(amount, people, cap, batch)
    if not states:
        return [], []
    if left <= 0:
        return [0] * len(states), [c for _, c in states]
    share = left * batch / people
    dues = [share * p + c for p, c in states]
    takes = [0] * len(states)
    carries = list(dues)
    # Python's sort is stable: equal dues keep the states' order, as
    # ordered_scope_state's tie order is the engine's.
    for i in sorted(range(len(states)), key=lambda i: dues[i], reverse=True):
        if left < 1:
            break
        give = min(max(math.floor(dues[i] / batch), 0), left)
        takes[i] = give * batch
        carries[i] = dues[i] - give * batch
        left -= give
    for i in sorted(range(len(states)), key=lambda i: carries[i], reverse=True):
        if left < 1 or carries[i] <= 0:
            break
        takes[i] += batch
        carries[i] -= batch
        left -= 1
    return takes, carries


def main(argv: list[str]) -> int:
    amount = float(argv[0]) if argv else 32_000
    months = int(argv[1]) if len(argv) > 1 else 12
    pops = [float(p) for p in argv[2:]] or [4_000_000, 2_000_000, 100_000]
    carries = [0.0] * len(pops)
    totals = [0] * len(pops)
    for _ in range(months):
        takes, carries = draw(amount, list(zip(pops, carries)))
        totals = [t + k for t, k in zip(totals, takes)]
    people = sum(pops)
    print(f"{amount:,.0f} a month for {months} months from {len(pops)} states ({people:,.0f} people)")
    for pop, total, carry in zip(pops, totals, carries):
        fair = months * min(amount, people * PEOPLE_CAP) * pop / people
        print(f"  {pop:>12,.0f}: gave {total:>9,} (its share {fair:>11,.1f}), owes {carry:,.1f}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
