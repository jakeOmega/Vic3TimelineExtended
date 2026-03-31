"""
Heir Education System Simulator
================================
Simulates the heir education monthly pulse system to tune parameters.

Design goals:
1. Add "terrible" tier below "poor" - rulers with no education should usually be bad
2. Slow progression rate (from 5% to 3% per focus per month)
3. Hidden "intelligence" stat (1-5 scale) that multiplies gain chance
4. Adult heirs get pre-initialized based on statistical age expectations
5. "Rebel child" chance: ~8% chance ideology flips opposite at resolution
6. Progress bar max raised from 15 to 20 to accommodate slower progression

Key parameters to tune:
- BASE_MONTHLY_CHANCE: base % per focus per month
- INTELLIGENCE_RANGE: (min, max) intelligence multiplier
- REBEL_CHILD_CHANCE: % chance of ideology inversion
- Trait resolution thresholds and probability distributions
"""

import random
import statistics
from collections import Counter

# ─── System Parameters ───

BASE_MONTHLY_CHANCE = 0.03  # 3% base (down from 5%)
INTELLIGENCE_MIN = 0.5      # worst intelligence (halves gain chance)
INTELLIGENCE_MAX = 1.5      # best intelligence (50% more gains)
# Intelligence is drawn uniformly on [0.5, 1.5] - mean 1.0
# So average heir has same 3% as base, but distribution adds variance

REBEL_CHILD_CHANCE = 0.08   # 8% chance ideology inverts at resolution
PROGRESS_BAR_MAX = 20       # raised from 15

# Trait resolution thresholds: investment -> probability distribution
# Tiers: terrible / poor / average / skilled / exceptional
# Format: {min_investment: [terrible%, poor%, average%, skilled%, exceptional%]}
TRAIT_RESOLUTION = {
    0: [35, 30, 25, 8, 2],    # No investment: mostly terrible/poor
    1: [15, 25, 35, 20, 5],   # Light: still mostly below average
    3: [5, 15, 30, 35, 15],   # Moderate: centered on average/skilled
    5: [2, 5, 18, 45, 30],    # Heavy: mostly skilled/exceptional
    8: [0, 2, 10, 38, 50],    # Extreme: exceptional dominant
}

# Thresholds for resolution (sorted descending for lookup)
TRAIT_THRESHOLDS = sorted(TRAIT_RESOLUTION.keys(), reverse=True)
TRAIT_NAMES = ["terrible", "poor", "average", "skilled", "exceptional"]

# For "no education at all" characters (assign_aptitude_traits_effect)
NO_EDUCATION_DIST = [20, 30, 35, 12, 3]

# Ideology resolution: maps signed ideology score to ideology strength
# Higher absolute values = stronger ideology alignment
IDEOLOGY_THRESHOLDS = {
    # (min_abs, max_abs): description
    0: "neutral",
    1: "leaning",
    4: "strong",
}

# ─── Simulation ───

def generate_intelligence():
    """Generate hidden intelligence score uniformly in [0.5, 1.5]"""
    return random.uniform(INTELLIGENCE_MIN, INTELLIGENCE_MAX)


def monthly_chance(intelligence):
    """Effective monthly gain chance per focus"""
    return BASE_MONTHLY_CHANCE * intelligence


