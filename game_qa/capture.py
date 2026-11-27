"""`python3 -m game_qa capture`: take the pictures the shot manifest lists, in one session per scene (#2056).

The manifest is `scripts/image_pipeline/guide_shots.py` (its docstring has the keys). For each scene the selected
shots need, `capture` starts a session on the scene's save with `start --capture` (the overlay's console draws
nothing; debug mode's counters hide while `te_qa_capture` is set) and `-no_notifications`, takes the scene's shots,
and stops the session; `--in-session` uses a session already running instead and leaves it running. For each shot:

1. `tag` the shot's country when it is not the one played;
2. `read` its `needs` (minimums, the owner's ruling of 2026-11-25): one not met skips the shot, reported with the
   values read, since a picture of an empty section is worse than the old picture;
3. `run-setup` its setups (given to `start` with the scene's other shots');
4. `view`: one step that resets what the shot before opened (the Timeline Extended window's keys and every key the
   last view set cleared, the side panel closed), sets `te_qa_capture`, then the shot's own steps;
5. its `scroll` and `input` (a wheel, clicks or a drag on the HUD, the map or the tech tree: the owner's standing
   grants of 2026-11-24 and 2026-11-26), then `click --console`, which takes the keyboard back;
6. `hover` its point, or park the cursor on the console's input line, where it hovers nothing (the edit line, which
   draws nothing in a capture, takes the hover);
7. `crop` its region with `settle` (shot again until two shots agree), then trim the empty panel below the content
   (`trim`, the owner's framing of 2026-11-26: from the tab strip down to the last section, no empty background);
8. compare with the committed picture: the same size and no pixel changed is `unchanged`.

A Workshop shot (`out` under `workshop/`, taken with `--workshop`) is never written into the repo: the carousel
images stay local (owner, 2026-11-26), and `scripts/image_pipeline/workshop_screenshots.py --src <capture folder>`
annotates them from the capture folder.

Everything lands in a capture folder under the backup root (`captures/<stamp>/`, on D:): each new picture, the old
one beside it, a difference image where Pillow is installed, `capture.json` and `index.html`, the contact sheet a
reviewer reads (old, new, difference, and what the manifest says the picture shows). Nothing in the repo changes
unless `--write` is given; then each picture that changed is copied to its `out` (a `.jpg` saved at quality 90 with
no chroma subsampling, as images/README.md says) and its row in `guide_shots_taken.json` (commit, date, window, UI
scale, save, SHA-256) is rewritten, which is what `guide_shots_stale.py` measures staleness from.

The window and the UI scale must be the manifest's (`WINDOW`, `UI_SCALE`): its regions are fractions measured
there, and a side panel's width in pixels follows the scale. Another is refused `window_mismatch` before any shot,
unless `--any-window`.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import html
import importlib.util
import json
import os
import shutil
import subprocess
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from game_qa import server

REPO = Path(__file__).resolve().parents[1]
MANIFEST = "scripts/image_pipeline/guide_shots.py"
TAKEN_FILE = "scripts/image_pipeline/guide_shots_taken.json"
CONSOLE_PARK = (0.1125, 0.544)          # session.CONSOLE_INPUT_LINE: the console's edit line, which hovers nothing
VIEW_TIMEOUT_S = 120.0
CAPTURE_ARGS = ("no_notifications",)
OPS = {">": lambda a, b: a > b, ">=": lambda a, b: a >= b, "<": lambda a, b: a < b, "<=": lambda a, b: a <= b,
       "==": lambda a, b: a == b, "!=": lambda a, b: a != b}

Call = Callable[..., tuple[dict, int]]


class CaptureError(Exception):
    def __init__(self, code: str, detail: str = "", **info: Any) -> None:
        super().__init__("%s: %s" % (code, detail) if detail else code)
        self.code, self.detail, self.info = code, detail, info


def load_manifest(repo: Path = REPO):
    """The manifest module of the checkout at `repo`."""
    path = Path(repo) / MANIFEST
    spec = importlib.util.spec_from_file_location("guide_shots", path)
    if spec is None or spec.loader is None:
        raise CaptureError("no_manifest", "%s could not be loaded" % path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def is_workshop(shot: Mapping) -> bool:
    return str(shot.get("out", "")).startswith("workshop/")


def select(manifest, only: Sequence[str] = (), scenes: Sequence[str] = (), workshop: bool = False) -> list[str]:
    """The shot ids to take: `only` (each a TAKEN shot), else every TAKEN shot of the guide (or, with `workshop`, of
    the Workshop page), narrowed to `scenes` when given."""
    shots = manifest.SHOTS
    unknown = [sid for sid in only if sid not in shots]
    if unknown:
        raise CaptureError("unknown_shot", "no shot %s in the manifest" % ", ".join(unknown))
    untaken = [sid for sid in only if shots[sid]["status"] not in manifest.TAKEN]
    if untaken:
        raise CaptureError("not_a_view", "%s: status %s, which capture does not take (only %s)"
                           % (", ".join(untaken), ", ".join(sorted({shots[s]["status"] for s in untaken})),
                              ", ".join(manifest.TAKEN)))
    bad = [s for s in scenes if s not in manifest.SCENES]
    if bad:
        raise CaptureError("unknown_scene", "no scene %s; the manifest has %s" % (", ".join(bad),
                                                                              ", ".join(manifest.SCENES)))
    chosen = list(only) or [sid for sid, shot in shots.items()
                            if shot["status"] in manifest.TAKEN and is_workshop(shot) == workshop]
    if scenes:
        chosen = [sid for sid in chosen if shots[sid]["scene"] in scenes]
    if not chosen:
        raise CaptureError("nothing_to_take", "no shot matches")
    return chosen


def by_scene(manifest, ids: Sequence[str]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for sid in ids:
        out.setdefault(manifest.SHOTS[sid]["scene"], []).append(sid)
    return out


def start_body(manifest, scene: str, ids: Sequence[str], permission: str) -> dict:
    """`start`'s body for a scene: its save, country, playset and limit, the capture overlay, no notifications, and
    every setup its shots name (a name used twice must have the same body)."""
    sc = manifest.SCENES[scene]
    setups: dict[str, str] = {}
    for sid in ids:
        for name, body in (manifest.SHOTS[sid].get("setups") or {}).items():
            if setups.get(name, body) != body:
                raise CaptureError("setup_clash", "setup %s has two bodies (shot %s)" % (name, sid))
            setups[name] = body
    body: dict[str, Any] = {"permission": permission, "as_tag": sc["as_tag"], "save": sc["save"],
                            "playset": sc.get("playset", "mod_only"), "setups": setups, "capture": True,
                            "game_args": list(CAPTURE_ARGS), "owner_confirmed_busy": False}
    if sc.get("unresponsive_s"):
        body["unresponsive_s"] = sc["unresponsive_s"]
    return body


def need_met(read: Mapping, op: str | None, number: float | None) -> bool | None:
    """Whether one read meets its need: None when the read failed (a form the game could not evaluate)."""
    if not read.get("ok"):
        return None
    value = read.get("value")
    if op is None:
        return value is True or (isinstance(value, (int, float)) and not isinstance(value, bool) and value != 0)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return OPS[op](float(value), number)


def keys_set(steps: Sequence[Sequence[str]]) -> list[str]:
    """The client-side keys a view's steps set, each once, in order."""
    out: list[str] = []
    for step in steps:
        for action in step:
            if action.startswith("set:"):
                key = action[4:].partition("=")[0]
                if key not in out:
                    out.append(key)
    return out


