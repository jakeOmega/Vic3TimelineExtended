# Legacy Narrative Events

Part of the [mod systems reference](../mod_systems.md), which indexes every system.

## Legacy narrative event integration

Law-enactment bank runs (`extra_law_events.2` / `.38`) now apply a small
confidence shock (-5 cycle, -1 momentum) when the banking JE exists, including
simplified banking. With banking disabled they remain enactment flavor.
`finreg_banking_stability` retains its company-throughput benefit and also
reduces banking crash probability by 10% of base; deposit guarantees in `.62`
share that protection.

The discretionary bailout (`banking_cycle_events.45`) requires a non-defaulting
donor at cycle 40+ and a non-hostile, diplomatically relevant trading partner
with a smaller GDP than the donor's, in downturn/panic with an active banking JE.
One of the two markets must rely on the other for at least 5% of its trade
(`market_trade_reliance`, `banking_bailout_min_trade_reliance` — the banking
contagion's first tier). The partner is asked first: the
donor's banking pulse picks it with the same gate and sends it
`banking_cycle_events.68` ("appeal to [donor]?", −5% prestige for asking), and
only its appeal option sends `.45` to the donor; whatever the donor answers
reaches the partner as `.69`, naming the sum. Rescue options transfer equal treasury amounts (the donor's
old weekly expense multiplied by duration / 14, approximating its former
linearly decaying total), capped by the recipient's GDP — the rescue package at
0.2× (vanilla's gold reserve limit), the smaller grant at 1/8 of that — and grant
temporary banking stability to the recipient.
This is a grant, not a new swap-line or lender-of-last-resort treaty. The latter
continues to use its own default-driven event. Protected recipients cannot draw
another discretionary bailout while the stability modifier lasts.

`international_relations_events.6` and `.7` are disabled-system fallbacks only.
Enabled covert warfare owns detection and exposure; enabled space race owns
milestone celebrations. The first-colony charter story (`society_technology_events.18`)
is dispatched seven days after a country's first tracked colony, after its
location-specialization event. Governance (`.19`) requires a tracked colony and
the charter story to have fired. Both retain their building-based flavor gates
when space race is disabled; enabled-system governance no longer needs an
unrelated space-elevator building or era-12 technology (colonization begins in
era 11). The monthly first-colony draw backfills existing saves, with a short
pending flag preventing it from racing the delayed establishment event.
