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
   does the method line show 2.50 per level or the staffed building total?
   Record decimal formatting, including a small fraction during hiring.
2. Run `event te_cc_probe.1`, choose **Log staffed capture**. `CC_PROBE:` lines
   in `debug.log`, paired with scope dumps identifying each state, contain
   each market state with a power plant and the market
   sum in internal units. In a state with only one probe-equipped plant, full
   staffing should read `2.5 × level`; half staffing should read half that.
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

All checks below are pending. Offline parsing does not verify engine behavior.
Fill in game version, save/date, country, state, level, staffing, screenshots or
log excerpts, selected fallback, and elapsed game time for each observation.

| Check | Expected | Observed |
|---|---|---|
| State read, fully staffed | 2.5 per coal plant level | Pending |
| State read, half staffed | Half the fully staffed total | Pending |
| Tooltip units and decimals | Readable 2.50; determine per-level vs total | Pending |
| Hidden fuel gating | Only the matching modern fuel's variant | Pending |
| Fuel swap without mandate | Drops invalid variant; record fallback | Pending |
| Law applied to default | Automatically selects a valid variant | Pending |
| Fuel swap under mandate | Lands on valid capture, never the default | Pending |
| Market sweep and foreign ownership | Location's state/market, counted once | Pending |

If hidden gating or forced fallback fails, do not build A′ unchanged. Record
the failure and use the building-percentage fallback in design §8. If the
state read fails, investigate scope and modifier registration before choosing
an accounting mechanism.
