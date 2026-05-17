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

If cloud_setup.sh fails (clone, vanilla data missing, or server didn't become ready within 180 s) OR the selector fails / doesn't write a prompt file, open a GitHub issue with labels `priority:critical` and `nightly-audit:failure` describing what went wrong, then exit. Do not update the state file — leaving it untouched ensures the next run re-selects the same targets.

**If the failure is the vanilla-clone auth probe specifically** (issues #93/#99 family — the bootstrap prints a `---- DIAGNOSTIC: git/github auth context ----` block before exiting): before filing the issue, also actively investigate the proxy yourself. Run a few probes interactively and include the findings alongside the diagnostic block. Useful probes:
- `git -c http.sslVerify=true ls-remote https://github.com/jakeOmega/Vic3TimelineExtended.git HEAD 2>&1 | head` — does the proxy reach the routine's *primary* repo when invoked from a bash subshell? (If yes but cross-repo fails, the proxy is repo-scoped.)
- `cat ~/.gitconfig ~/.config/git/config 2>/dev/null` — any user-level credential helper or url.insteadOf rewrite that's repo-specific?
- `env | grep -iE 'http_proxy|https_proxy|CLAUDE'` — is there a proxy env var Claude Code sets only for some processes?
- `gh auth status` (if installed) and `cat ~/.config/gh/hosts.yml 2>/dev/null` — does gh have a token that git could borrow via `http.extraHeader = "Authorization: token $(gh auth token)"`?
- Try `git clone` of `jakeOmega/vic3` WITHOUT the `--filter=blob:none --sparse` flags — minimal clone in case those options confuse the proxy.

Include each probe's command + output (with secrets redacted) in the issue body. The goal is one diagnostic round-trip, not many — we're trying to figure out what the proxy actually exposes so the fix lands on the first follow-up.
