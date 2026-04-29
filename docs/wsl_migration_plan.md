# WSL Migration & Deploy Plan

**Goal:** Move the repository from OneDrive (Windows filesystem) to the WSL Linux filesystem for better git/I-O performance, and set up a small deploy script that syncs only the game-required files back to the Paradox mod folder.

**Why:** Git operations over OneDrive-backed NTFS paths trigger WSL's "Performance Tip" warning — every file operation pays for OneDrive sync and NTFS → ext4 translation. Moving the working copy to `/home/<user>/...` removes both overheads. The Paradox launcher still reads from the Windows mod path, so we need a deploy step.

---

## 1. Target Layout

| Location | Purpose |
|---|---|
| `\\wsl$\Ubuntu\home\<user>\src\Vic3TimelineExtended` | **Working copy.** The git repo, Python tools, docs — everything. Edits happen here. |
| `C:\Users\jakef\OneDrive\Documents\Paradox Interactive\Victoria 3\mod\Vic3TimelineExtended` | **Deploy target.** Only the runtime files the game needs. Never edited directly after the migration. |

Both paths are accessible from either side:
- From WSL: `/home/<user>/src/Vic3TimelineExtended` (native) and `/mnt/c/Users/jakef/OneDrive/.../Vic3TimelineExtended` (mount).
- From Windows: `\\wsl$\Ubuntu\home\<user>\src\Vic3TimelineExtended` (UNC) and the usual `C:\...` path.

---

## 2. What Gets Deployed (include list)

The game only cares about these paths, relative to the mod root:

- `common/` — all .txt script data
- `events/` — event files
- `localization/` — .yml files
- `gui/` — .gui files
- `gfx/` — .dds textures, portraits, etc.
- `map_data/` — map overrides
- `.metadata/` — Paradox launcher metadata (contains `metadata.json`; required for Paradox Mods)
- `descriptor.mod` — if present at root
- `thumbnail.png` — if present at root

**Exclusion rule of thumb:** if the Clausewitz engine wouldn't parse it, it doesn't get deployed.

---

## 3. What Stays Behind (exclude list)

Nothing in this list is copied to the deploy target:

| Path / Pattern | Reason |
|---|---|
| `.git/`, `.github/`, `.gitignore`, `.gitattributes` | Git plumbing |
| `.venv/`, `__pycache__/`, `*.pyc` | Python environment |
| `.vscode/` | Editor settings |
| `docs/` | Human-readable docs only |
| `tests/`, `test_*.py` | Test suite |
| `*.py` at repo root | Dev tools (gen_event.py, mod_state_server.py, etc.) |
| `*.log`, `*.log.1`, `*.log.2`, `*.pid` | Runtime log files |
| `generated_images/` | Intermediate image-gen output |
| `generate_images.log`, `rules_found.txt` | Scratch files |
| `README.md` | Repo-level readme |
| `deposits_config.json` | Only consumed by Python tools |
| `commented_vanilla_*.txt`, `vanilla_companies.txt` | Reference-only dumps |
| `texconv.exe` | Windows binary used by image pipeline |
| `*.code-workspace` | VS Code workspace files |
| Hidden dotfiles (anything starting with `.` other than `.metadata`) | Convention |

---

## 4. Migration Sequence

Execute once, in order, from a clean git state:

1. **Commit and push** any WIP on the current Windows repo so nothing is lost.
2. **Verify the WSL distro** (`wsl -l -v` from PowerShell). Ensure Ubuntu or equivalent is running with WSL 2.
3. **Inside WSL:**
   ```bash
   mkdir -p ~/src
   cd ~/src
   git clone <remote-url> Vic3TimelineExtended
   cd Vic3TimelineExtended
   ```
   Clone from the remote rather than moving the Windows copy so line-ending / permission oddities don't carry over.
