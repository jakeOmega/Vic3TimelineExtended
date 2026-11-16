# Power Bloc Identities: Play-Test List

What only the running game can show for the Creditors' Consortium and the Research Commons
(design: `docs/superpowers/specs/2026-11-16-power-bloc-identities-design.md`). Nothing here gates a merge;
the play-test before a release works through it. Each self-check prints one `TE_SELF_CHECK OK|BROKEN <name>`
line to `debug.log` once a game; the fallback for each is in its table.

## Creditors' Consortium

System: `docs/systems/mod_systems/power_blocs.md` § "Creditors' Consortium". Script: `te_creditors_consortium_*.txt`.
The console event `event te_debug_cc.1`, as a member or the leader, reads out the country's place in the consortium; its
option b sends the default call to the leader as if the member had defaulted, and option c runs a Development Lending
pulse. Play under the Banking System game rule set to Enabled (the Full monetary layer); the identity is hidden otherwise.

| # | Check | How | Expected |
|---|---|---|---|
| CC1 | The identity shows and founds | Found a bloc as a country with a National Bank, no Command Economy, not in default | Creditors' Consortium is offered, with the Trade League icon as a placeholder; a country without a National Bank sees it greyed with the founder line |
| CC2 | The identity hides with the rule | Switch the Banking System rule to Simplified mid-game | No new bloc can pick it; an existing consortium keeps its name, and no member's guarantee shows in its premium breakdown |
| CC3 | The standing guarantee | A member with debt, in the Banking tab's premium breakdown | A Monetary Arrangements line cuts its premium; the leader's own premium rises by a share of it |
| CC4 | The default call | `te_debug_cc.1` option b as a member, or a member's real default | The leader gets "A Member Defaults" with the options its Conditionality tier allows, each listing the terms |
| CC5 | The member's answer | Rescue from the leader | The member gets "The Consortium's Terms"; Accept moves the money (both treasuries) and makes the treaties in the diplomacy panel; the leader gets "Our Terms Are Accepted" |
| CC6 | A refusal by the leader | Refuse in `te_cc.1` | The bloc loses 20 cohesion at once, the leader carries the Reneged modifier, no member's premium shows the guarantee for five years, and the member gets "Our Bloc Leaves Us to Our Creditors" |
| CC7 | A refusal by the member | Refuse in `te_cc.2` as a player member | It stays in default; it may leave the bloc at once whatever the leverage; no guarantee for ten years, also after rejoining |
| CC8 | Structural adjustment | After a rescue with the adjustment term, as the leader, open the member's diplomacy actions | Impose Law offers the leader's economic system, trade policy and tax laws the member lacks; it stops once the receivership ends |
| CC9 | The receivership's exit | A member in receivership that recovers | It ends after the months the tier gives (12 to 36) out of default with debt under a quarter of the ceiling; the remittance stops |
| CC10 | Development Lending | A consortium with the group and members on both sides of the bloc's GDP per head; `te_debug_cc.1` option c | The richer members' investment pools fall and the poorer ones' rise by the same total; from tier II the poorer members carry the Development Lending construction modifier |
| CC11 | The law locks | As a consortium's leader, open the law panel | Command Economy and abolishing the National Bank are greyed with "We do not lead a Creditors' Consortium" |
| CC12 | The Debt Conference | Convene a summit as the leader | Option p, "Hold a conference on the members' debts", gives every member the summit modifier; the members get the communiqué |
| CC13 | Can't leave in receivership | As a member in the leader's receivership, try to leave | The leave button is greyed with the receivership line |
| CC14 | Subjugation | As the leader, Subjugate a member in your receivership | The Subjugate tooltip shows the Creditors' Consortium line at +0.40 |

### Self-checks

| Self-check | Engine fact (spec § 11) | OK means | BROKEN means | Fallback |
|---|---|---|---|---|
| `cc_receivership_treaty` | 1: `create_treaty` with `debt_receivership` enters into force without a war and runs its `on_entry_into_force` | The member is the source of an in-force `debt_receivership` three days after it accepted | No such article: the treaty was not made in force | Already shipped: the check sets the receivership directly (`te_cred_set_direct_receivership`), which the monetary discovery honors with the article's conditions and exit ramp. If BROKEN, make that the only path |
| `cc_monopoly_treaty` | 3: `create_treaty` carries `acquire_monopoly_for_company` with a company and a building type chosen by script | At least one such article with the member as source is in force three days on | None is | The leader asks for monopolies in the treaty screen; drop `te_cred_demand_monopolies` and give the member's AI an acceptance bonus for its receiver's monopoly requests |
| `cc_adjustment_imposition` | 2: a `can_impose` added to a vanilla law by `INJECT` makes the engine grant the imposition | `has_law_imposition_rights` holds for at least one law the leader has and the member, in its receivership with the adjustment term, lacks | It holds for none | `start_enactment` of one of the leader's laws from the rescue (an option per law group in `te_cc.2`'s acceptance) |
