import sys, time
sys.path.insert(0, "/home/<winuser>/src/vic3te-game-qa-part2")
from game_qa import gate
from game_qa.helper import ProcessHelper
game = gate.list_games()[0]
h = ProcessHelper(); h.adopt(game)
print("idle samples, 1 s apart, no keys sent:", [(h.idle_ms(), time.sleep(1))[0] for _ in range(6)])
h.keys(game.pid, [{"text": "help observe"}, {"scan": 0x1C}])
print("after our own keys, 1 s apart:", [(h.idle_ms(), time.sleep(1))[0] for _ in range(4)])
if "--kill" in sys.argv:
    h.kill(game); time.sleep(4); print("after kill, games:", gate.list_games())
h.close()
