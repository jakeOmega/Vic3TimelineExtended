# Tax code probes — architecture-risk results

Use the [focused runbook](tax-code-probes.md). One observation and decision per row is
enough. Choose **worked / failed / unclear / skipped**; every row starts skipped.
A result applies only to the tested channel, scope, and access path.

- Tester/date; game version / mod commit or downloaded revision: ___
- Country / other enabled mods (if any): ___
- Approximate time spent; setup limitations: ___

| Risk | Result | What happened / demonstrated scope? | Decision or next targeted check |
|---|---|---|---|
| R1a State relief: payer savings versus lost collections; capital versus other state | skipped | | |
| R1b Sector relief: actual beneficiary/channel; agriculture versus manufacturing | skipped | | |
| R2a Script receipts/fiscal balances match relevant Budget totals and respond to treatment | skipped | | |
| R2b Zero-rate bases / payer and distribution data available to scripts, separately from GUI | skipped | | |
| R3 Wage + dividend coexist; rebuild twice; scheduled commencement and zero successor | skipped | | |
| R4 Two owned container records; overflow rejection; references/fields/dates survive one pending-package reload | skipped | | |
| Customs (if building): actual good/direction effect; member/treaty authority | skipped | | |
| School promises (if building): delivered level distinguished from requested target | skipped | | |
| Native AI integration: automatic mutation paths and intervention needed | skipped | | |
| Civil-war storage (if choosing copying): raw inheritance/ownership at outbreak | skipped | | |

Useful rough readings, only for the rows run:

- R1: same capital payer deduction / state receipts before → after ___;
  noncapital deduction ___; agricultural payer income source/location and deduction ___;
  manufacturing comparison ___
- R2: script domestic receipts / fixed / total balance and matching UI values ___;
  candidate base getter, scope, units, coverage, zero-rate result ___
- R3/R4: two operative rates ___; after repeated rebuild ___;
  record references/owners/month fields before → after reload ___;
  original due/expiry → reloaded due/expiry → actual transition months ___
- Conditional check: relevant setting, authority or requested/delivered readings ___

R2b cannot pass from a tooltip or receipt total. If a bounded developer search finds no
candidate, write **unavailable in inspected docs** and identify the approximation chosen;
do not call engine-wide impossibility proven. No native AI change in a short run is
inconclusive about prevention. Do not infer untested tax channels or ownership cases.

Problem/error (step; screenshot or relevant log excerpt if useful): ___

**Ready to build:** supported mechanisms and explicit fallbacks ___

**Before the dependent work:** unresolved risk → affected feature → next check/fallback ___

**Deferred to implementation/release validation:** ___

No mandatory screenshots, save uploads, calculations, or extended-form completion.
