#!/usr/bin/env python3
"""Which script a crash was running, read from a Victoria 3 minidump.

The exe ships without symbols, so `exception.txt` lists every frame as
`function-name not available`. The minidump still holds the crashing thread's
stack, and the frames on it point at the compiled script they were running:
variable names, effect and event keys, file paths. This reads them.

    crash_stack_strings.py <crash folder or minidump.dmp> [--min N] [--all]
                           [--depth BYTES] [--exe victoria3.exe]

Prints the exception, its RVA (the fault address minus the exe base, which
compares across launches of one build), the address an access violation
read or wrote, the general registers, the size of the stack above the
faulting frame, and every identifier-like string the stack points at, counted
once per pointing slot. Strings that name a mod scripted effect, trigger,
script value or event are starred; `--all` prints the rest too.

An access violation is not a loop, so its strings are pointed at once or
twice and the default `--min 20` hides them all: use `--min 1 --all`.
`--depth BYTES` lists each slot of the stack's first BYTES in order instead,
an exe return address or the text a pointer reaches, nearest the fault first.
Two crashes whose depth listings share their return addresses ran the same
call chain; on 2026-10-20 two such crashes held a different state key in the
same slot (STATE_CAMBODIA, STATE_LAOS), which named the per-state work they
were doing. `--exe` disassembles the exe around the fault (binutils
`objdump`) and prints the read-only strings that code references: the only
way to name the subsystem without symbols. It named mimalloc, the allocator,
for RVA 0x4223fd0. A crash inside the allocator, or one that reads through a
register holding random bits, is heap corruption: the damage was done earlier,
by other code, and the fault is only where it was next touched. The same
garbage register value in two launches means the save replays the damage
deterministically; bisect the autosaves (log-triage skill, 2026-10-20).

For a stack overflow the counts give the recursion away: the strings of the
loop's code show up once per round, so the top of the list shares one count
(198 for both 2026-10-17 crashes) and names the loop, here
`monument_events.26`, `gm_com_progress` and `gm_gift`. A count is evidence of
code run at that depth, not proof it is still on the stack: a slot can hold a
pointer left by a call that has returned, and a window can catch a neighbour
in the string pool. Confirm the loop in the script (log-triage skill,
2026-10-17).
"""
from __future__ import annotations

import argparse
import bisect
import collections
import glob
import os
import re
import struct
import subprocess
import sys

EXCEPTIONS = {
    0xC0000005: "EXCEPTION_ACCESS_VIOLATION",
    0xC00000FD: "EXCEPTION_STACK_OVERFLOW",
    0xC0000094: "EXCEPTION_INT_DIVIDE_BY_ZERO",
    0x80000003: "EXCEPTION_BREAKPOINT",
}
IDENT = re.compile(rb"[a-z][a-z0-9_.:]{5,}")
TEXT = re.compile(rb"[\x20-\x7e]{6,}")
REGISTERS = ("rax", "rcx", "rdx", "rbx", "rsp", "rbp", "rsi", "rdi",
             "r8", "r9", "r10", "r11", "r12", "r13", "r14", "r15", "rip")


