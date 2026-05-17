<!--
Canonical text for the Anthropic Routines UI "Instructions" field that drives
the nightly mod audit. Paste the contents below (everything under the next
horizontal rule) into the UI verbatim.

When this file changes, re-paste into the UI — the UI does not auto-pull.
The README references this file so prose and live instructions can't drift.
-->

---

First, source ./scripts/cloud_setup.sh. This shallow-sparse-clones vanilla into ../vic3, clones Modding-Digests, exports the VIC3_* env vars, creates a .venv, and starts mod_state_server in the background (waits ~60–110 s for /status to return ready, with a 180 s ceiling). Don't explore the codebase or skip ahead — the bootstrap is load-bearing for the rest of the audit.

Then run python3 scripts/nightly_audit_select.py. It will print the path to a prompt file like docs/audits/nightly/YYYY-MM-DD/prompt.md — read that file and follow it end-to-end. Everything you need (including how to query mod_state_server for modifier validity, engine-doc origins, and post-fix verification via `?mod_only=true&audits_only=true`) is in it.

If cloud_setup.sh fails (gh auth, clone, or server didn't become ready within 180 s) OR the selector fails / doesn't write a prompt file, open a GitHub issue with labels `priority:critical` and `nightly-audit:failure` describing what went wrong, then exit. Do not update the state file — leaving it untouched ensures the next run re-selects the same targets.