4. **Recreate the Python virtualenv** inside WSL:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt   # create this if it doesn't exist
   ```
   (The mod state server, gen scripts, and image tools all need to work from WSL.)
5. **Rename/archive the Windows working copy.** Do **not** delete until the WSL clone is confirmed working and deploy has run successfully at least once. Rename to e.g. `Vic3TimelineExtended.old/` so it stops being picked up by the launcher.
6. **Run the deploy script** (§5). This populates the Paradox mod folder for the first time.
7. **Launch Victoria 3** and confirm the mod loads as before (check no new parse errors in `debug.log`).
8. **Update tooling paths.** `path_constants.py` currently points at the OneDrive mod root; it needs a source/destination split (see §6).
9. Once everything is verified, delete `Vic3TimelineExtended.old/`.

---

## 5. Deploy Script

Add `scripts/deploy.sh` (new `scripts/` folder) with the following contract:

- **Source:** the working copy (`~/src/Vic3TimelineExtended` or `$PWD` if run from the repo root).
- **Destination:** the Windows mod path, reached from WSL via `/mnt/c/...`.
- **Tool:** `rsync` with `--delete` so removed files on source are removed on destination.
- **Mode:** dry-run by default; apply only with `--apply`.

### Sketch

```bash
#!/usr/bin/env bash
# scripts/deploy.sh — copy game-required files from the WSL working copy
# to the Windows-side Paradox mod folder.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="/mnt/c/Users/jakef/OneDrive/Documents/Paradox Interactive/Victoria 3/mod/Vic3TimelineExtended"

APPLY=0
if [[ "${1:-}" == "--apply" ]]; then APPLY=1; fi

RSYNC_FLAGS=(
  -av                   # verbose, preserve timestamps
  --delete              # remove files on dest that are gone from source
  --prune-empty-dirs
)
[[ "$APPLY" -eq 0 ]] && RSYNC_FLAGS+=(--dry-run)

# Include only game-required top-level entries, exclude everything else.
INCLUDES=(
  --include='/common/***'
  --include='/events/***'
  --include='/localization/***'
  --include='/gui/***'
  --include='/gfx/***'
  --include='/map_data/***'
  --include='/.metadata/***'
  --include='/descriptor.mod'
  --include='/thumbnail.png'
  --exclude='/*'        # drop everything else at repo root
  --exclude='*.pyc'
  --exclude='__pycache__/'
)

mkdir -p "$DEST"
rsync "${RSYNC_FLAGS[@]}" "${INCLUDES[@]}" "$REPO_ROOT/" "$DEST/"

if [[ "$APPLY" -eq 0 ]]; then
  echo
  echo "DRY RUN. Re-run with --apply to copy files."
