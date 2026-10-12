# Demographics play-test checklist

What the next play-test of the Demographics rule should look at. Since 2026-10-12 the owner's in-game checks no
longer gate a merge: a PR lands on the offline gate (CI, the audits, the golden tests, the harness), adds what only
the game can show here, and the play-test before a release works through the list. Where a build rests on an engine
fact nobody has verified, it ships the preferred version with a self-check line in `debug.log` and names its fallback
below; a BROKEN line means swap the fallback in.

Each PR adds its own section, newest last, and a fixed item is struck through with the commit that fixed it.

## How to run

- **Deploy** per CLAUDE.md, "Play-testing unmerged work" (or from `main`). Check the playset has no Workshop copy of
  the mod.
- **Rule.** The Demographics (Experimental) rule is chosen in the lobby: Disabled (the default, and every release),
  Display only, or Full. Each item names its setting.
- **Console.** Vic3's console has no `effect` command: the census's console is `event te_debug_demog.1`, on the
  player's country, with lettered options (the list is at the top of `events/te_debug_demog_events.txt`).
- **Logs.** Read `debug.log`, not `error.log`. Grep it for `TE_SELF_CHECK` first, then `TE_DEMOG`.

## Self-checks (every game, any rule)

| Line in `debug.log` | When | OK means | BROKEN means | Fallback |
|---|---|---|---|---|
| `TE_SELF_CHECK … primogeniture_scaled` | once a game: `START` when the first state with a farm share between 0.1 and 0.9 takes Primogeniture's farm line fresh (a Primogeniture country's first yearly state pulse), the verdict a week later | the engine sums a script-only type on a state modifier scaled by its multiplier (`added` ≈ `expected`) | `added` reads 0.1 (the multiplier is ignored) or 0 (the type isn't summed): Primogeniture's farm births are wrong in every game | Plan B of `docs/superpowers/plans/2026-10-11-demographics-late-marriage.md`, Task 9 |
| `TE_SELF_CHECK … measure_country_types` | once a game, under Full: `START` when the first measure that moves desired family size goes on in any country (Child Allowance, Honours, Parental Leave, Later Longer Fewer, Birth Limit, the Crash Campaign; the AI's included), the verdict a week later from the capital (`te_debug_demog.10`) | the capital's read of the script-only `state_desired_fertility_mult` rose by the measures' lines its owner gained (`added` ≈ `expected`): a script-only state type on a country static modifier reaches the states | `added` reads 0: the census will never see any measure's types (step 3b reads them) | put each measure's census types on a state modifier in each of the country's states, applied and removed with the country modifier and re-applied by the yearly state pulse (inheritance's rural modifiers' pattern), and keep the interest groups and upkeep on the country |

No `primogeniture_scaled` line after a game's first year means no state took the line fresh: no country had Primogeniture, or the game was continued from a save where every Primogeniture state already held it. Start a new game, or enact the law. A `START` with no verdict means the state changed hands within the week; the check doesn't run again in that game. No `measure_country_types` line means no measure that moves family size went on (start Child Allowance under Pro-Natalist Policy); a `START` with no verdict, that the capital changed hands within the week.

## Late Marriage and Birth Spacing (#906)

1. **Full, a new 1836 game as Britain.**
   - The Population panel's children-per-woman tooltip shows "Late marriage ×0.90" and "women marry at about 26",
     with "Birth spacing ×1.00". The country line reads about 26 and 0%.
   - A Japanese state's Demographics subtab: Birth spacing ×0.80, Late marriage ×1.00, women marry at about 19.
   - A Chinese state: Birth spacing ×0.99.
   - A state in Posen: Late marriage ×0.92 (a share of 0.8), women marry at about 25.
2. **Option l** on the capital after its first census step: `lm=1.000`, `bs=0.000`, `lm_target` near 1 (an
   unincorporated state reads `lm_target=-1.000`), and
   `absorbed_b` holding 0.1 × the capital's agrarian share on top of the laws' own absorbed birth lines.
3. **Disabled, a new game, a farming state in Britain** (Primogeniture). After its first yearly pulse, its birth-rate
   breakdown shows Primogeniture's farm births at +10% × its Peasants' and Farmers' share, as a Laws and Institutions
   line, and no "Cadet Sons Leave the Land" birth line. The modifier still shows its migration line. (The self-check
   above tests the same thing from the log.)
4. **Full, the same state after its first census step:** no Laws and Institutions birth line, Census: Births present,
   and option n's `q_b` at 0.
5. **A split state.** Release or annex part of a state region (debug). At its next census the new state's option l
   shows its sibling's `lm` and `bs`, not the start table's.
6. **A whole state region changing hands** (a debug transfer, or a revolution that wins). At the new state's first
   census, option l shows the old state's last `lm` and `bs` (the region's copy). Option q answers whether
   `on_state_owner_change` still sees the old state's variables: if it does, a follow-up can carry the census's ring
   and medicine through conquests too.
7. **An old save** made under Full before this build: each state's tooltip shows ×1.00 for both practices until its
   next yearly pulse, then its seed.
8. **Fast mode** (option h) for a few clock years: the capital's `lm` moves once a clock year, toward `lm_target`.
9. **`debug.log`:** no error from `te_demog_practice_effects.txt`, the generated `te_demog_pr_*` values, `region =
   sr:` or `state_region = s:` lookups ("Invalid strategic region"), or `te_demog_events.4` fired from the rural
   refresh.
10. **Two yearly plain-text saves of the Full game:** keep them. The harness's `practices-check` (not built yet; the
    late-marriage plan, Task 12 Step 2) compares each state's stepped shares with the model's.
