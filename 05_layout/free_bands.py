#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
free_bands.py -- for each multi-finger device, find the y-bands inside the
device body where a horizontal metal2 rail can run across the whole device
without touching any EXISTING top-level metal2 / via1 / via2.

Report format: list of (y1, y2) free intervals, plus the blockers.
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
MAG = os.path.join(HERE, "mag")

DEVICES = {
    "M5":   ("sky130_fd_pr__nfet_01v8_SND6KL.mag", 1662, 957, "ndiffc"),
    "M6":   ("sky130_fd_pr__pfet_01v8_8MY6K8.mag", 7140, 4766, "pdiffc"),
    "M7":   ("sky130_fd_pr__nfet_01v8_9A3M24.mag", 7139, 2807, "ndiffc"),
    "Mref": ("sky130_fd_pr__nfet_01v8_RNGHDB.mag", 4589, 1007, "ndiffc"),
}


def read_mag(path):
    secs, cur = {}, None
    for line in open(path, "r", encoding="utf-8", errors="replace"):
        line = line.rstrip("\n")
        if line.startswith("<<") and line.endswith(">>"):
            cur = line[2:-2].strip(); secs.setdefault(cur, []); continue
        if cur is None: continue
        t = line.split()
        if t and t[0] == "rect":
            secs[cur].append(tuple(int(v) for v in t[1:5]))
    return secs


def pads(fn, diffl):
    s = read_mag(os.path.join(MAG, fn))
    m1 = s.get("metal1", [])
    out = []
    for r in s.get(diffl, []):
        cx = (r[0] + r[2]) // 2
        icy = (r[1] + r[3]) // 2
        caps = [q for q in m1 if q[0] <= r[0] and q[2] >= r[2]
                and abs((q[1] + q[3]) // 2 - icy) < 300]
        if caps:
            out.append((cx, min(q[0] for q in caps), max(q[2] for q in caps),
                        min(q[1] for q in caps), max(q[3] for q in caps)))
    out.sort()
    return out


def main():
    top = read_mag(os.path.join(MAG, "ota2_miller.mag"))
    # NOTE: metal3 does NOT block a metal2 rail (different layer, no contact).
    #       via1 / via2 DO block: an m2 rail overlapping them would short to
    #       the m1 / m3 net they belong to.
    obs_layers = ("metal2", "via1", "via2")
    SP = 28           # metal2 min spacing, internal units (0.14 um)

    for name, (fn, dx, dy, diffl) in DEVICES.items():
        p = pads(fn, diffl)
        xs1 = dx + p[0][1] - 60
        xs2 = dx + p[-1][2] + 60
        ys1 = dy + p[0][3]
        ys2 = dy + p[-1][4]
        print("=" * 74)
        print("%-5s  rail x-span %d..%d    island pad y band %d..%d"
              % (name, xs1, xs2, ys1, ys2))
        blockers = []
        for lay in obs_layers:
            for r in top.get(lay, []):
                if r[0] > xs2 or r[2] < xs1:
                    continue
                if r[1] > ys2 + 400 or r[3] < ys1 - 400:
                    continue
                blockers.append((lay, r))
        print("  blockers in x-span (%d):" % len(blockers))
        for lay, r in sorted(blockers, key=lambda z: z[1][1]):
            print("     %-7s x %6d..%-6d  y %6d..%-6d" % (lay, r[0], r[2], r[1], r[3]))

        # free y intervals inside [ys1, ys2] with spacing SP around each blocker
        iv = [(ys1 - 400, ys2 + 400)]
        for lay, r in blockers:
            lo, hi = r[1] - SP, r[3] + SP
            nxt = []
            for a, b in iv:
                if hi <= a or lo >= b:
                    nxt.append((a, b))
                    continue
                if lo > a:
                    nxt.append((a, lo))
                if hi < b:
                    nxt.append((hi, b))
            iv = nxt
        print("  FREE y bands (with %d spacing):" % SP)
        for a, b in iv:
            if b - a >= 60:
                print("     %6d..%-6d   (h=%d)" % (a, b, b - a))
        print()


if __name__ == "__main__":
    main()
