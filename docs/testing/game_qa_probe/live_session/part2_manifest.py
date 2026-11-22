"""Independent, read-only manifest of the owner's game folder: path, size, mtime_ns, sha256.
Not through game_qa. Skips logs/, crashes/, shadercache and the like (they change with every run)."""
import hashlib, json, os, sys
sys.path.insert(0, '/home/<user>/src/vic3te-game-qa-session')
import path_constants as pc
root = str(pc.game_user_data_path)
SKIP_DIRS = {'logs', 'crashes', 'shadercache', 'exceptions', 'dumps', 'cache', 'te_qa_overlay'}
out = {}
for name in sorted(os.listdir(root)):
    full = os.path.join(root, name)
    if os.path.isdir(full):
        if name in SKIP_DIRS:
            continue
        if name == 'mod':                       # names only, one level: the mods are big and not the run's to touch
            for m in sorted(os.listdir(full)):
                st = os.lstat(os.path.join(full, m))
                out['mod/' + m] = ['entry', st.st_mtime_ns]
            continue
        for d, dirs, files in os.walk(full):
            dirs.sort()
            for f in sorted(files):
                p = os.path.join(d, f)
                st = os.lstat(p)
                h = hashlib.sha256()
                with open(p, 'rb') as fh:
                    for chunk in iter(lambda: fh.read(1 << 20), b''):
                        h.update(chunk)
                out[os.path.relpath(p, root)] = [st.st_size, st.st_mtime_ns, h.hexdigest()]
    else:
        st = os.lstat(full)
        with open(full, 'rb') as fh:
            out[name] = [st.st_size, st.st_mtime_ns, hashlib.sha256(fh.read()).hexdigest()]
json.dump(out, open(sys.argv[1], 'w'), indent=0, sort_keys=True)
tops = {}
for k in out:
    tops[k.split('/')[0]] = tops.get(k.split('/')[0], 0) + 1
print(len(out), 'entries;', tops)