def simulate_education(
    start_age=0,       # 0 = newborn, positive = adult heir starting age - threshold
    education_years=18, # years from birth to adulthood (18 for newborn)
    num_trait_focuses=1, # 0 or 1 (trait focuses are mutually exclusive)
    num_ideology_focuses=1, # 0 or 1
    num_ig_focuses=1,  # 0 or 1
    intelligence=None,
):
    """Simulate one heir's education journey.
    
    Note: Only one trait focus (admin/diplo/military) can be active at a time
    (they are mutually exclusive). Same for ideology and IG focuses.
    Max total focuses: 3 (1 trait + 1 ideology + 1 IG).
    
    Returns dict with final investments and resolved traits.
    """
    if intelligence is None:
        intelligence = generate_intelligence()
    
    chance = monthly_chance(intelligence)
    months = education_years * 12
    
    # If adult heir, pre-initialize investments
    if start_age > 0:
        # Adult heir: simulate what they would have gotten with no active focus
        # (passive gains from events only, or we can give them statistical expected values)
        # Actually: for adult heirs, we pre-initialize based on expected gains 
        # as if they had 1 focus running per category for start_age years
        pre_months = start_age * 12
        # Expected gain per category with default unfocused passive: lower rate
        passive_chance = chance * 0.3  # passive gain is 30% of focused rate
        admin_init = sum(1 for _ in range(pre_months) if random.random() < passive_chance)
        diplo_init = sum(1 for _ in range(pre_months) if random.random() < passive_chance)
        military_init = sum(1 for _ in range(pre_months) if random.random() < passive_chance)
        ideology_init = 0  # no ideology drift without focus
        ig_init = {k: 0 for k in ['radical', 'moderate', 'regressive']}
    else:
        admin_init = 0
        diplo_init = 0
        military_init = 0
        ideology_init = 0
        ig_init = {k: 0 for k in ['radical', 'moderate', 'regressive']}
    
    admin = admin_init
    diplo = diplo_init
    military = military_init
    ideology = ideology_init
    ig = dict(ig_init)
    total = admin + diplo + military + abs(ideology) + sum(ig.values())
    
    # Simulate monthly pulses for education_years
    # Assume player picks: focus on admin, progressive, moderate (reasonable default)
    trait_focuses = ['admin', 'diplo', 'military'][:num_trait_focuses]
    ideology_focus = 'progressive' if num_ideology_focuses > 0 else None
    ig_focus = 'moderate' if num_ig_focuses > 0 else None
    
    for _ in range(months):
        for focus in trait_focuses:
            if random.random() < chance:
                if focus == 'admin':
                    admin += 1
                elif focus == 'diplo':
                    diplo += 1
                elif focus == 'military':
                    military += 1
                total += 1
        
        if ideology_focus and random.random() < chance:
            ideology += 1 if ideology_focus == 'progressive' else -1
            total += 1
        
        if ig_focus and random.random() < chance:
            ig[ig_focus] += 1
            total += 1
    
    # Resolve traits
    def resolve_trait(investment):
        for threshold in TRAIT_THRESHOLDS:
            if investment >= threshold:
                dist = TRAIT_RESOLUTION[threshold]
                return random.choices(TRAIT_NAMES, weights=dist, k=1)[0]
        return random.choices(TRAIT_NAMES, weights=TRAIT_RESOLUTION[0], k=1)[0]
    
    admin_trait = resolve_trait(admin)
    diplo_trait = resolve_trait(diplo)
    military_trait = resolve_trait(military)
    
    # Rebel child check for ideology
    rebel = random.random() < REBEL_CHILD_CHANCE
    if rebel and ideology != 0:
        ideology = -ideology  # flip!
    
    return {
        'intelligence': intelligence,
        'admin': admin,
        'diplo': diplo,
        'military': military,
        'ideology': ideology,
        'ig': dict(ig),
        'total': total,
        'admin_trait': admin_trait,
        'diplo_trait': diplo_trait,
        'military_trait': military_trait,
        'rebel_child': rebel,
    }


def run_simulation(n=10000, **kwargs):
    """Run n simulations and collect statistics."""
    results = [simulate_education(**kwargs) for _ in range(n)]
    
    # Trait distribution
    admin_dist = Counter(r['admin_trait'] for r in results)
    diplo_dist = Counter(r['diplo_trait'] for r in results)
    military_dist = Counter(r['military_trait'] for r in results)
    
    # Investment stats
    admin_investments = [r['admin'] for r in results]
    diplo_investments = [r['diplo'] for r in results]
    military_investments = [r['military'] for r in results]
    totals = [r['total'] for r in results]
    ideology_scores = [r['ideology'] for r in results]
    
    rebel_count = sum(1 for r in results if r['rebel_child'])
    
    return {
        'admin_dist': admin_dist,
        'diplo_dist': diplo_dist,
        'military_dist': military_dist,
        'admin_investments': admin_investments,
        'diplo_investments': diplo_investments,
        'military_investments': military_investments,
        'totals': totals,
        'ideology_scores': ideology_scores,
        'rebel_count': rebel_count,
        'n': n,
    }


def print_trait_distribution(name, dist, n):
    print(f"\n  {name}:")
    for tier in TRAIT_NAMES:
        count = dist.get(tier, 0)
        pct = count / n * 100
        bar = '█' * int(pct / 2)
        print(f"    {tier:13s}: {pct:5.1f}% ({count:5d}) {bar}")


def print_investment_stats(name, values):
    print(f"\n  {name}: mean={statistics.mean(values):.1f}, "
          f"median={statistics.median(values):.0f}, "
          f"stdev={statistics.stdev(values):.1f}, "
          f"min={min(values)}, max={max(values)}")


def print_results(results, label=""):
    n = results['n']
    print(f"\n{'='*60}")
    print(f"  Simulation Results: {label} (n={n})")
    print(f"{'='*60}")
    
    print_trait_distribution("Administrative", results['admin_dist'], n)
    print_trait_distribution("Diplomatic", results['diplo_dist'], n)
    print_trait_distribution("Military", results['military_dist'], n)
    
    print_investment_stats("Admin investments", results['admin_investments'])
    print_investment_stats("Diplo investments", results['diplo_investments'])
    print_investment_stats("Military investments", results['military_investments'])
    print_investment_stats("Total progress", results['totals'])
    print_investment_stats("Ideology score", results['ideology_scores'])
    
    print(f"\n  Rebel child events: {results['rebel_count']} ({results['rebel_count']/n*100:.1f}%)")