class Minidump:
    """The streams this needs: module list (4), memory lists (5, 9), exception (6)."""

    def __init__(self, path):
        with open(path, "rb") as fh:
            self.b = fh.read()
        sig, _ver, n, dirrva = struct.unpack_from("<4sIII", self.b, 0)
        if sig != b"MDMP":
            raise SystemExit(f"{path}: not a minidump")
        self.streams = collections.defaultdict(list)
        for i in range(n):
            kind, size, rva = struct.unpack_from("<III", self.b, dirrva + 12 * i)
            self.streams[kind].append((size, rva))
        self.modules = self._modules()
        self.memory = self._memory()
        self._starts = [m[0] for m in self.memory]

    def _modules(self):
        out = []
        for _size, rva in self.streams[4]:
            for i in range(struct.unpack_from("<I", self.b, rva)[0]):
                base, size, _, _, name_rva = struct.unpack_from("<QIIII", self.b, rva + 4 + 108 * i)
                length = struct.unpack_from("<I", self.b, name_rva)[0]
                name = self.b[name_rva + 4:name_rva + 4 + length].decode("utf-16-le", "replace")
                out.append((base, size, name))
        return out

    def _memory(self):
        out = []  # (start, size, file offset)
        for _size, rva in self.streams[5]:
            for i in range(struct.unpack_from("<I", self.b, rva)[0]):
                out.append(struct.unpack_from("<QII", self.b, rva + 4 + 16 * i))
        for _size, rva in self.streams[9]:
            n, offset = struct.unpack_from("<QQ", self.b, rva)
            for i in range(n):
                start, size = struct.unpack_from("<QQ", self.b, rva + 16 + 16 * i)
                out.append((start, size, offset))
                offset += size
        return sorted(out)

    def read(self, addr, n):
        i = bisect.bisect_right(self._starts, addr) - 1
        if i < 0:
            return None
        start, size, offset = self.memory[i]
        if addr >= start + size:
            return None
        n = min(n, start + size - addr)
        return self.b[offset + addr - start:offset + addr - start + n]

    def exception(self):
        """(code, address, rsp) of the crashing thread."""
        rva = self.streams[6][0][1]
        code, _flags, _record, addr = struct.unpack_from("<IIQQ", self.b, rva + 8)
        _ctx_size, ctx_rva = struct.unpack_from("<II", self.b, rva + 160)
        rsp = struct.unpack_from("<Q", self.b, ctx_rva + 0x98)[0]  # AMD64 CONTEXT.Rsp
        return code, addr, rsp

    def registers(self):
        """({name: value} of the crashing thread, the address an access violation touched or None)."""
        rva = self.streams[6][0][1]
        nparams = struct.unpack_from("<I", self.b, rva + 32)[0]
        params = struct.unpack_from("<15Q", self.b, rva + 40)  # ExceptionInformation
        _ctx_size, ctx_rva = struct.unpack_from("<II", self.b, rva + 160)
        values = struct.unpack_from("<17Q", self.b, ctx_rva + 0x78)  # AMD64 CONTEXT.Rax .. Rip
        return dict(zip(REGISTERS, values)), (params[1] if nparams >= 2 else None)


def mod_script_names(mod_root):
    """Top-level keys of the mod's scripted effects, triggers and script values, and its event ids."""
    names = set()
    top = re.compile(r"^([A-Za-z_][\w.]*)\s*=", re.M)
    for pattern in ("common/scripted_effects/*.txt", "common/scripted_triggers/*.txt",
                    "common/script_values/*.txt", "events/**/*.txt"):
        for path in glob.glob(os.path.join(mod_root, pattern), recursive=True):
            with open(path, encoding="utf-8-sig", errors="replace") as fh:
                names.update(top.findall(fh.read()))
    names.discard("namespace")
    return names


