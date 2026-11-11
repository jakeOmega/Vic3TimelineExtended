import sys
from pathlib import Path
sys.path.insert(0, "/home/<winuser>/src/vic3te-game-qa-part1")
from game_qa import gate, snapshot
snap = next(s for s in snapshot.all_snapshots(Path("/mnt/d/vic3_qa_backups")) if s.id == sys.argv[1])
event = sys.argv[2]
if event == "started":
    games = gate.list_games()
    assert len(games) == 1, games
    snapshot.record(snap, "started", pid=games[0].pid, created=games[0].created)
    print("started", games[0])
else:
    snapshot.record(snap, event)
    print(event)
print([e["event"] for e in snapshot.journal(snap)])
