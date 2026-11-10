"""The launch gate: may the harness start the game now?

The owner's rule (spec § 2): a session asks before launching unless the owner
granted launches for the session, and even with a grant the GPU is checked
first. Only the conversation knows about the grant, so the tool's half is to
make the session state its permission, and to refuse on what it can see:

  * no stated permission;
  * no usable backup root (nothing launches without a snapshot);
  * a Victoria 3 process this harness did not start;
  * a busy GPU, until the owner has confirmed.

Processes are told apart by process id *and* creation time: an id is reused,
the pair is not.
"""
from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from game_qa import snapshot

GPU_QUERY = (
    "nvidia-smi",
    "--query-gpu=utilization.gpu,memory.used,memory.total",
    "--format=csv,noheader,nounits",
)
GPU_SAMPLES = 5
GPU_INTERVAL_S = 1.0
GPU_BUSY_UTIL_PCT = 50.0
GPU_BUSY_MEMORY_SHARE = 0.5

LIST_GAMES = (
    "powershell.exe",
    "-NoProfile",
    "-Command",
    "Get-Process victoria3 -ErrorAction SilentlyContinue | "
    "ForEach-Object { '{0} {1}' -f $_.Id, $_.StartTime.ToUniversalTime().ToString('o') }",
)


class GateError(Exception):
    """The gate could not look (PowerShell would not run): nothing may launch."""


@dataclass(frozen=True)
class GpuSample:
    util_pct: float
    mem_used_mib: int
    mem_total_mib: int


@dataclass(frozen=True)
class ProcId:
    pid: int
    created: str  # creation time, UTC ISO-8601, as Windows reports it


@dataclass
class Gate:
    ok: bool
    reason: str  # "ok" | "no_permission" | "backup_root" | "other_game" | "gpu_busy"
    detail: str


def parse_nvidia_smi(text: str) -> list[GpuSample]:
    """One sample per readable line of `nvidia-smi --format=csv,noheader,nounits`."""
    samples = []
    for line in text.splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) != 3:
            continue
        try:
            samples.append(GpuSample(float(parts[0]), int(parts[1]), int(parts[2])))
        except ValueError:
            continue
    return samples


def sample_gpu(run=subprocess.run, sleep=time.sleep, n: int = GPU_SAMPLES,
               interval: float = GPU_INTERVAL_S) -> list[GpuSample]:
    """`n` readings `interval` seconds apart; [] when nvidia-smi is missing or fails."""
    samples: list[GpuSample] = []
    for i in range(n):
        if i:
            sleep(interval)
        try:
            out = run(list(GPU_QUERY), capture_output=True, text=True, timeout=10, check=False)
        except (OSError, subprocess.SubprocessError):
            return []
        if out.returncode != 0:
            return []
        samples.extend(parse_nvidia_smi(out.stdout))
    return samples


def gpu_busy(samples: Sequence[GpuSample]) -> bool:
    """Busy at a mean utilization of 50% or more, or with more than half the
    memory in use in any sample. No reading counts as busy: the owner is asked."""
    if not samples:
        return True
    mean = sum(s.util_pct for s in samples) / len(samples)
    if mean >= GPU_BUSY_UTIL_PCT:
        return True
    return any(s.mem_total_mib and s.mem_used_mib / s.mem_total_mib > GPU_BUSY_MEMORY_SHARE for s in samples)


def list_games(run=subprocess.run) -> list[ProcId]:
    """Every running victoria3.exe, by process id and creation time."""
    try:
        out = run(list(LIST_GAMES), capture_output=True, text=True, timeout=30, check=False)
    except (OSError, subprocess.SubprocessError) as exc:
        raise GateError(f"could not list game processes: {exc!r}") from exc
    games = []
    for line in out.stdout.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[0].isdigit():
            games.append(ProcId(int(parts[0]), parts[1]))
    return games


def ours_from_journals(backup_root: Path) -> set[ProcId]:
    """The game processes of runs that started and were neither restored nor
    held: if one is still up, it is this harness's own orphan."""
    ours: set[ProcId] = set()
    if not Path(backup_root).is_dir():
        return ours
    for snap in snapshot.all_snapshots(Path(backup_root)):
        events = snapshot.journal(snap)
        names = {e.get("event") for e in events}
        if "restored" in names or "held" in names:
            continue
        for e in events:
            if e.get("event") == "started" and "pid" in e and "created" in e:
                ours.add(ProcId(int(e["pid"]), str(e["created"])))
    return ours


def check(permission: str, games: Sequence[ProcId], ours: set[ProcId], samples: Sequence[GpuSample],
          owner_confirmed_busy: bool, backup_error: str | None) -> Gate:
    """The first refusal that applies, in the order of the module docstring."""
    if not permission.strip():
        return Gate(False, "no_permission",
                    "state where the permission to launch came from (asked, or granted for this session)")
    if backup_error:
        return Gate(False, "backup_root", backup_error)
    theirs = [g for g in games if g not in ours]
    if theirs:
        return Gate(False, "other_game",
                    "a Victoria 3 process this harness did not start is running: "
                    + ", ".join(f"pid {g.pid} (started {g.created})" for g in theirs))
    if gpu_busy(samples) and not owner_confirmed_busy:
        if not samples:
            return Gate(False, "gpu_busy", "no GPU reading (nvidia-smi missing or failing): ask the owner")
        mean = sum(s.util_pct for s in samples) / len(samples)
        peak = max(s.mem_used_mib / s.mem_total_mib if s.mem_total_mib else 0.0 for s in samples)
        return Gate(False, "gpu_busy",
                    f"GPU at {mean:.0f}% mean utilization, {peak:.0%} of memory in use: ask the owner")
    return Gate(True, "ok", "")
