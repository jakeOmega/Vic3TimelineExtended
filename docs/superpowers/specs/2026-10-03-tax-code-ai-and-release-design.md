# Legislated tax code: AI legislation (package 6) and release validation (package 7)

**Status:** design for owner review, 2026-10-03.
**Authority:** the [tax code design](2026-09-29-legislated-tax-code-design.md) governs. This document refines its §10 (AI) and §13, and the [package plan](../plans/2026-09-30-legislated-tax-code.md) §9–§10, for the code that packages 1–5 built (`docs/systems/tax_code_schema.md`).
**Research:** `.superpowers/sdd/2026-10-02-legislated-tax-code-tasks/research/G_ai_legislation.md` (AI) and `H_validation_docs.md` (validation and docs). Each is git-ignored scratch with file:line evidence, and both are summarised here.
**Out of scope:** the carbon levy, deferred until #674 lands; package 8's catalog expansion; retiring the probe harness, which needs the owner's probe pass and an old-save load in game.

## 1. Owner decisions (2026-10-03)

| Topic | Decision |
|---|---|
| Merge gate | Packages 6 and 7 finish on the branch. #680 then merges behind the default-off rule, still labelled experimental, and the owner play-tests from `main`. Fixes come as follow-up PRs. Package 7 delivers the evidence *instrument* (runbook, setup events, save report, docs); no runtime gate is marked passed without the owner's result. |
| AI promises | The owner asked whether this can follow vanilla's law-negotiation journal entries. §2.8 explains how those steer the AI and gives the equivalent built here. Owner follow-up: let the AI try; if it is still short near the deadline, enact the promise for it. Log met or unmet at every deadline (§2.8). |
| AI customs | The owner first chose "the AI legislates the levels it wants", then asked whether the native tariff controls could be disabled outright: by cancelling the tariff maximum, as Free Trade lacks one, and applying tariffs another way. Decision: **probe first**, bundled with the owner's in-game test. This branch registers the per-good tariff modifier families and extends probe P09 to test both mechanisms. AI customs legislation waits for that result (§2.9). |
| Guide | The Tax Code chapter is chapter 5, right after Banking. It is filed as `04-tax-code.md` to avoid renaming files while other branches edit the guide; the renumbering is issue #682 (§3.6). |

## 2. Package 6: AI legislation

### 2.1 Invariants

1. **One legal path.** The AI calls the same `te_tax_cmd_*` effects, behind the same `te_tax_can_*` triggers, as the player's buttons. Research G found nothing in the command layer that gates on `is_ai`, `GetPlayer` or a GUI scope, apart from `te_tax_cmd_draft_relief_state`'s saved state scope, which the AI does not use. `is_ai = yes` appears only in the AI decision layer and in log verbosity.
2. **No free money, no bypass.** No collection or approval is granted to the AI. It never writes a native rate: the collection writer stays the only writer. When no legal package is viable the AI logs why and lives with borrowing and its native spending responses, as spec §10 asks. One deliberate exception is the owner's: an institution promise the native AI fails to deliver is enacted for it (§2.8). Every such enactment is logged, and the institution's native costs still apply from then on.
3. **Rule-off unchanged.** Every new hook checks `te_tax_code_on = yes`, written positively. The AI-strategy hooks (§2.8) read obligation variables that no rule-off country ever holds.
4. **AI state follows the token rule.** Every `te_tax_ai_*` variable is a schema token: initialised by `te_tax_init_country` (schema version 2, backfilled), never `remove_variable`d, copied at the outbreak with the rest of the code, and reset by the civil-war repair and at release. A loser's cooldown or "AI bill" marker must not block or leak into the winner (research G §10).

### 2.2 Where it runs

- **`te_tax.1` (processor), new rule 1b**, after the fiscal record (rule 1a) and before any transition. It does two things:
  - It updates the fiscal streaks (§2.3) for every migrated country. That is a few comparisons, and it lets a revolution's player-side tokens stay meaningful.
  - For an AI country, it decides whether an AI step is due: an initiative is due (§2.4), an emergency holds, or there is something to manage (an open bill, a held package, or a promise in force). If so, it raises the hidden country event `te_tax.8` with `days` taken from the country's bucket.
  
  `te_tax.1` itself never drafts.
