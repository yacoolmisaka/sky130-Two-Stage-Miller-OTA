#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
analyze_fingers.py
------------------
Dump, for every multi-finger gencell device, the exact geometry magic created:

  * diffusion islands   (ndiffc / pdiffc)  -> x centre, y span
  * metal1 S/D pad ring that belongs to each island
  * metal1 gate straps  (the short bars sitting between the islands)
  * metal1 gate feed rails / any other tall metal1

Everything is reported in the subcell's OWN coordinate system.

Usage:  python analyze_fingers.py
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MAG = os.path.join(HERE, "mag")

# name -> (mag file, top level placement dx dy)
DEVICES = {
    "M5":   ("sky130_fd_pr__nfet_01v8_SND6KL.mag", 1662, 957),
    "M6":   ("sky130_fd_pr__pfet_01v8_8MY6K8.mag", 7140, 4766),
    "M7":   ("sky130_fd_pr__nfet_01v8_9A3M24.mag", 7139, 2807),
    "Mref": ("sky130_fd_pr__nfet_01v8_RNGHDB.mag", 4589, 1007),
}


def read_sections(path):
    """Return {layer: [ (x1,y1,x2,y2), ... ]} plus the 'use' records."""
    secs = {}
    cur = None
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith("<<") and line.endswith(">>"):
                cur = line[2:-2].strip()
                secs.setdefault(cur, [])
                continue
            if cur is None:
                continue
            t = line.split()
            if not t:
                continue
            if t[0] == "rect" and len(t) >= 5:
                secs[cur].append(tuple(int(v) for v in t[1:5]))
            elif t[0] == "use":
                secs.setdefault("_use_", []).append(t[1:])
            elif t[0] == "string" and cur == "properties":
                secs.setdefault("_prop_", []).append(" ".join(t[1:]))
    return secs


def bbox(rects):
    xs1 = min(r[0] for r in rects)
    ys1 = min(r[1] for r in rects)
    xs2 = max(r[2] for r in rects)
    ys2 = max(r[3] for r in rects)
    return (xs1, ys1, xs2, ys2)


def overlaps(a, b):
    return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])


def main():
    for name, (fn, dx, dy) in DEVICES.items():
        path = os.path.join(MAG, fn)
        if not os.path.exists(path):
            print("%-5s MISSING %s" % (name, fn))
            continue
        s = read_sections(path)
        diffl = "ndiffc" if "ndiffc" in s else "pdiffc"
        islands = []
        for r in s.get(diffl, []):
            cx = (r[0] + r[2]) // 2
            cy = (r[1] + r[3]) // 2
            islands.append((cx, cy, r))
        islands.sort(key=lambda t: t[0])

        m1 = s.get("metal1", [])

        print("=" * 78)
        print("%-5s  %s" % (name, fn))
        print("=" * 78)
        params = " ".join(s.get("_prop_", []))
        m = re.search(r"nf\s+(\d+)", params)
        print("  gencell params : nf=%s" % (m.group(1) if m else "?"))
        print("  islands        : %d   (from << %s >>)" % (len(islands), diffl))
        print("  metal1 rects   : %d" % len(m1))
        print()

        # island -> m1 pad.  The pad is a hollow ring: the two caps (top/bottom)
        # CONTAIN the diffusion x-range, the two side strips do not.
        print("  idx  island_cx   diff_y        pad_x          pad_y        pad_w  pitch")
        prev = None
        for i, (cx, cy, r) in enumerate(islands):
            icy = (r[1] + r[3]) // 2
            caps = [q for q in m1 if q[0] <= r[0] and q[2] >= r[2]
                    and abs((q[1] + q[3]) // 2 - icy) < 300]
            if not caps:
                print("  %3d  %8d   %4d..%-4d  NO METAL1 PAD FOUND" % (i, cx, r[1], r[3]))
                prev = cx
                continue
            px1 = min(q[0] for q in caps)
            px2 = max(q[2] for q in caps)
            py1 = min(q[1] for q in caps)
            py2 = max(q[3] for q in caps)
            pitch = "" if prev is None else str(cx - prev)
            prev = cx
            print("  %3d  %8d   %5d..%-5d  %6d..%-6d  %5d..%-5d  %4d   %s"
                  % (i, cx, r[1], r[3], px1, px2, py1, py2, px2 - px1, pitch))

        print()
        # gate straps: metal1 bars that sit OUTSIDE the island y span
        iy1 = min(r[1] for _, _, r in islands)
        iy2 = max(r[3] for _, _, r in islands)
        gs = {}
        for q in m1:
            if q[1] >= iy2 or q[3] <= iy1:
                key = ((q[0] + q[2]) // 2 // 8, (q[1] + q[3]) // 2 // 8)
                gs.setdefault(key, []).append(q)
        gboxes = sorted((bbox(v) for v in gs.values()), key=lambda b: (b[1], b[0]))
        print("  metal1 bars outside the island y-band (%d..%d): %d groups"
              % (iy1, iy2, len(gboxes)))
        for b in gboxes[:8]:
            print("      x %6d..%-6d  y %6d..%-6d   (w %d h %d)"
                  % (b[0], b[2], b[1], b[3], b[2] - b[0], b[3] - b[1]))
        if len(gboxes) > 8:
            print("      ... (%d more)" % (len(gboxes) - 8))
        print()

        print("  TOP-LEVEL : placement (%d, %d)" % (dx, dy))
        print("     island centres x : %s ... %s"
              % (", ".join(str(dx + c[0]) for c in islands[:4]),
                 ", ".join(str(dx + c[0]) for c in islands[-2:])))
        print("     island y band    : %d..%d" % (dy + iy1, dy + iy2))
        print("     pad outer x      : %d..%d"
              % (dx + min(c[0] for _, _, c in islands) - 23,
                 dx + max(c[2] for _, _, c in islands) + 23))
        print()


if __name__ == "__main__":
    main()