fi
```

### Usage

```bash
./scripts/deploy.sh            # dry-run, prints what would change
./scripts/deploy.sh --apply    # actually syncs
```

### Making it automatic

Options, ordered by lowest friction to highest:

1. **Manual** (simplest): run `./scripts/deploy.sh --apply` before launching the game.
2. **VS Code task:** add a `.vscode/tasks.json` entry that runs the deploy on save of any file under `common/`, `events/`, `localization/`, `gui/`, `gfx/`, `map_data/`. Use the `runOptions: { runOn: "folderOpen" }` pattern.
3. **Git pre-push hook:** `.git/hooks/pre-push` invokes deploy; guarantees the mod folder is up to date with anything pushed. Slightly heavy-handed.
4. **File watcher:** `entr`, `fswatch`, or `inotifywait` in a long-running terminal that re-runs `deploy.sh --apply` on every save. Best developer experience but requires an always-on terminal.

Recommend starting with option 1 and upgrading to option 4 once the workflow feels natural.

---

## 6. Code Changes Required in the Repo

### 6.1 `path_constants.py`

Currently this file hard-codes the mod root. After migration it should distinguish:

```python
MOD_SOURCE = Path(__file__).parent                 # the WSL working copy
MOD_DEPLOY_TARGET = Path("/mnt/c/Users/jakef/OneDrive/Documents/Paradox Interactive/Victoria 3/mod/Vic3TimelineExtended")
VANILLA_GAME = Path("/mnt/c/Program Files (x86)/Steam/steamapps/common/Victoria 3/game")
VANILLA_DOCS = Path("/mnt/c/Users/jakef/OneDrive/Documents/Paradox Interactive/Victoria 3/docs")
GAME_LOGS = Path("/mnt/c/Users/jakef/OneDrive/Documents/Paradox Interactive/Victoria 3/logs")
```

Most tools (mod_state_server, generators, organize_loc) should keep reading/writing to `MOD_SOURCE`. Only deploy touches `MOD_DEPLOY_TARGET`.

**Backward compatibility:** if any script currently writes to the deploy folder directly, update it to write to the source folder instead. Grep for `OneDrive\\Documents` and `Paradox Interactive` hard-codes across all `.py` files.

### 6.2 `.gitignore` cleanup

The new `.venv/` will live in WSL — keep it ignored. Make sure these patterns are present:

```
.venv/
__pycache__/
*.pyc
*.log
*.log.[0-9]
mod_state_server.pid
generated_images/
generate_images.log
rules_found.txt
```

### 6.3 New `requirements.txt` (if missing)

Pin the Python dependencies used by the mod state server, gen scripts, and image pipeline. This replaces "figure out what to `pip install`" with a single step during WSL setup.

### 6.4 Copilot-instructions update

`.github/copilot-instructions.md` currently lists the mod root as the OneDrive Windows path. After migration, update it to reference the WSL source path for editing and the OneDrive path only as the deploy target. Also update the "Critical Paths" table in that file.

---

## 7. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Line-ending changes between NTFS and ext4 corrupt Clausewitz `.txt` files | Enforce `git config core.autocrlf false` in the WSL clone. Clausewitz requires UTF-8 BOM, which `rsync` preserves byte-for-byte. |
| `rsync --delete` wipes files the launcher created on its own | Keep `.metadata/` in the include list; any other mod-loader-created files should be rare. If this bites, add more explicit includes. |
| Paradox launcher caches the old mod path | After the first deploy, open Paradox Launcher → Mods → Refresh. The launcher reads `.metadata/metadata.json` to identify the mod, not the folder name. |
| Windows tools (`texconv.exe`, image gen with CUDA) need Windows access | `texconv.exe` can be invoked from WSL via `/mnt/c/.../texconv.exe`. CUDA via Docker Desktop + WSL2 works, but simpler: keep image generation scripts on Windows or run them from a PowerShell session that operates on `\\wsl$\Ubuntu\...`. |
| Mod state server binds to `127.0.0.1:8950` inside WSL — Windows tools can't reach it | WSL2 with Windows 11 auto-forwards localhost. Verify by calling `http://localhost:8950/status` from PowerShell after starting the server in WSL. If it fails, bind to `0.0.0.0` and use the WSL IP. |
| OneDrive sync conflicts on the deploy target | The deploy target is inside OneDrive. Either (a) move the mod folder outside OneDrive (recommended — Paradox mods don't need cloud sync), or (b) pause OneDrive during deploys. |
| Path-constant hardcodes scattered through Python tools | Do a repo-wide grep for `OneDrive`, `C:\\`, `C:/`, `/mnt/c`, `Paradox Interactive` before migration and fix every hit to use `path_constants.py`. |

---

## 8. Rollback Plan

If something goes wrong:

1. Keep `Vic3TimelineExtended.old/` on the Windows side for at least a week.
2. To abandon the WSL setup: rename `Vic3TimelineExtended.old/` → `Vic3TimelineExtended/`, and the launcher picks up the pre-migration state.
3. The WSL clone is detachable — you can delete `~/src/Vic3TimelineExtended` without affecting the game.

---

## 9. Validation Checklist

After the first successful `deploy.sh --apply`:

- [ ] `ls /mnt/c/Users/jakef/OneDrive/Documents/Paradox\ Interactive/Victoria\ 3/mod/Vic3TimelineExtended` shows only game-required folders.
- [ ] `common/`, `events/`, `localization/`, `gui/`, `gfx/`, `map_data/`, `.metadata/` are present in the deploy target.
- [ ] `docs/`, `*.py`, `.git/`, `.venv/` are NOT in the deploy target.
- [ ] Paradox launcher still shows the mod and marks it enabled.
- [ ] Victoria 3 starts, the custom title screen / mod icon appear, and `debug.log` has no new "Failed to parse" errors that weren't there before.
- [ ] `python mod_state_server.py` starts in WSL and `curl http://localhost:8950/status` returns `status: running`.
- [ ] A small edit (e.g., touch a loc string) → deploy → launch game shows the change in-game.
- [ ] `git status` in the WSL clone shows no unexpected file-mode changes (`100644` vs `100755` drift).

---

## 10. Timeline of Work

Rough task breakdown, shortest path first:

1. Write `scripts/deploy.sh` and test with `--dry-run` on the current Windows repo (no migration yet).
2. Fix `path_constants.py` to split source vs deploy-target, and grep for hardcoded paths to fix.
3. Generate `requirements.txt` from the current `.venv`.
4. Clone into WSL, run `deploy.sh --apply`, playtest the game.
5. Switch daily editing to the WSL clone; leave the Windows copy as backup for one week.
6. After a week with no problems, delete the backup and update `copilot-instructions.md` to reflect the new layout.