- **Buckets.** `te_tax_ai_phase` is drawn once with `integer_range` at initialisation; it is never redrawn. A literal `if` chain on `phase modulo 4` picks a delay of 5, 12, 19 or 26 days. This spreads the AI's work over the month and off the month-boundary burst, which the perf branch measured at about 5 s in late game.
- **`te_tax.8`** runs `te_tax_ai_step` with ROOT = THIS = the country. That makes force-through's `multiplier = forced_law_through_event_authority_multiplier_medium` resolve correctly (schema "Force through"; research G Q1). The step is called nowhere else, and it does at most one support refresh per execution, except for the offer chain (§2.7).

### 2.3 Signals

Each is read in the processor on the 1st or in the step, never from a GUI. The thresholds copy vanilla's own tax-AI defines (`common/defines/00_ai.txt:209-218`, 1.14.5).

| Signal | Read | Use |
|---|---|---|
| Fiscal record | `te_tax_fisc_deficit`, `_surplus`, `_bur_ok` (exists, rule 1a) | The support model rewards a revenue raise only when a fixed deficit is recorded (+8) and penalises one in recorded surplus (−4). So the AI raises only on a recorded deficit, or in an emergency. |
| Deficit streak | new token `te_tax_ai_def_streak`: consecutive 1sts with a recorded deficit, 0 otherwise | Hysteresis for raises |
| Surplus streak | new token `te_tax_ai_sur_streak`: consecutive 1sts with a recorded surplus and R at or above the cut ratio | Hysteresis for cuts |
| R | `income / max(1, total_expenses)` (both precedented) | Raise at R ≤ 0.9 without significant debt, ≤ 1.1 with it. Cut at R ≥ 1.25 without debt, ≥ 1.5 with it. This is vanilla's dead band. |
| D | `principal / credit` (vanilla's own form); significant at ≥ 0.1 | Picks the ratio pair above |
| G | `scaled_gold_reserves` | No raise for need while reserves are at least 10% full (vanilla's rule) |
| Emergency | `in_default`, or D ≥ 0.5, or `taking_loans` with `weeks_until_bankruptcy < te_tax_ai_emergency_weeks` (30) | Skips the streak, the stagger and the cooldown; allows the minor emergency bill and force-through |
| Promised surplus | a kind-4 obligation in force (states 7, 2, 3) | Counts as a revenue need until it is fulfilled. The AI's own bills deliver it (§2.8). |

Every threshold and count is a named script value in `common/script_values/te_tax_ai_values.txt`. Where a `define:NAI|…` read is proven it can replace a copied constant; until then each value cites its define line.

### 2.4 What the step does, in order

1. **Held packages.** A conflicting one (state 2) is released. A missed one (state 3) is rescheduled if `te_tax_can_package_reschedule` holds, else released. An AI that ignored held packages would fill both slots and could never pass again.
2. **Promises in force.** At most one promise is handled per step, and only one the next monthly check would otherwise breach: a delivering promise whose deadline falls at the next check and whose condition does not hold, or a maintaining promise one failing check short of its grace whose condition still fails.
   - **An institution promise (kind 1) is enacted** (§2.8), and the step logs `ai_obl_enacted`.
   - **A balance promise (kinds 2 and 4) is renegotiated.** A balance cannot be enacted, so the AI accepts −2 approval and −1 trust rather than the breach's −5.
   
   AI promises are therefore never breached by neglect. **This changes the answer to the PR's owner question 1** (is renegotiation always the cheaper exit?), so the owner rules on both together.
3. **An open bill.** Each bill is introduced by this step, because an AI country has no other drafter.
   - Pass if `te_tax_can_pass` holds.
   - If every line holds except legitimacy, and the native tax level is not `medium`, the native AI has raised its level since the last pin and is paying −10/−20 legitimacy for it (research G finding 4). The step logs `reason=legitimacy_native_level`, and the next processor re-raises `te_tax.8` for the 2nd, the day after the pin, instead of the bucket day.
   - Otherwise accept the best offer (§2.7).
   - Otherwise, in an emergency, force it through if `te_tax_can_force_through` holds.
   - Otherwise, withdraw when the bill cannot pass: `te_tax_open_clout` is at or below the passage share and no force path exists, or it has been open `te_tax_ai_bill_patience` (6) months. On withdrawal the step sets the failure cooldown and logs the reason.
4. **No bill.** This branch runs only when an initiative is due, or an emergency holds, and:
   - the cooldown has passed;
   - no package the AI passed is still waiting to commence (except in an emergency);
   - no draft is open. An AI draft is opened, used and closed within one step.
   
   Pick one template (§2.5), build the draft with `te_tax_cmd_draft_*`, introduce it, then evaluate it in the same execution:
   - Introduction runs the real support refresh. If `te_tax_open_clout` (committed plus persuadable) cannot reach the passage share and no force path exists, withdraw at once. Introduction and withdrawal carry no political cost (research G finding 2).
   - Then set the failure cooldown and log `ai_no_viable reason=<support|legitimacy|slots|authority>`. The log fires once per episode, with a marker reset when a bill passes or the need ends.

An initiative is due when `(te_history_month_index − te_tax_ai_phase) modulo te_tax_ai_cadence_months = 0` (cadence 3). Management (steps 1–3) runs monthly while there is something to manage.

### 2.5 Templates

The set is bounded. Exactly one template is built per initiative, and a template is a drafting aid, not law.

| Template | When | Draft |
|---|---|---|
| T1 Raise | Deficit streak ≥ `te_tax_ai_need_months` (3), the raise rule of §2.3 holds, and no emergency | +1 index step on the one or two cheapest instruments (pre-score below), due now + 3 |
| T2 Emergency | Emergency | A minor bill: at most 2 provisions, each at most 2 steps, on the cheapest instruments, due now + 2 (15-day debate) |
| T3 War levy | At war, and T1's or T2's need holds | +2 steps on the cheapest instrument, with a 24-month sunset, so the levy reverts by itself |
| T4 Extend | A raise of the AI's own expires within 6 months and the raise rule still holds | Restates the rate with a new sunset |
| T5 Cut | Surplus streak ≥ `te_tax_ai_surplus_months` (6), the cut rule holds, and reserves are full | −1 step on the instrument with the largest clout-weighted grievance, never below 0 |
| T6 Luxury goods | T1's need holds, the consumption rate is above 0, and fewer than `te_tax_ai_max_goods` (4) catalog goods are taxed | Tax 1–2 untaxed `luxury`-category goods (vanilla's AI weights luxury ×2, staple ×0.5). T1 and T6 compete on pre-score |

No template touches customs until the customs probe decides the mechanism (§2.9).

**Pre-score** (generated, one value per instrument, read only by the step): the clout-weighted political cost of a +1 step. That is Σ over the country's non-marginal groups of `ig_clout` × (10 × ΔL × exposure − 5 × P(ig) × progressivity sign × ΔL), the support model's material and ideology terms for one step, with the same `EXPOSURE` and `te_tax_ideo_p_<ig>` the bill refresh uses.

An instrument is excluded when:
- it is at its maximum;
- the draft-readiness rules would refuse it (Traditionalism: no wage or dividend tax);
- it is the consumption rate and no catalog good is taxed;
- the AI cut it in the last `te_tax_ai_reverse_months` (24), or, for a cut, raised it then.

No template touches relief or the state list. Relief offers can still add relief (§2.7).

### 2.6 Evaluation route

There are two ways to evaluate a draft:
- **Draft-scoped support values**, a second copy of the support model on `te_tax_dr_*`: about 350 values and 1,600 generated lines, and a duplicate model to keep in step.
- **Introduce and observe.** The bill's own refresh scores the bill, the step reads the result, and it keeps or withdraws the bill.

**Chosen: introduce and observe.** The AI is then judged by exactly the model the player sees, and introduction and withdrawal cost nothing politically. The pre-score only picks which bill to try. One refresh costs about 10⁴ reads (research G Q2), so the step allows one per execution.

### 2.7 Offers

Offers reach the AI as they reach the player (`te_tax_gen_offer_select`, at each refresh). The step accepts at most one per execution. Each acceptance opens a new revision and refreshes support. The step then re-raises `te_tax.8` the next day, at most `te_tax_ai_max_offers` (3) times a month, so a bargain completes within days. Acceptance stops once the committed share is above the passage share: the AI never concedes more than it needs.

- **Order:** persuadable groups first, since they commit on acceptance, by clout, largest first. Then opposed groups, whose concession raises the open clout.
- **Clauses:** a softened raise or an untaxed staple is accepted while the bill still raises revenue (`te_tax_dl_revenue > 0`) or, for T5, still cuts. Agricultural relief is accepted outside an emergency only.
- **Promises:**

  | Kind | Accepted only when | Delivered by |
  |---|---|---|
  | 1, institution level | `bureaucracy ≥ 0` and `approaching_bureaucracy_shortage = no` | the native AI, steered by the institution hook (§2.8) |
  | 2, bureaucracy balance | `bureaucracy > 0` and no approaching shortage | the native AI, which already targets a bureaucracy ratio of 1.2 (`00_ai.txt:767-769`) |
  | 4, fiscal balance | the bill raises revenue and no emergency holds | the AI's own revenue bills (§2.3, promised surplus) |
  
  Kind 3 (military wages) is never offered. The native AI would undo a wage cut (research G Q4).

### 2.8 How the AI keeps its promises

**The owner's question.** Vanilla's negotiation journal entries (`common/journal_entries/00_negotiation_quests_je.txt`) do not steer the AI by themselves. AI-weight *scripts* read them:
- `wanted_army_size_script_value` (`common/script_values/ai_script_values.txt:308-320`) adds the promised army size while `je_negotiate_army_quest` is active, so the AI builds barracks.
- `ai_has_enact_weight_modifier_journal_entries` (`common/scripted_triggers/00_ai_triggers.txt:166`) raises the AI's weight for a law a petition journal entry asks for.

The journal entry is the record; the script that reads it is what changes the AI's behaviour.

**The equivalent here.** A tax promise's obligation slot already is that record, and the Tax Code panel already shows it. So no extra journal entry is needed, and one would not fit anyway: a journal entry type can be active only once per country, and there are four slots. Instead, the AI-strategy scripts read the obligation:

- **Institution promises (kind 1).** While any obligation of kind 1 with arg *x* is bound, delivering or maintaining (states 7, 2, 3), `institution_scores.<institution x>` gets `+ te_tax_ai_promise_institution_score` (200).
  - Maintenance needs the boost too: its grace is 1, and the native AI degrades institutions at spending ratio 2.0.
  - The native AI then expands the institution at native speed (about one level a year) and native bureaucracy cost. The tax code never calls `change_institution_investment_level`, which also sidesteps the open question of whether that effect sets a level at once (P16).
  - **Where the boost goes:** only into the mod's existing `INJECT:ai_strategy_default`, whose `institution_schools = { value = 10 }` and `institution_health_system = { value = 10 }` gain the `if`.
  - **Not into the political agenda strategies,** even though they score schools and health themselves (`common/ai_strategies/03_political_strategies.txt:83, 255, 454, 656, 834`). Whether an `INJECT:` into a strategy's nested `institution_scores` sums or replaces the block is unread. If it replaces, it would drop vanilla's other institution scores in rule-off games too.
  - **Untested:** whether the default's boost reaches a country whose political strategy declares the same institution. The enactment fallback below covers either case, and the deadline log measures how often the native AI delivered on its own.
- **Bureaucracy promises (kind 2):** accepted only when they already hold, and the native AI keeps them by its own thresholds. No hook.
- **Fiscal promises (kind 4):** the promised-surplus signal (§2.3) keeps the AI legislating revenue until the surplus streak delivers.

**Enacting a promise the native AI missed** (owner, 2026-10-03). The step checks a promise when the next monthly check would breach it (§2.4 step 2):
- a delivering kind-1 promise one month before its deadline with the delivered level below the target;
- a maintaining one whose level has fallen below the target.

For either, the step runs `set_institution_investment_level = { institution = <x> level = <target> }` and logs `TE_TAX ai_obl_enacted kind=1 arg= target= level=`.
- **No time to deliver if P16 says "target".** If probe P16 shows the effect only sets a target that expands at native speed, one month is too late. The lead is a named value (`te_tax_ai_enact_lead_months`, 1) for the play-test to raise.
- **Costs and verification are untouched.** The institution's native bureaucracy cost applies from then on, and the monthly check still verifies the delivered level.
- **Other promises are renegotiated.** Kinds 2 and 4 cannot be enacted; the AI renegotiates them before a breach.

**Deadline logging, for every country.** When a delivering promise reaches its deadline month, the monthly check writes `TE_TAX obl_deadline result=met|unmet kind= arg= target= level= ai=yes|no country=` before it acts. One line is written per promise and deadline, for player and AI countries alike, so the owner can see how often the AI meets its promises on its own. `level` is the measure the verifier read: the delivered institution level, or 1 or 0 for a balance.

### 2.9 Customs: probe first

**Today** (Task 15): on the 1st the customs sync finds the market's level differs from the code's, re-asserts the code's, and counts a retry. After `te_tax_customs_adopt_after` (4) consecutive retries it adopts the market's level into the code. The counter cannot tell "the setter was refused" (a treaty ban, a cooldown) from "the re-assert took and the native AI moved the level again". So a level the native AI keeps choosing becomes law in four months without a bill (research G finding 7).

**The owner's alternative: disable the native control at its source.**
- **How Free Trade does it.** The other trade laws carry a maximum tariff (`state_tariff_import_add` / `_export_add`, "Maximum Tariffs on Imports/Exports"; mercantilism and protectionism 0.5). The applied tariff is the level's fraction of that maximum: 0.25, 0.5, 1.0 (`TARIFF_LEVEL_EFFECT_*`, `common/defines/00_defines.txt:648-650`). Free Trade has no maximum (`common/laws/01_trade_policy.txt:96-139`), so every level collects nothing.
- **Why the per-good route is untested.** Probe P09 applied the per-good families `country_grain_{import,export}_tariffs_rate_add` and `country_grain_{min,max}_import_tariffs_level_add`. The load rejected them: "Unknown modifier type … potential dynamic modifier type definition missing from the database" (ledger row 14). That is the message `docs/guides/scripting_best_practices.md` gives for a dynamic pattern with no registration, and neither vanilla's nor the mod's `common/modifier_type_definitions/` registers these families. So their behaviour is untested.

Once registered, there are two candidate mechanisms:
1. **Lock.** The writer pins each good's minimum and maximum level to the enacted level, so the engine refuses the buttons and, if bounds bind it, the native AI.
2. **Carrier.** A rule-gated static modifier cancels the trade law's maxima on a code country, Free Trade's effect, and per-good rate modifiers collect the legislated tariffs. Whether `_rate_add` raises a good's maximum, still scaled by the level, or its applied rate is unknown.

**Decision: probe first** (owner, 2026-10-03), run with the owner's in-game test after the merge. This branch:
- registers the six per-good families for the probe's goods (grain, and one industrial good) in a new `common/modifier_type_definitions/te_tax_probe_modifier_types.txt`. A registration alone changes nothing: only the probe applies these modifiers;
- adds probe options for the lock (min = max on grain at a chosen level) and the carrier (maxima cancelled plus a grain rate);
- adds runbook steps for what to observe: the tariff buttons, the market's tariff tooltip, the Budget's tariff income, grain trade, and whether an AI market owner's grain level moves.

Until the result is in:
- **The customs option keeps** re-assert and adoption, documented as experimental.
- **AI countries legislate no customs.** Their tariff path is the native AI plus adoption, documented as a known limitation in the guide and the ledger.
- **What follows the probe.** A follow-up PR builds whichever mechanism passes, registered for every tradeable good by `gen_tax_code.py`, and gives the AI its customs template. With the lock there is no native wish to read, so the template uses rules of its own. The next-day verify path in this design's first draft is dropped.

### 2.10 The native tax level

The pin to `medium` stays, and owner question 2 (measure AI drift in an observer run) stays open. Package 6 adds two things:
- the passage retry the day after the pin (§2.4 step 3);
- a per-year drift summary for AI countries, the drift counters' change since the year began, which the observer run reads.

A rule-gated AI strategy that pins `desired_tax_level` would displace each country's real administrative strategy (research G Q9), so it is not used.

### 2.11 Civil wars and new countries

- **New tokens.** `te_tax_ai_phase`, `te_tax_ai_def_streak`, `te_tax_ai_sur_streak`, `te_tax_ai_next_month` (cooldown), `te_tax_ai_tpl` (the open bill's template, 0 none), `te_tax_ai_bill_month`, `te_tax_ai_noviable_logged` and `te_tax_ai_offers_month`/`_count`. Each per-instrument mark `te_tax_ai_last_<key>` records the month and direction of the AI's last change to that instrument, for the reverse window.
- **Outbreak copy.** The new tokens are added to the generated copy list, so the 165-token count test changes.
- **Reset.** The rebels' and the winner's AI state is reset at the repair (no open bill survives it) and at release.
- **Rebels.** Rebels are AI, often below 25 legitimacy, and may hold up to two inherited packages. They log `ai_no_viable reason=legitimacy` once per episode and never loop.

### 2.12 Logging and debugging

- **One summary line per AI action:** `TE_TAX ai_<verb> tpl= R= D= G= def= sur= country=`, with verbs `introduced`, `passed`, `forced`, `withdrawn`, `accepted`, `released`, `rescheduled`, `renegotiated`, `obl_enacted` and `no_viable`.
- **Gating.** The commands' own `debug_log` lines become player-only (`is_ai = no`). With about 100 AI countries legislating, `debug.log` would otherwise flood, and the AI summary line replaces them.
- **Console.** `te_tax_debug` gains options that:
  - run the AI step now on the console's country;
  - print its signals and pre-scores;
  - force a deficit streak, so a tester can watch a full AI bill in one session.
  
  The `te_debug_gw.1` option `l` is the precedent.

### 2.13 Performance

- An AI country's step runs monthly only while it has something to manage, otherwise once a quarter per country, on bucket days.
- Each execution does at most one support refresh (≈ 10⁴ reads) and one snapshot, except during the offer chain.
- The processor gains only the streak update and one event raise.
- The owner measures with the script profiler; the recipe is in commit 6815868c on the perf branch, and the runbook repeats it. Budgets to watch:
  - the month-boundary tick does not grow measurably with the rule on, against a rule-off control;
  - the AI step's daily cost stays under the processor's.

### 2.14 Tunables and timing

The values below are first estimates, every one a named script value. Under the default cadence, from the onset of a deficit (research G's days-to-threshold table):

| Path | Detect | Debate and pass | Commence | Onset to new rates |
|---|---|---|---|---|
| Normal raise (streak 3, cadence 3) | 61–92 d | 30 d, then the next step: 28–62 d | intro + 89–92 d | ≈ 150–245 d |
| Emergency (minor, no stagger) | 0–31 d | 15 d: 28–31 d | intro + 2 months | ≈ 60–92 d |
| Cut (surplus 6) | 152–184 d | 28–62 d | + 89–92 d | ≈ 9–11 months |

Vanilla's AI rides out a deficit on 20 weeks (140 d) of reserves (`WAGE_CUT_MIN_WEEKS_OF_GOLD_RESERVES`, `00_ai.txt:33`). The normal path is slower than that, which is why the emergency trigger sits at 30 weeks to bankruptcy and uses the minor bill.

| Value | Default | Value | Default |
|---|---|---|---|
| `te_tax_ai_cadence_months` | 3 | `te_tax_ai_need_months` | 3 |
| `te_tax_ai_surplus_months` | 6 | `te_tax_ai_raise_ratio` / `_debt` | 0.9 / 1.1 |
| `te_tax_ai_cut_ratio` / `_debt` | 1.25 / 1.5 | `te_tax_ai_debt_significant` | 0.1 |
| `te_tax_ai_reserves_full` | 0.1 | `te_tax_ai_emergency_debt` | 0.5 |
| `te_tax_ai_emergency_weeks` | 30 | `te_tax_ai_cooldown_months` (after commencement) | 12 |
| `te_tax_ai_fail_cooldown_months` | 6 | `te_tax_ai_bill_patience` | 6 |
| `te_tax_ai_max_offers` | 3 | `te_tax_ai_levy_sunset` | 24 |
| `te_tax_ai_reverse_months` | 24 | `te_tax_ai_max_goods` | 4 |
| `te_tax_ai_promise_institution_score` | 200 | `te_tax_ai_enact_lead_months` | 1 |

### 2.15 Tests

The new file is `test_tax_code_ai.py`, with additions to the existing files. It checks that:
- every AI entry point is rule-gated, and `is_ai` appears only in the AI files and in log gating;
- the step calls only `te_tax_cmd_*` effects inside their own `te_tax_can_*` triggers, and no native setter;
- `te_tax.8` is raised only by the processor and the debug event, and force-through is called only from `te_tax.8`;
- every `te_tax_ai_*` token is initialised, copied at the outbreak, reset at the repair and at release, and never removed;
- the template table and the threshold pairs are pinned, as `test_gw_ai_policy_table.py` pins the Global Warming AI;
- the institution hook sits only in `INJECT:ai_strategy_default`, on schools and health, and reads only obligation variables;
- the enactment of a missed promise runs only for an AI country's kind-1 promise, in `te_tax.8`, and logs `ai_obl_enacted`;
- the monthly check writes exactly one `obl_deadline` line per delivering promise in its deadline month;
- the per-good tariff registrations name only the probe's goods, and nothing outside the probe harness applies those modifiers;
- AI templates never call a customs command;
- the commands' `debug_log` lines are player-gated.

## 3. Package 7: release validation and documentation

The agents cannot run the game. Package 7 makes each runtime gate runnable and checkable by the owner, and documents the release; it marks none of them passed.

### 3.1 Evidence matrix and known limitations

`docs/testing/tax-code-capability-ledger.md` gains:
- the package plan §10 scenario table (S1–S12, plus S13 for AI legislation), each row with its play-test ids and empty result and evidence cells;
- one reconciled list of the open probes;
- a "Known limitations" section, made from research H §3's limitation items and the PR's parked items.

The PR body's claim that three of those items are already in the ledger is corrected.

### 3.2 Play-test runbook

New file: `docs/testing/tax-code-playtest.md`. It numbers about 45 checks, PT-01 onwards: research H's 37 deduplicated items, plus the AI, promise-enactment and customs-probe checks. Each check gives:
- its setup and console commands;
- the `TE_TAX` log tags it expects;
- a save-report command where one applies;
- a pass/fail cell;
- the scenario row it serves.

It adds the scenarios research H found missing: save/load at every lifecycle stage, a moved capital, AI fiscal crisis, an observer run, and loading an old save. It also carries the profiler recipe and the PR's 15 items, highest risk first. The existing PR checklist points to it.

### 3.3 Console setup events

`events/te_tax_debug_events.txt` (namespace `te_tax_debug`, kept) gains setup options, so the scenarios that otherwise need months of play become runnable:
- a package with a 1-month sunset;
- a dispatch skip that forces a missed package;
- an external-version bump that forces a conflict;
- naming a relief state;
- the AI options of §2.12.

Each is console-only and carries the `REVIEWED` orphan suppression the current event uses. The customs probe (§2.9) extends the existing P09 harness (`te_debug_tax*`, the `te_tp_grain_*` probe modifiers), not this namespace.

### 3.4 Save report

New script: `scripts/analysis/tax_code_save_report.py`. For one country it prints:
- the enacted code (rates, sunsets, goods, relief);
- the packages, the draft or bill, and the obligations and trust;
- the drift counters;
- the history ring with each kind's name, from the schema.

`--diff A B` compares two saves (a civil war before and after, or a save/load round trip) and gives a verdict per group.

It reads **plain-text** saves with a streaming extractor of `te_tax_*` names and the taxation-law and amendment records, since the owner's recent saves are plain text (research H §1). It reads zipped binary saves through `save_country_probe.py`'s decoder, which gains a list reader. `test_tax_code_save_report.py` tests it on a small synthetic text fixture. No full text-save parser is written.

### 3.5 Debug-tag index and cheap fixes

- **Tag index.** The schema doc's "Debug lines" section lists every `TE_TAX` tag, about 56 plus the AI tags. A test fails on any tag the doc does not list.
- **Cheap fixes,** from research H §3:
  - the one-day-slip sentence in the How text and the commencement concept;
  - the history kind-18 wording;
  - the locked tab's `$je_tax_code$` splice;
  - "Customs Levels";
  - the stale research citations in ledger and schema;
  - the generator docstring and its `auto_generated_files.md` row.

### 3.6 Player guide chapter

- **File.** A new chapter `04-tax-code.md`. It sorts after `04-banking.md`, so the PDF, which numbers chapters by position, prints it as chapter 5 with no other file renamed. A full renumber would rewrite about 265 links across the guide and conflict with every open branch that edits it. Issue #682 renumbers the files once the guide is quiet.
- **Index.** The README index lists it as 5 and shifts the later numbers. No chapter refers to another by its number in prose; only links by file name are used.
- **Outline.** Research H §4b gives the outline, filled with what packages 6 and 7 built, and every UI name is single-sourced from loc (§4c table).
- **Marked experimental.** The chapter opens with the rule, labelled experimental and off by default. It documents customs as the experimental option, and the carbon levy not at all.
- **AI section.** It says how AI countries legislate, in player terms: when they raise or cut, what they concede, and that they keep their promises or renegotiate them.
- **Also updated:**
  - `01-introduction.md` (the rule row),
  - `16-reference.md` (the system and rule rows),
  - `05-politics.md` (the taxation-law mentions under the rule),
  - the README index.
- **Then:** rebuild the PDF; run the style lint with `--strict`.

### 3.7 System docs

- `docs/systems/journal_entry_systems.md`: a Tax Code section. The file is CRLF, so it is edited with line endings preserved.
- `docs/guides/gui_modding_guide.md` (CRLF): the right-click-menu and Budget gate rows.
- The schema doc: an AI section, its Files table rows, and the new tokens in the schema table.
- `docs/guides/python_tools.md`: the save-report row.
- `docs/README.md`: an index line for `docs/testing/`.
- `docs/systems/mod_systems.md`: the on-actions row and an AI line.
- The root README: the rule bullet.

### 3.8 Release gate

1. Merge `origin/main`.
2. Run every `ci.yml` step and `gen_tax_code.py --check`.
3. Rewrite the PR body: summary, a "Player guide" line naming the chapter, a link to the evidence matrix, known limitations, and the owner questions, with question 1 updated per §2.4 step 2.
4. Mark #680 ready for review.
5. Merge only on the owner's word.

The harness retirement stays out of this branch. Research H §6's corrected removal list goes into the runbook for later.

## 4. Unknowns that become play-test items

| Unknown | Where it matters | Fallback |
|---|---|---|
| Whether the default strategy's institution boost reaches a country whose political strategy scores the same institution | §2.8 | The enactment fallback; the deadline log measures it |
| Whether the native AI keeps moving an inert tax level (P14) | §2.10, AI passage | Owner question 2 |
| Whether `trigger_event` takes a computed `days` | §2.2 | A literal `if` chain (the design's default) |
| Whether the per-good tariff families work once registered, and which of lock or carrier holds | §2.9 | Keep re-assert and adoption; AI customs stays native |
| Whether `set_institution_investment_level` sets the level at once or a target (P16) | §2.8 enactment | Raise `te_tax_ai_enact_lead_months` |
| AI pre-score versus real support: does the cheapest instrument usually pass? | §2.5 | Retune the pre-score weights; the withdraw path bounds the cost |