def reset_step(manifest, previous: Sequence[str]) -> list[str]:
    """Clear the Timeline Extended window's keys, the mod's popups' and every key the last view set, close the side
    panel, and set the capture key: the first step of every shot's view."""
    keys = list(dict.fromkeys(list(manifest.TE_WINDOW_KEYS) + list(getattr(manifest, "POPUP_KEYS", ()))
                              + [k for k in previous if k != manifest.CAPTURE_KEY]))
    return ["clear:%s" % k for k in keys] + ["close-panel", "set:%s=yes" % manifest.CAPTURE_KEY]


class Capture:
    """One run of the verb: what it took, skipped and failed, in `results` (one dict per shot id)."""

    def __init__(self, manifest, call: Call, out_dir: Path, any_window: bool = False) -> None:
        self.m, self.call, self.out_dir, self.any_window = manifest, call, Path(out_dir), any_window
        self.results: dict[str, dict] = {}
        self.country: str | None = None
        self.previous_keys: list[str] = []
        self.window_checked = False
        self.ui_scale: float | None = None
        self.save: str | None = None

    def verb(self, verb: str, body: Mapping | None = None, timeout: float | None = None) -> dict:
        args = (verb, dict(body or {})) if timeout is None else (verb, dict(body or {}), timeout)
        reply, code = self.call(*args)
        if code != 0:
            raise CaptureError(str(reply.get("refused") or reply.get("error") or "verb_failed"),
                               "%s: %s" % (verb, reply.get("detail", reply)), reply=reply)
        return reply

    def scene(self, scene: str, ids: Sequence[str], started: dict | None) -> None:
        """Take `ids` in the running session (started for `scene`, its start reply `started`, or found running)."""
        sc = self.m.SCENES[scene]
        self.country = (started or {}).get("country") or sc["as_tag"]
        self.save = (started or {}).get("save") or sc["save"]
        cap = (started or {}).get("capture") or {}
        self.ui_scale = cap.get("ui_scale")
        self.previous_keys = []
        for sid in ids:
            try:
                self.results[sid] = self.shot(sid)
            except CaptureError as e:
                self.results[sid] = {"id": sid, "status": "failed", "error": e.code, "detail": e.detail}
                if e.code in ("window_mismatch", "watch_ended", "stopped", "game_gone", "not_started"):
                    for rest in ids[ids.index(sid) + 1:]:
                        self.results[rest] = {"id": rest, "status": "not_run", "error": e.code}
                    break
        try:
            self.verb("view", {"steps": [reset_step(self.m, self.previous_keys)[:-1] + [
                "clear:%s" % self.m.CAPTURE_KEY]]}, VIEW_TIMEOUT_S)
        except CaptureError:
            pass                                # the shots stand; the next view resets anyway
        played = (started or {}).get("country") or sc["as_tag"]
        if self.country != played:
            # A shot's candidate countries leave the last one tried played: an --in-session run's session goes on
            # (live 2026-11-26, as Germany after the taboo shot), so the scene's country is played again.
            try:
                self.verb("tag", {"tag": played})
                self.country = played
            except CaptureError:
                pass

    def shot(self, sid: str) -> dict:
        shot = self.m.SHOTS[sid]
        out: dict[str, Any] = {"id": sid, "out": shot["out"], "shows": shot.get("shows", ""), "scene": shot["scene"]}
        candidates = [c for c in self.m.shot_countries(shot) if c] or [self.country]
        tried: list[dict] = []
        for country in candidates:
            found = self.try_country(shot, country)
            tried.append(found)
            if found["met"]:
                break
        else:
            out["country"] = self.country
            if len(tried) == 1:
                out.update(needs=tried[0].get("needs", []), status="skipped", reason=tried[0]["reason"])
            else:
                out.update(tried=tried, status="skipped", reason="no candidate country met the needs: %s" % "; ".join(
                    "%s %s" % (t["country"], t["reason"]) for t in tried))
            return out
        out["country"] = self.country
        out["needs"] = tried[-1].get("needs", [])
        if len(tried) > 1:
            out["tried"] = tried[:-1]
        for name in shot.get("setups") or {}:
            self.verb("run-setup", {"name": name})
        event = shot.get("event")
        steps = [reset_step(self.m, self.previous_keys)] + [list(s) for s in shot.get("view") or [["close-panel"]]]
        view = self.verb("view", {"steps": steps}, VIEW_TIMEOUT_S)
        self.previous_keys = keys_set(shot.get("view") or [])
        out["view_log"] = view.get("log") or []
        scroll = shot.get("scroll")
        inputs = ([("wheel", *scroll)] if scroll else []) + [tuple(step) for step in shot.get("input") or []]
        for step in inputs:
            self.do_input(step)
        if inputs:
            # A click, a wheel or a drag latches the keyboard away (whether it moved the keyboard is not known): the
            # console's input line takes it back before anything types again.
            self.verb("click", {"console": True})
        if event:
            # Fired after the view (which closes the side panel), then `events` (the list waits for the console's
            # reply, by when the window is up); answered after the shot, its first option, so it covers nothing
            # later. The console's `event` ignores the event's trigger: a recipe names one whose text needs no
            # scope but the country's.
            self.verb("console", {"text": "event %s" % event})
            out["pending"] = self.verb("events", {}).get("pending")
        hover = shot.get("hover") or CONSOLE_PARK
        self.verb("hover", {"x": hover[0], "y": hover[1]})
        try:
            crop = self.verb("crop", {"box": list(self.m.crop_box(shot)), "settle": True, "label": sid})
        finally:
            if event:
                try:
                    out["picked"] = self.verb("pick", {"index": 0, "event": event}).get("form")
                except CaptureError as e:
                    out["pick_error"] = "%s: %s" % (e.code, e.detail)
        self.check_window(crop.get("window"))
        new = self.out_dir / ("%s%s" % (sid, ".png"))
        shutil.copyfile(crop["crop"], new)
        out.update(status="taken", new=str(new), settled=crop.get("settled"), tries=crop.get("tries"),
                   crop_size=crop.get("crop_size"), window=crop.get("window"))
        gap = self.m.shot_trim(shot)
        if gap:
            trimmed = trim_bottom(new, gap)
            if trimmed:
                out["trimmed"] = trimmed
                out["crop_size"] = [crop.get("crop_size", [0])[0], trimmed["height"]]
        return out

    def do_input(self, step: Sequence) -> None:
        """One input step of a recipe: ("click", x, y), ("wheel", x, y, notches) or ("drag", x1, y1, x2, y2)."""
        kind, args = step[0], list(step[1:])
        if kind == "click":
            self.verb("click", {"x": args[0], "y": args[1]})
        elif kind == "wheel":
            self.verb("wheel", {"x": args[0], "y": args[1], "notches": args[2]})
        elif kind == "drag":
            self.verb("drag", {"x1": args[0], "y1": args[1], "x2": args[2], "y2": args[3]})
        else:
            raise CaptureError("bad_input", "%r is not a click, wheel or drag" % (step,))

    def try_country(self, shot: Mapping, country: str) -> dict:
        """Play `country` (a `tag` when it is another) and read the shot's needs there: {country, met, needs,
        reason}. A country the save does not have is a need not met, as one formed away would be."""
        if country != self.country:
            try:
                self.verb("tag", {"tag": country})
            except CaptureError as e:
                if e.code != "tag_failed":
                    raise
                return {"country": country, "met": False, "reason": "not in this save (%s)" % e.detail}
            self.country = country
        needs = [need.replace("{tag}", country) for need in shot.get("needs") or []]
        if not needs:
            return {"country": country, "met": True, "needs": []}
        parsed = [self.m.parse_need(n) for n in needs]
        reads = self.read([expr for expr, _op, _num in parsed])
        listed, unmet = [], []
        for need, (_expr, op, num), read in zip(needs, parsed, reads):
            met = need_met(read, op, num)
            listed.append({"need": need, "value": read.get("value"), "ok": read.get("ok"), "met": met})
            if met is not True:
                unmet.append(need)
        return {"country": country, "met": not unmet, "needs": listed,
                "reason": "need not met: %s" % "; ".join(unmet) if unmet else ""}

    def read(self, exprs: list[str]) -> list[dict]:
        """`read`, once more after a `no_stop` (the first read after a late save's start can miss: #1702)."""
        try:
            return self.verb("read", {"exprs": exprs})["reads"]
        except CaptureError as e:
            if e.code != "no_stop":
                raise
            return self.verb("read", {"exprs": exprs})["reads"]

    def check_window(self, window) -> None:
        if self.window_checked or self.any_window:
            return
        want_w, want_s = list(self.m.WINDOW), self.m.UI_SCALE
        if list(window or []) != want_w or (self.ui_scale is not None and abs(self.ui_scale - want_s) > 1e-6):
            raise CaptureError("window_mismatch", "the window is %s at UI scale %s, and the manifest's regions were "
                               "measured at %s and %s: run in that window, or pass --any-window to take them anyway"
                               % (window, self.ui_scale, want_w, want_s))
        self.window_checked = True