11. Optional, for phase 3: does `every_neighbouring_state` from a British state include a French one?

## Medical Outreach (#929)

1. **Full.** Issue Medical Outreach in a state behind its medicine targets. Once the state has caught up, the decree
   ends on its own; the decree panel names the reason as "This state's medicine is still behind what our technology
   and laws allow", not a raw comparison.
2. **Full, an observer run of a few decades:** AI countries issue it in states behind and let it lapse; few states
   hold it once caught up.

## Family Policy measures (step 3a)

The measures and their panel (`docs/superpowers/specs/2026-10-12-demographics-phase2-consequences-design.md` §3.3-§3.7).
Until step 3b the census reads only Free and Restricted Contraception's means lines, so births don't move for the
others; check the switching, the costs and the politics.

1. **Full, a new game; console the Family & Reproductive Policy law** (or enact it). The Demographics tab's Family
   Policy section, open after the pyramid: "Law in Force" names the law and shows the law's tooltip; each measure the
   law allows is a row with its running cost, "Off" and a Start button; the rest sit dimmed under "Under Other Laws",
   their hover naming the laws that allow them. No label, cost or term cut short ("Honours for Large Families",
   "Restricted Contraception", "Barred to 1915").
2. **Start Child Allowance** (Pro-Natalist Policy): the budget shows a new expense line of about 0.5% of GDP a year ×
   (the 0-14 share ÷ 0.3), weekly; the Devout and Trade Unions gain +1 approval; the term reads "On to <year + 5>";
   the button reads End, greyed, its tooltip "Its five-year term runs to <year>". Each 31 December the expense
   follows GDP.
3. **Honours, Later Longer Fewer, Birth Limit, the Crash Campaign**: authority falls by 25, 50, 100, 100. Sex
   Education: the Ministry of Education's bureaucracy cost +10%. Restricted Contraception: feminist movement support
   up, and (option l) the capital's `fmeans` falls by 0.2; Free Contraception raises it by 0.1.
4. **Birth Limit's button**: Start (two children), Tighten (one child, the modifier swaps at once), then End once five
   years have run, which also ends the Rural Exemption. The Rural Exemption's Start is greyed "Needs Birth Limit in
   force" without it.
5. **The Crash Campaign**: no button ends it; five years to the month after it starts it ends with the "Crash Campaign
   Over" notice, legitimacy recovers its 10, and the row reads "Barred to <year + 10>" until then.
6. **Leaving the law**: with measures on, enact another family law (console). Every measure the new law doesn't allow
   ends at once, each with its "… Ended" notice; under a law that allows it again it starts a new term.
7. **Display only**: the section shows, one line above the rows says the measures act only under Full, and every
   button is greyed with that reason.
8. **An AI country with a measure on** (an observer run of a few decades, Full): a shrinking or ageing AI on
   Pro-Natalist Policy takes Child Allowance or Honours; one in a famine on Population Control takes Free
   Contraception, Later Longer Fewer or Birth Limit; none ends one before five years. Read the country's
   `te_dg_ms_*` in a plain-text save.
9. **A revolution that wins** under Full, the old government holding a measure: by the next 31 December (at once, if
   the engine copies the variables before `on_civil_war_won`) the winner has the measure's modifier and cost again,
   or a notice if its law doesn't allow it.
10. **Every game (Disabled)**: the family laws' AI weights: an AI country in famine moves toward Population Control
    Measures; one whose population shrinks, toward Pro-Natalist Policy. `debug.log`: no error from
    `te_demog_measure_*`, `te_demog_messages.txt`, `te_demog_ms_law_on_action` or `te_debug_demog.10` (the
    self-check's verdict event: an error there would leave a `START` with no verdict, which reads like a capital
    that changed hands).
