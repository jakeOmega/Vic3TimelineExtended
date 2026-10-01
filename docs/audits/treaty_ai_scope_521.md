# Treaty AI proposal scope correction (#521)

The installed vanilla treaty documentation, quoted in #521 and in
`scripting_best_practices.md`, gives `evaluation_chance` only the evaluating
country as root. The original files contained 103 direct named-scope reads in
22 articles. No engine experiment has established how those missing scopes
behave; this correction follows the documented contract.

“Fatal” below means every positive term depended on the partner. “Partial”
means some root-only positive route existed, but partner bonuses or exclusions
could not be evaluated as written.

| Article | Before | Correction / partner logic |
|---|---|---|
| `disband_company` | Fatal | Base 0.01, +0.09 for major powers; the beneficiary refuses a source of equal or higher rank in acceptance. |
| `seize_company` | Fatal | Base 0.01, +0.04 for major powers; same relative-rank acceptance rule. |
| `minority_protection` | Partial | Base/rank motives retained; protective/domineering beneficiary bonuses moved to acceptance. |
| `free_port_concession` | Partial | Law/rank motives retained; existing domineering and friendly acceptance terms retained. |
| `corporate_concessions` | Partial | Law/rank motives retained; existing domineering acceptance term retained. |
| `enforce_privatization` | Partial | Capitalist/industrialist motives and final wartime multiplier retained; existing cooperative-economy and domineering preferences retained, traditionalist source preference added to acceptance. |
| `religious_mission_rights` | Partial | Own religion law/devout motives retained; same-religion missionary demand refused in beneficiary acceptance, existing domineering preference retained. |
| `demilitarized_zone` | Partial | Base/rank motives retained; existing hostile/domineering acceptance terms retained. |
| `forced_disarmament` | Partial | Base/rank motives retained; existing hostile/domineering acceptance terms retained. |
| `cultural_exchange_program` | Partial | Base/ethnostate motives retained; acceptance selects the other mutual party from first/second country. Existing friendly/hostile preferences retained, conciliatory bonus added. |
| `currency_peg` | Partial | Small-country motive uses own rank; anchor-rank preference moved to pegger acceptance. Inflation motive and final ×0.25 retained. |
| `imposed_currency_peg` | Partial | Base and final ×0.25 retained; existing domineering acceptance term retained. |
| `debt_receivership` | Partial | Base and final ×0.25 retained; existing shared-market and domineering acceptance terms retained. Removes the invalid source-country read as well as other-country reads from proposal evaluation. |
| `nuclear_guarantee` | Partial | Base 0.02 allows a beneficiary to request a guarantee or a smaller armed provider to offer one; armed-major-power bonus retained. Existing protective preference retained in acceptance. |
| `nuclear_security_assistance` | Partial | Base 0.02, own missing-warhead line +0.1, armed-great-power +0.05. Existing recipient missing-warhead preference retained in provider acceptance. |
| `request_influence` | Partial | Base/bloc/rank motives retained; cooperative/conciliatory preferences moved to bloc leader acceptance. |
| `suppress_subject_liberty` | Partial | Base retained; domineering bonus moved to overlord acceptance. |
| `nuclear_disarmament` | Fatal | Base 0.05, +0.1 if evaluator has rivals; existing rival/hostile/friendly/bloc acceptance terms retained, refused custody settlement bonus moved to requester acceptance. |
| `nuclear_program_aid` | Partial | Base retained; existing friendly/shared-bloc acceptance terms retained. |
| `nuclear_program_pause` | Fatal | Base 0.1, +0.15 if evaluator has rivals; existing rival/hostile/friendly/bloc acceptance terms retained. Pause remains considered more often than full disarmament. |
| `join_united_nations` | Partial | Base retained; friendly/shared-bloc sponsor preferences moved to source acceptance, existing recipient preferences retained. |
| `population_transfer` | Partial | Base 0.01 and nationalist-government +0.08; hostile bonuses moved to requester acceptance, friendly requesters refuse. Existing population/cultural-unrest preferences retained. |

Acceptance scores and proposal probabilities have different scales. Moved
preferences use the surrounding acceptance score's scale, not the old
probability numbers. These are starting weights for game validation, not a
claim that observed proposal rates remain identical. `possible`, `can_ratify`,
input filters, effects and article directions are unchanged.

## Static validation

- `python3 treaty_evaluation_scope_audit.py --strict` checks every mod treaty
  file recursively, excluding comments and including quoted expressions.
- Unit tests cover nested/scalar/quoted reads, source lines, BOM, multiple
  articles, legal partner-aware fields, CLI exit codes, the mod tree, positive
  base chances for the four fatal articles, and final monetary multipliers.
- The audit runs in CI. It detects direct reads, not dependencies hidden inside
  scripted triggers or script values. It has no suppression for invalid scopes.

## In-game validation still required

1. Use a save with two countries eligible for a formerly fatal article, such
   as Seize Company (a stronger requester and a weaker company owner) or
   Nuclear Program Pause (a rival with an eligible nuclear programme).
2. Let the AI negotiate under comparable conditions before and after the
   patch. Record whether it includes the article in a proposal; acceptance or
   ratification alone does not verify proposal evaluation.
3. Compare friendly and hostile partners, and small and major requesters.
   Check that acceptance still expresses the intended preferences.
4. For Cultural Exchange, inspect the acceptance breakdown from both parties;
   the attitude and heritage checks must refer to the other country each time.
5. Test both offer and request for nuclear guarantees/security assistance,
   including a non-armed recipient requesting an eligible armed provider.
6. Inspect error/debug logs for undefined scopes, and observe unsolicited
   monetary proposals to assess the retained ×0.25 frequency reduction.

An absence of proposals in a short run is inconclusive: treaty construction
also depends on category selection, diplomatic context, eligibility and the
other article scores. No in-game validation was performed in this environment.