# ---- trimming


TRIM_PAD = 24           # pixels kept below the last content row
TRIM_BRIGHT = 100       # a pixel brighter than this (0-255) is text, a bar or a frame, not the panel's background
TRIM_MIN = 3            # sampled pixels a row needs above TRIM_BRIGHT to hold content


def content_rows(path: Path, x_margin: tuple[float, float] = (0.05, 0.93)) -> list[bool] | None:
    """For each row of the picture, whether it holds content: more than TRIM_MIN of every second pixel between the
    margins brighter than TRIM_BRIGHT. A side panel's background is a dark texture (under 70 in the shots of
    2026-11-26) and its text and bars are bright. None without Pillow."""
    pil = _pillow()
    if pil is None:
        return None
    with pil[0].open(path) as im:
        grey = im.convert("L")
    w, h = grey.size
    data = grey.tobytes()
    lo, hi = int(w * x_margin[0]), int(w * x_margin[1])
    return [sum(1 for v in data[y * w + lo:y * w + hi:2] if v > TRIM_BRIGHT) > TRIM_MIN for y in range(h)]


def trim_line(rows: Sequence[bool], gap: int, pad: int = TRIM_PAD) -> int | None:
    """The height to keep: the content ends at the first run of `gap` or more empty rows below content (what is
    below that, such as the Market panel's World Market button, is the panel's footer, not the section's), or at
    the last content row; `pad` rows are kept below it. None when nothing would be cut."""
    last = None
    for y, filled in enumerate(rows):
        if filled:
            if last is not None and y - last - 1 >= gap:
                break
            last = y
    if last is None:
        return None
    keep = min(len(rows), last + 1 + pad)
    return keep if keep < len(rows) else None


