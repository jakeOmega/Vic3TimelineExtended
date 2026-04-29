# WSL Migration — Cutover Checklist

The Strategic Reserve work + open-issue fixes are committed on `main` in three local commits:

```
60cfd06 Fix open issues: covert warfare scope pattern, remove unused fund_resistance action
d964351 Add Strategic Reserve System
<infra>  Add WSL deploy script, requirements.txt, gitignore cleanup
```

These commits have NOT been pushed to GitHub (HTTPS auth failed — credential is not cached). They are preserved in both the Windows working copy and the fresh WSL clone.

The WSL clone at `~/src/Vic3TimelineExtended` (user `jakef`) is fully set up: git configured with `core.autocrlf=false`, origin pointing at `https://github.com/jakeOmega/Vic3TimelineExtended.git`, `path_constants.py` rewritten for `/home/jakef/...` paths, `scripts/deploy.sh` executable, and `docs/`, `tests/`, `.metadata/` mirrored from the Windows copy (since they are gitignored and did not come with `git clone`). A successful `deploy.sh --apply` has already synced every game-required file from WSL to the Windows mod folder.

---

## What still needs you (the human) to finish

### 1. Push commits to GitHub

```bash
# From WSL:
cd ~/src/Vic3TimelineExtended
git push origin main
```

Or from Windows PowerShell (if Git Credential Manager already works):

```powershell
cd "C:\Users\jakef\OneDrive\Documents\Paradox Interactive\Victoria 3\mod\Vic3TimelineExtended"
git push origin main
```

If neither side has cached credentials, the easiest fix is GitHub CLI in WSL:

```bash
sudo apt install gh
gh auth login          # pick HTTPS, follow the prompt
git push origin main
```

### 2. Stop the Windows-side mod-state server

From PowerShell in the Windows working copy:

```powershell
Stop-Process -Id (Get-Content mod_state_server.pid)
```

### 3. Close this VS Code window

It is holding file handles to the Windows working copy. Close it completely.

### 4. Rename the Windows working copy to `.old`

From a PowerShell window that is NOT inside the mod directory:

```powershell
cd "C:\Users\jakef\OneDrive\Documents\Paradox Interactive\Victoria 3\mod"
Rename-Item Vic3TimelineExtended Vic3TimelineExtended.old
```

If Windows complains that the directory is in use, wait for OneDrive to settle or reboot.

### 5. Create a clean deploy target and populate it

```powershell
cd "C:\Users\jakef\OneDrive\Documents\Paradox Interactive\Victoria 3\mod"
New-Item -ItemType Directory Vic3TimelineExtended
```

Then from WSL:

```bash
cd ~/src/Vic3TimelineExtended
./scripts/deploy.sh --apply
```

### 6. Verify in the Paradox Launcher

Open Victoria 3 and refresh the playset. The mod is identified by `.metadata/metadata.json`, not by folder name, so no re-enabling should be needed.

### 7. Reopen VS Code on the WSL path

From a WSL terminal:

```bash
code ~/src/Vic3TimelineExtended
```

Or from the VS Code command palette: **Remote-WSL: Open Folder in WSL...** and point at `/home/jakef/src/Vic3TimelineExtended`. Install the "Remote - WSL" extension if prompted.

### 8. First-time setup inside the reopened workspace

```bash
cd ~/src/Vic3TimelineExtended
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 mod_state_server.py &
curl http://localhost:8950/status
```

### 9. Smoke-test an edit

1. From the WSL VS Code workspace, touch any loc file.
2. `./scripts/deploy.sh --apply` to push to the Windows mod folder.
3. Launch the game and confirm the change is visible.

### 10. After one week with no issues, delete the backup

```powershell
Remove-Item -Recurse -Force "C:\Users\jakef\OneDrive\Documents\Paradox Interactive\Victoria 3\mod\Vic3TimelineExtended.old"
```

Then update `.github/copilot-instructions.md` so the "Critical Paths" table lists `/home/jakef/src/Vic3TimelineExtended` as the canonical mod root.

---

## Notes

- `path_constants.py` is gitignored, so the Windows and WSL versions are each per-machine. The WSL version has been populated with Linux paths.
- `docs/`, `tests/`, and `.metadata/` are gitignored. They were mirrored into the WSL clone via rsync from the Windows copy; future rsyncs can rerun the same command if they drift.
- Image generation (`gen_image.py`) currently assumes a CUDA Windows setup. If you want to drive it from WSL you will need CUDA-in-WSL configured and will need to uncomment the ML deps in `requirements.txt`. Otherwise run image gen from a PowerShell session pointed at `\\wsl$\Ubuntu\home\jakef\src\Vic3TimelineExtended`.
- `texconv.exe` is a Windows binary. From WSL you can invoke it via `/mnt/c/.../texconv.exe` or keep texconv invocations on the Windows side.