def exe_strings_near(exe_path, rva, span=0x3000):
    """[(rva of the referencing instruction, text)] for the read-only strings code within `span` of `rva` references."""
    with open(exe_path, "rb") as fh:
        data = fh.read()
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    nsec = struct.unpack_from("<H", data, pe + 6)[0]
    opt = struct.unpack_from("<H", data, pe + 20)[0]
    image_base = struct.unpack_from("<Q", data, pe + 48)[0]
    sections = []
    for i in range(nsec):
        o = pe + 24 + opt + 40 * i
        vsize, va, _rsize, rptr = struct.unpack_from("<IIII", data, o + 8)
        sections.append((data[o:o + 8].rstrip(b"\0"), va, vsize, rptr))
    out = subprocess.run(["objdump", "-d", "--no-show-raw-insn",
                          f"--start-address={image_base + max(rva - span, 0):#x}",
                          f"--stop-address={image_base + rva + span:#x}", exe_path],
                         capture_output=True, text=True, check=True).stdout
    found = []
    for line in out.splitlines():
        m = re.search(r"#\s*0x([0-9a-f]+)", line)
        if not m:
            continue
        target = int(m.group(1), 16) - image_base
        for name, va, vsize, rptr in sections:
            if name in (b".rdata", b".data") and va <= target < va + vsize:
                text = TEXT.match(data, rptr + target - va)
                if text:
                    found.append((int(line.split(":")[0], 16) - image_base, text.group(0).decode()[:100]))
    return found


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("target", help="a crash folder (victoria3_<stamp>) or its minidump.dmp")
    ap.add_argument("--min", type=int, default=20, help="hide strings pointed at fewer times (default 20)")
    ap.add_argument("--all", action="store_true", help="print strings that name no mod script too")
    ap.add_argument("--depth", type=int, metavar="BYTES",
                    help="list the stack's first BYTES slot by slot, nearest the fault first, instead of counting")
    ap.add_argument("--exe", metavar="PATH", help="victoria3.exe: print the strings the code around the fault references")
    ap.add_argument("--mod-root", default=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    args = ap.parse_args(argv)

    path = os.path.join(args.target, "minidump.dmp") if os.path.isdir(args.target) else args.target
    dump = Minidump(path)
    exe = next((m for m in dump.modules if m[2].lower().endswith("victoria3.exe")), None)
    if exe is None:
        raise SystemExit("victoria3.exe is not in the module list")
    code, addr, rsp = dump.exception()
    print(f"{EXCEPTIONS.get(code, hex(code))} at rva {addr - exe[0]:#x}")
    regs, touched = dump.registers()
    if code == 0xC0000005 and touched is not None:
        print(f"touched address {touched:#x}")
    print("  ".join(f"{n} {v:#x}" for n, v in regs.items() if n not in ("rsp", "rip")))
    if args.exe:
        for at, text in exe_strings_near(args.exe, addr - exe[0]):
            print(f"  code at rva {at:#x} references: {text}")

    region = next((m for m in dump.memory if m[0] <= rsp < m[0] + m[1]), None)
    if region is None:
        raise SystemExit("the crashing thread's stack is not in the dump")
    start, size, offset = region
    stack = dump.b[offset + rsp - start:offset + size]
    modules = [(base, base + sz) for base, sz, _ in dump.modules]
    if args.depth:
        for i in range(0, min(len(stack), args.depth) - 7, 8):
            value = struct.unpack_from("<Q", stack, i)[0]
            if exe[0] <= value < exe[0] + exe[1]:
                print(f"{i:6} exe rva {value - exe[0]:#x}")
            elif value >= 0x10000 and not start <= value < start + size and not any(a <= value < b for a, b in modules):
                runs = [r.decode() for r in TEXT.findall(dump.read(value, 160) or b"")][:3]
                if runs:
                    print(f"{i:6} {value:#x} " + " | ".join(r[:90] for r in runs))
        return 0
    exe_slots = 0
    counts = collections.Counter()
    for i in range(0, len(stack) - 7, 8):
        value = struct.unpack_from("<Q", stack, i)[0]
        if exe[0] <= value < exe[0] + exe[1]:
            exe_slots += 1
            continue
        if value < 0x10000 or start <= value < start + size or any(a <= value < b for a, b in modules):
            continue
        window = dump.read(value - 64, 320)
        if window:
            counts.update({s.decode() for s in IDENT.findall(window)})
    print(f"stack above the fault: {len(stack):,} bytes, {exe_slots:,} slots holding an exe address")

    names = mod_script_names(args.mod_root)
    for text, n in counts.most_common():
        if n < args.min:
            break
        named = text in names
        if named or args.all:
            print(f"{n:6} {'*' if named else ' '} {text}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