def trim_bottom(path: Path, gap: int) -> dict | None:
    """Cut the empty panel below the content off the picture at `path`, in place: {height, cut} or None."""
    rows = content_rows(path)
    keep = trim_line(rows, gap) if rows else None
    if keep is None:
        return None
    Image = _pillow()[0]
    with Image.open(path) as im:
        im.load()
        cut = im.height - keep
        im.crop((0, 0, im.width, keep)).save(path)
    return {"height": keep, "cut": cut}


# ---- comparing, the contact sheet, writing back


def _pillow():
    try:
        from PIL import Image, ImageChops
    except ImportError:
        return None
    return Image, ImageChops


def compare(results: Mapping[str, dict], repo: Path, out_dir: Path) -> None:
    """For each taken shot: the committed picture copied beside the new one, `change` (new, resized, changed,
    unchanged, or unknown without Pillow), `changed_share` and a difference image when the sizes agree."""
    pil = _pillow()
    for sid, r in results.items():
        if r.get("status") != "taken":
            continue
        old = Path(repo) / r["out"]
        if is_workshop(r) or not old.is_file():
            r["change"] = "new"
            continue
        old_copy = Path(out_dir) / ("%s.old%s" % (sid, old.suffix))
        shutil.copyfile(old, old_copy)
        r["old"] = str(old_copy)
        if pil is None:
            r["change"] = "unknown"
            continue
        Image, ImageChops = pil
        with Image.open(old) as a, Image.open(r["new"]) as b:
            a, b = a.convert("RGB"), b.convert("RGB")
            r["old_size"] = list(a.size)
            if a.size != b.size:
                r["change"] = "resized"
                continue
            diff = ImageChops.difference(a, b)
            mask = diff.convert("L").point(lambda v: 255 if v > 8 else 0)
            share = sum(1 for v in mask.getdata() if v) / float(a.size[0] * a.size[1])
            r["changed_share"] = round(share, 6)
            r["change"] = "unchanged" if share == 0 else "changed"
            if share:
                path = Path(out_dir) / ("%s.diff.png" % sid)
                Image.composite(Image.new("RGB", a.size, (255, 0, 255)), b.point(lambda v: v // 3), mask).save(path)
                r["diff"] = str(path)


def why_no_diff(r: Mapping) -> str:
    """What the sheet says where a shot has no difference image."""
    if r.get("change") == "resized":
        old, new = r.get("old_size"), r.get("crop_size")
        return "none: the sizes differ (%s to %s)" % ("x".join(map(str, old or ["?"])), "x".join(map(str, new or ["?"])))
    if r.get("change") == "unchanged":
        return "none: the same pixels"
    if r.get("change") == "unknown":
        return "none: Pillow is not installed"
    return "none"


def contact_sheet(results: Mapping[str, dict], out_dir: Path, title: str) -> Path:
    """index.html in `out_dir`: one row a shot, old, new and difference side by side, with what it should show."""
    def img(path: str | None, label: str, missing: str = "none") -> str:
        if not path:
            return "<figure><figcaption>%s: %s</figcaption></figure>" % (label, html.escape(missing))
        name = os.path.basename(path)
        return ('<figure><a href="%s"><img src="%s" loading="lazy"></a><figcaption>%s</figcaption></figure>'
                % (html.escape(name), html.escape(name), label))

    rows = []
    for sid, r in results.items():
        facts = [r.get("status", "?")]
        if r.get("change"):
            facts.append(r["change"] + (" (%.2f%% of pixels)" % (100 * r["changed_share"])
                                        if r.get("changed_share") else ""))
        if r.get("settled") is False:
            facts.append("did not settle in %s shots" % r.get("tries"))
        if r.get("reason"):
            facts.append(r["reason"])
        if r.get("error"):
            facts.append("%s %s" % (r["error"], r.get("detail", "")))
        needs = "".join("<li><code>%s</code>: %s</li>" % (html.escape(n["need"]), html.escape(str(n["value"])))
                        for n in r.get("needs") or [])
        logs = "".join("<li><code>%s</code> ×%d</li>" % (html.escape(x["text"][:300]), x.get("count", 1))
                       for x in r.get("view_log") or [])
        rows.append('<section><h2>%s</h2><p class="facts">%s</p><p>%s</p>%s%s<div class="row">%s%s%s</div></section>'
                    % (html.escape(sid), html.escape(" · ".join(facts)), html.escape(r.get("shows", "")),
                       "<ul>%s</ul>" % needs if needs else "",
                       "<p>GUI lines logged by the view:</p><ul>%s</ul>" % logs if logs else "",
                       img(r.get("old"), "old", "none committed"), img(r.get("new"), "new", "not taken"),
                       img(r.get("diff"), "difference", why_no_diff(r))))
    page = ("<!doctype html><meta charset=utf-8><title>%s</title><style>body{font:14px system-ui;margin:2em;"
            "background:#f6f6f4;color:#222}section{background:#fff;padding:1em;margin:1em 0;border-radius:6px}"
            ".row{display:flex;gap:1em;align-items:flex-start}figure{margin:0;flex:1}img{max-width:100%%;"
            "border:1px solid #ccc}.facts{font-weight:600}</style><h1>%s</h1>%s"
            % (html.escape(title), html.escape(title), "".join(rows)))
    path = Path(out_dir) / "index.html"
    path.write_text(page, encoding="utf-8")
    return path


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True).stdout.strip()


def write_back(results: Mapping[str, dict], manifest, repo: Path, window_scale: tuple, save_of: Mapping[str, str]
               ) -> list[str]:
    """Copy each new or changed picture to its `out` and rewrite its row in TAKEN_FILE. Returns what was written."""
    pil = _pillow()
    taken_path = Path(repo) / TAKEN_FILE
    taken = json.loads(taken_path.read_text(encoding="utf-8")) if taken_path.is_file() else {}
    commit = _git(repo, "rev-parse", "HEAD")
    written = []
    for sid, r in results.items():
        if r.get("status") != "taken" or r.get("change") == "unchanged" or is_workshop(r):
            continue
        out = Path(repo) / r["out"]
        if out.suffix.lower() in (".jpg", ".jpeg"):
            if pil is None:
                r["write_error"] = "a .jpg needs Pillow"
                continue
            with pil[0].open(r["new"]) as im:
                im.convert("RGB").save(out, quality=90, subsampling=0)
        elif pil is not None:
            with pil[0].open(r["new"]) as im:
                im.save(out, optimize=True)
        else:
            shutil.copyfile(r["new"], out)
        data = out.read_bytes()
        cap = manifest.SHOTS[sid].get("max_kb", manifest.DEFAULT_MAX_KB)
        if len(data) > cap * 1024:
            r["over_cap_kb"] = len(data) // 1024
        taken[sid] = {"commit": commit, "taken": _dt.date.today().isoformat(), "window": window_scale[0],
                      "ui_scale": window_scale[1], "save": save_of.get(sid), "sha256": hashlib.sha256(data).hexdigest()}
        written.append(r["out"])
    taken_path.write_text(json.dumps(dict(sorted(taken.items())), indent=1) + "\n", encoding="utf-8")
    return written


# ---- the verb


def add_parser(sub, run) -> None:
    p = sub.add_parser("capture", help="take the pictures the shot manifest lists (scripts/image_pipeline/"
                                       "guide_shots.py): one capture session per scene, then a contact sheet")
    p.add_argument("--only", action="append", default=[], metavar="ID", help="a shot id (repeatable)")
    p.add_argument("--scene", action="append", default=[], metavar="NAME", help="only this scene's shots")
    p.add_argument("--permission", help="where the go-ahead to launch came from (needed unless --in-session)")
    p.add_argument("--in-session", action="store_true",
                   help="use the session already running (started with --capture), and leave it running")
    p.add_argument("--write", action="store_true",
                   help="copy each new or changed picture to its out path and record it in guide_shots_taken.json")
    p.add_argument("--any-window", action="store_true",
                   help="take them in a window other than the manifest's (its regions will be off)")
    p.add_argument("--workshop", action="store_true",
                   help="take the Workshop page's shots (out under workshop/), never written into the repo")
    p.add_argument("--list", action="store_true", help="list what would be taken, start nothing")
    p.set_defaults(run=run)


def main_verb(args, call: Call, start: Callable[[dict], tuple[dict, int]], stop: Callable[[], tuple[dict, int]],
              backup_root: Path, repo: Path = REPO) -> tuple[dict, int]:
    try:
        manifest = load_manifest(repo)
        problems = manifest.validate()
        if problems:
            raise CaptureError("bad_manifest", "; ".join(problems[:10]))
        ids = select(manifest, args.only, args.scene, getattr(args, "workshop", False))
        plan = by_scene(manifest, ids)
        if args.list:
            return {"plan": plan, "starts": 0 if args.in_session else len(plan)}, 0
        if not args.in_session and not (args.permission or "").strip():
            raise CaptureError("no_permission", "say where the go-ahead to launch came from (--permission), or "
                               "use a running session (--in-session)")
        if args.in_session and len(plan) > 1:
            raise CaptureError("one_scene", "--in-session takes one scene's shots, and these need %s: pass --scene"
                               % ", ".join(plan))
    except CaptureError as e:
        return {"refused": e.code, "detail": e.detail}, 2
    stamp = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = Path(backup_root) / "captures" / stamp
    out_dir.mkdir(parents=True, exist_ok=True)
    cap = Capture(manifest, call, out_dir, any_window=args.any_window)
    sessions: list[dict] = []
    for scene, scene_ids in plan.items():
        started = None
        if args.in_session:
            status, code = call("status", {})
            # The server's status nests the session's own facts under "session" (live 2026-11-26: read at the top,
            # every --in-session capture answered no_session).
            running = status.get("session") or {} if code == 0 else {}
            if not running.get("started") or running.get("stopped"):
                for sid in scene_ids:
                    cap.results[sid] = {"id": sid, "status": "not_run", "error": "no_session"}
                continue
            started = {"country": running.get("country"), "save": running.get("save")}
            if running.get("save") != manifest.SCENES[scene]["save"]:
                sessions.append({"scene": scene, "note": "the running session's save is %s, not the scene's %s"
                                 % (running.get("save"), manifest.SCENES[scene]["save"])})
        else:
            try:
                body = start_body(manifest, scene, scene_ids, args.permission)
            except CaptureError as e:
                return {"refused": e.code, "detail": e.detail}, 2
            reply, code = start(body)
            sessions.append({"scene": scene, "start": {k: reply.get(k) for k in (
                "snapshot", "save", "country", "capture", "run_dir", "refused", "detail", "next")}})
            if code != 0:
                for sid in scene_ids:
                    cap.results[sid] = {"id": sid, "status": "not_run", "error": reply.get("refused", "start")}
                # A failed start has stopped its session already, unless that stop can be run again: then the
                # server serves on for one more `stop` (client.start_session), which this gives it.
                if "stop" in reply and not server.final_stop(reply["stop"]):
                    stopped, _code = stop()
                    sessions[-1]["stop"] = {k: stopped.get(k) for k in ("outcome", "held", "reason", "next")}
                break               # the next scene's start would meet what refused this one
            started = reply
        try:
            cap.scene(scene, scene_ids, started)
        finally:
            if not args.in_session:
                stopped, _code = stop()
                sessions[-1]["stop"] = {k: stopped.get(k) for k in ("outcome", "held", "reason", "next", "refused")}
    compare(cap.results, repo, out_dir)
    sheet = contact_sheet(cap.results, out_dir, "%s shots, %s" % (
        "Workshop" if getattr(args, "workshop", False) else "Guide", stamp))
    written: list[str] = []
    if args.write:
        saves = {sid: manifest.SCENES[manifest.SHOTS[sid]["scene"]]["save"] for sid in cap.results}
        written = write_back(cap.results, manifest, repo, (list(manifest.WINDOW), manifest.UI_SCALE), saves)
    summary = {"capture_dir": str(out_dir), "contact_sheet": str(sheet), "sessions": sessions,
               "counts": {}, "results": cap.results, "written": written}
    for r in cap.results.values():
        summary["counts"][r.get("status", "?")] = summary["counts"].get(r.get("status", "?"), 0) + 1
    (out_dir / "capture.json").write_text(json.dumps(summary, indent=1, default=str) + "\n", encoding="utf-8")
    failed = any(r.get("status") in ("failed", "not_run") for r in cap.results.values())
    return summary, 2 if failed else 0


def _arg_namespace(**kw) -> argparse.Namespace:
    """For tests: the verb's arguments with their defaults."""
    base = dict(only=[], scene=[], permission=None, in_session=False, write=False, any_window=False, list=False,
                workshop=False)
    base.update(kw)
    return argparse.Namespace(**base)