def main():
    random.seed(42)
    N = 20000
    
    print("=" * 60)
    print("  HEIR EDUCATION SYSTEM SIMULATION")
    print(f"  Base monthly chance: {BASE_MONTHLY_CHANCE*100:.0f}%")
    print(f"  Intelligence range: [{INTELLIGENCE_MIN}, {INTELLIGENCE_MAX}]")
    print(f"  Rebel child chance: {REBEL_CHILD_CHANCE*100:.0f}%")
    print("=" * 60)
    
    # Scenario 1: Newborn heir, single focus (most common)
    print("\n\n>>> SCENARIO 1: Newborn, 1 trait focus + ideology + IG (18 years)")
    r = run_simulation(N, start_age=0, education_years=18, num_trait_focuses=1)
    print_results(r, "Newborn / 1 focus")
    
    # Scenario 2: Newborn heir, trait focus only (no ideology or IG tutors)
    print("\n\n>>> SCENARIO 2: Newborn, 1 trait focus only, no ideology/IG (18 years)")
    r = run_simulation(N, start_age=0, education_years=18, num_trait_focuses=1,
                       num_ideology_focuses=0, num_ig_focuses=0)
    print_results(r, "Newborn / trait only")
    
    # Scenario 3: Newborn heir, ideology + IG only (no trait focus)
    print("\n\n>>> SCENARIO 3: Newborn, no trait focus, ideology + IG only (18 years)")
    r = run_simulation(N, start_age=0, education_years=18, num_trait_focuses=0)
    print_results(r, "Newborn / ideology+IG only")
    
    # Scenario 4: Adult heir (5 years of pre-education, then 5 years focused)
    print("\n\n>>> SCENARIO 4: Adult heir (pre-age 5 yrs passive, 5 yrs focused education)")
    r = run_simulation(N, start_age=5, education_years=5, num_trait_focuses=1)
    print_results(r, "Adult / 5yr pre + 5yr focused")
    
    # Scenario 5: No education (what random characters get)
    print("\n\n>>> SCENARIO 5: No education at all (assign_aptitude_traits dist)")
    no_ed_admin = Counter()
    no_ed_diplo = Counter()
    no_ed_military = Counter()
    for _ in range(N):
        no_ed_admin[random.choices(TRAIT_NAMES, weights=NO_EDUCATION_DIST, k=1)[0]] += 1
        no_ed_diplo[random.choices(TRAIT_NAMES, weights=NO_EDUCATION_DIST, k=1)[0]] += 1
        no_ed_military[random.choices(TRAIT_NAMES, weights=NO_EDUCATION_DIST, k=1)[0]] += 1
    print_trait_distribution("Admin (no education)", no_ed_admin, N)
    print_trait_distribution("Diplo (no education)", no_ed_diplo, N)
    print_trait_distribution("Military (no education)", no_ed_military, N)
    
    # Scenario 6: Newborn with no focuses active (neglected heir)
    print("\n\n>>> SCENARIO 6: Newborn, NO focuses active (neglected, 18 years)")
    r = run_simulation(N, start_age=0, education_years=18, num_trait_focuses=0,
                       num_ideology_focuses=0, num_ig_focuses=0)
    print_results(r, "Newborn / neglected")
    
    # Intelligence distribution analysis
    print("\n\n>>> INTELLIGENCE IMPACT ANALYSIS")
    for intel in [0.5, 0.75, 1.0, 1.25, 1.5]:
        r = run_simulation(N, start_age=0, education_years=18, num_trait_focuses=1,
                          intelligence=intel)
        admin_mean = statistics.mean(r['admin_investments'])
        total_mean = statistics.mean(r['totals'])
        exc_pct = r['admin_dist'].get('exceptional', 0) / N * 100
        ter_pct = r['admin_dist'].get('terrible', 0) / N * 100
        print(f"  Intelligence {intel:.2f}: avg admin={admin_mean:.1f}, "
              f"total={total_mean:.1f}, "
              f"terrible={ter_pct:.1f}%, exceptional={exc_pct:.1f}%")
    
    # Summary table for implementation
    print("\n\n" + "=" * 60)
    print("  RECOMMENDED IMPLEMENTATION PARAMETERS")
    print("=" * 60)
    print(f"""
    Monthly pulse chance per focus: {BASE_MONTHLY_CHANCE*100:.0f}%
    Intelligence range: uniform [{INTELLIGENCE_MIN}, {INTELLIGENCE_MAX}]
    Effective chance range: {BASE_MONTHLY_CHANCE*INTELLIGENCE_MIN*100:.1f}% - {BASE_MONTHLY_CHANCE*INTELLIGENCE_MAX*100:.1f}%
    Rebel child chance: {REBEL_CHILD_CHANCE*100:.0f}%
    Progress bar max: {PROGRESS_BAR_MAX}
    
    Trait Resolution Thresholds (investment -> [terrible/poor/avg/skilled/exc]):
    """)
    for thresh in sorted(TRAIT_RESOLUTION.keys()):
        dist = TRAIT_RESOLUTION[thresh]
        print(f"      {thresh}+ : {dist}")
    
    print(f"""
    Non-educated character dist: {NO_EDUCATION_DIST}
    
    Adult heir passive initialization:
      - Passive rate = 30% of focused rate per category
      - Pre-simulated for (heir_age - adult_threshold) years
    """)


if __name__ == "__main__":
    main()
