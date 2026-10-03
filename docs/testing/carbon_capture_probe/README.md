# Carbon capture engine probe (design phase 0)

This is an opt-in overlay for a **copied test save**, kept outside the deployed
mod directories. `scripts/deploy.sh` does not include it. Its handwritten coal
variant is the design's Modern Coal-Fired Plant Tier II example. A second,
cost-free oil variant supplies a valid mandated fallback; it is a diagnostic,
not a balanced gameplay method. No market emissions formula reads the probe.

## Loading the overlay

Use a full checkout's normal deploy dry run and deploy first, following
`CLAUDE.md`'s play-testing instructions. Then copy this folder's `common/`,
`events/` and `localization/` contents into the deployed mod, preserving the
subdirectories. Restart Victoria 3 with only that copy of Timeline Extended
enabled. Do not run a deploy watcher during the test: it may remove the overlay.
The next normal full deploy removes the overlay. Never copy these fixtures into
the repository's production `common/` directories or run `organize_loc` on them.

Use a country with Modern Urban Planning researched and an existing Power
Plant; both modern fuel methods must be available. The probe adds a group to
Power Plants only. A new or upgraded-save building should start on Probe: No
Carbon Capture. Only the variant matching the current modern fuel method should
appear. Early fuel methods intentionally have no probe capture variant; keep
all the test country's power plants on one of the two modern methods before
enabling the mandate. Use a test country without preexisting restrictive laws
and save a baseline before changing anything.

## Procedure

1. On a Modern Coal-Fired Plant, choose Probe: Coal Capture (50%). Record the
   method tooltip and building tooltip at level 1 and at level 2 or higher:
   the fuel method adds 5.00 Greenhouse Gas Emissions and capture subtracts
   2.50 per level, giving 2.50 net at full staffing and base throughput.
   Modern oil adds 6.09 and capture subtracts 3.05, giving 3.04 net.
   The state capture credit is hidden; only the building's net emissions should
   be visible. Record decimal formatting during hiring and with throughput
   bonuses, comparing the building's total with the method's per-level figure.
2. Run `event te_cc_probe.1`, choose **Log staffed capture**. `CC_PROBE:` lines
   in `debug.log`, paired with scope dumps identifying each state, contain
   each market state with a power plant and the market
   sum in internal units. In a state with only one probe-equipped plant, full
   staffing at base throughput should read `2.5 × level`; half staffing should
   read half that. Record throughput too, since workforce-scaled contributions
   follow it.
   Record level, staffing and actual read together. The market sum should be
   the state's total divided by 1000. Let a tick pass after each PM change.
3. With Unrestricted Extraction, switch coal to Modern Oil-Fired Plant while
   coal capture is selected. Advance time and record which probe method the
   engine selects, whether an invalid method persists, and retooling. Repeat
   oil to coal. Restore the baseline for repeatable comparisons.
4. Run the event's **Impose the phaseout mandate** option. It researches the
   current law's prerequisites, establishes the ministry and activates Managed
   Fossil Phaseout. Verify the law is still held after a monthly pulse. Start
   from Probe: No Carbon Capture and check whether the law forces a valid
   variant by itself. Swap modern coal to modern oil and back; record whether
   the engine keeps a valid capture method with the default disallowed. The
   **Remove the mandate** option restores Unrestricted Extraction only; reload
   the baseline to restore the original ministry and technologies.
5. Test a foreign-owned plant and a multi-country market, including a treaty
   port if available. Confirm that the state receives the credit, the market
   sweep includes it once in its location's market, and note whose law makes
   the default unavailable. Compare the logged market sum with the individual
   states' capture totals.

## Evidence record

The removal-only building and subsidy policy can also be tested in the normal
mod (the overlay is only needed for the unfinished source-capture tiers):
research Carbon Capture and Storage, build Carbon Conversion Works, and select
Direct Air Capture. At full staffing and base throughput expect −168 Greenhouse
Gas Emissions per level and no goods output. Subsidize the works and compare
hiring, a throughput bonus and the next January's Carbon Captured reading.
Carbon Removal Support needs 0.5 °C warming and the new technology; verify its
100 Authority cost, required subsidies, +5% throughput and movement radicalism
bonus, then repeal it. Synthetic Coal must remain gated by Genetic Engineering;
switching methods must replace the credit, never add both.

The owner supplied nonzero state reads on 2026-10-03 (ROOT Byzantium, country
88): Bougainville 1.43647, Sicily 1.43647, Abruzzo 1.07660, Apulia 2.87897 and
Umbria 0.35835. This confirms the state accessor returns varying contributions;
levels, staffing and throughput were not supplied, so exact scaling is pending.
Offline parsing does not verify the remaining engine behavior.
Fill in game version, save/date, country, state, level, staffing, screenshots or
log excerpts, selected fallback, and elapsed game time for each observation.

| Check | Expected | Observed |
|---|---|---|
| State read, fully staffed | 2.5 per coal plant level | Pending |
| State read, half staffed | Half the fully staffed total | Pending |
| Net emissions tooltip | Coal +5.00 −2.50 = 2.50; oil +6.09 −3.05 = 3.04, scaled by staffing and throughput | Pending updated overlay |
| Throughput scaling | Fuel emissions and capture grow together with throughput | Pending |
| Hidden fuel gating | Only the matching modern fuel's variant | Pending |
| Fuel swap without mandate | Drops invalid variant; record fallback | Pending |
| Law applied to default | Automatically selects a valid variant | Pending |
| Fuel swap under mandate | Lands on valid capture, never the default | Pending |
| Market sweep and foreign ownership | Location's state/market, counted once | Pending |

If hidden gating or forced fallback fails, do not build A′ unchanged. Record
the failure and use the building-percentage fallback in design §8. If the
state read fails, investigate scope and modifier registration before choosing
an accounting mechanism.
