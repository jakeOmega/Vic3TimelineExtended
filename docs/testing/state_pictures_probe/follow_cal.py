"""Follow the game's debug.log during a calibration run and keep the probe's lines.

    python3 docs/testing/state_pictures_probe/follow_cal.py <out file> [--interval 5]

Appends every `TE_SP_CAL`, `TE_SELF_CHECK` and `TE_STATE_PICTURE` line to <out file> as it is
written, across the log's rotation (game_qa.logtail.LogFollower), with a marker line where
lines were lost. Run it from the repo root, before the game starts; stop it with Ctrl-C or by
creating <out file>.stop.
"""
import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
import path_constants  # noqa: E402
from game_qa.logtail import GAP_MARKER, LogFollower  # noqa: E402

KEEP = ("TE_SP_CAL", "TE_SELF_CHECK", "TE_STATE_PICTURE")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("out", type=Path)
    ap.add_argument("--interval", type=float, default=5.0)
    args = ap.parse_args()
    follower = LogFollower(Path(path_constants.game_logs_path) / "debug.log")
    stop = args.out.with_name(args.out.name + ".stop")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    kept = 0
    with open(args.out, "a", encoding="utf-8") as out:
        while not stop.exists():
            for line in follower.poll():
                if line == GAP_MARKER or any(k in line for k in KEEP):
                    out.write(line.rstrip("\n") + "\n")
                    kept += 1
            out.flush()
            time.sleep(args.interval)
    print(f"stopped: {kept} lines kept in {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
