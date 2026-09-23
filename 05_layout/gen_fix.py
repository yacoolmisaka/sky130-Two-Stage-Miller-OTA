#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_fix.py -- build + verify the complete connectivity patch for ota2_miller.

Everything is computed in magic INTERNAL units and emitted as lambda
(internal / 2), because magic's `box` takes lambda, not internal units.

Outputs:
    fix_a.tcl   cleanup + opens + gate wiring      (run first)
    fix_b.tcl   source/drain bundling              (run second)

Then it replays both through sim.py and prints the resulting per-island nets.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

# ------------------------------------------------------------------ constants
SP_M1 = 28          # metal1 min spacing
SP_M2 = 28          # metal2 min spacing
VIA1 = 60           # via1 drawn 0.30 um
VIA2 = 60
WING_W = 200        # metal1 wing width
PITCH = 258

DEV = {
    "M5":   dict(tx=1662, ty=957,  n=13, pad=(757, 1157)),
    "M6":   dict(tx=7140, ty=4766, n=29, pad=(4566, 4966)),
    "M7":   dict(tx=7139, ty=2807, n=26, pad=(2557, 3057)),
    "Mref": dict(tx=4589, ty=1007, n=6,  pad=(757, 1257)),
}


def centres(d):
    n, tx = d["n"], d["tx"]
    span = (n - 1) * PITCH
    x0 = -span // 2
    return [tx + x0 + k * PITCH for k in range(n)]


A = []      # fix_a ops
B = []      # fix_b ops


def pa(layer, r):
    A.append(("paint", layer, r))


def ea(layer, r):
    A.append(("erase", layer, r))


def pb(layer, r):
    B.append(("paint", layer, r))


# =============================================================== A: cleanup
# --- 1. the bad metal1 bus that ties M5 islands 1..12 + Mref 0/1 to vbias
ea("metal1", (340, 776, 4180, 836))
# --- 2. dead stub hanging off it
ea("metal1", (3170, 714, 3320, 780))
# --- 3. the two via1 that land the vbias stack on M5 island 1 / island 11
ea("via1", (350, 866, 402, 918))
ea("via1", (2930, 866, 2982, 918))
# --- 4. the vbias metal2 stacks above them (would block the GND rail)
ea("metal2", (310, 742, 434, 954))
ea("metal2", (2890, 742, 3014, 954))
# --- 5. M6's half-finished vout stack (it stops at y=4990 and floats);
#        rebuilt cleanly by the M6 vout rail in fix_b.
ea("metal2", (3700, 4650, 3980, 5000))
ea("via1", (3772, 4730, 3822, 4782))
# --- 6. leftover 2-unit metal2 slivers: below min width (0.14um) AND they
#        silently stitch nets together.  All are < 0.01 um tall.
for r in [(160, 740, 3166, 742), (3990, 740, 5190, 742),
          (160, 1172, 3166, 1174), (3990, 1272, 5190, 1274),
          (160, 2540, 586, 2542), (1410, 2540, 1836, 2542),
          (3960, 2540, 10320, 2542),
          (160, 2972, 586, 2974), (1410, 2972, 1836, 2974),
          (160, 3940, 586, 3942), (1410, 3940, 1836, 3942),
          (160, 4390, 586, 4392), (1410, 4390, 3760, 4392),
          (3572, 4540, 10708, 4542), (3960, 3072, 10320, 3074),
          (3572, 4990, 10708, 4992)]:
    ea("metal2", r)
# --- 7. island-12 stub: sits 3 units from the new wing -> DRC spacing error
ea("metal1", (3262, 1160, 3304, 2200))
# --- 8. re-join the vbias column's lower stub (bad bus used to bridge it)
pa("metal1", (3660, 776, 3740, 836))

# =============================================================== A: opens
# n2: bridge the two halves of the n2 metal2 bus
pa("metal2", (3572, 4360, 3810, 4540))
# vout(M7.D): widen m2/m3 locally and drop via2 onto the vout bus
pa("metal2", (3812, 5080, 3960, 5180))
pa("metal3", (3860, 5080, 3960, 5190))
pa("via2", (3884, 5104, 3936, 5156))

# =============================================================== A: gates
# --- M5 gate -> vbias.  All 12 gates are already one poly net (gate_strap).
#     Contact it once through gate 11's TOP strap and run metal2 to vbias.
G11 = centres(DEV["M5"])[11] + PITCH // 2          # gate 11 centre
pa("metal1", (G11 - 81, 1188, G11 + 79, 1340))     # landing on the strap
pa("via1", (G11 - 51, 1250, G11 + 9, 1310))
pa("metal1", (3630, 1220, 3770, 1360))             # widen the vbias column
pa("via1", (3670, 1250, 3730, 1310))
pa("metal2", (2980, 1220, 3760, 1360))
# --- M6 gate -> n2.  Contact gate 1's BOTTOM strap, drop below the body.
G1 = centres(DEV["M6"])[1] + PITCH // 2
pa("metal1", (G1 - 95, 4380, G1 + 95, 4536))
pa("via1", (G1 - 55, 4400, G1 + 5, 4460))
pa("metal2", (3820, 4360, 4010, 4530))

# =============================================================== B: bundling
def bundle_dev(name, via_a, via_b, rail_a, rail_b):
    """via_a / via_b : (y1,y2) of the via1 for group A / group B
       rail_a/rail_b : full m2 rects for group A / group B"""
    d = DEV[name]
    cx = centres(d)
    y1, y2 = d["pad"]
    for k, X in enumerate(cx):
        pb("metal1", (X - WING_W // 2, y1, X + WING_W // 2, y2))
        vy = via_a if k % 2 == 0 else via_b
        pb("via1", (X - VIA1 // 2, vy[0], X + VIA1 // 2, vy[1]))
    for r in rail_a:
        pb("metal2", r)
    for r in rail_b:
        pb("metal2", r)


# ---- M5 : even islands -> ntail , odd islands -> GND
c5 = centres(DEV["M5"])
bundle_dev("M5", (1060, 1120), (800, 860),
           [(14, 1020, 3310, 1160)],
           [(272, 620, 3052, 900)])
#  ntail tap: land rail A on the existing metal1 stub that already carries
#  island 0 out to the ntail bus
pb("via1", (52, 1080, 112, 1140))

# ---- Mref : even -> vbias , odd -> GND
bundle_dev("Mref", (1040, 1100), (840, 900),
           [(3600, 1000, 5076, 1140)],
           [(4102, 800, 5334, 940), (5260, 300, 5360, 940)])
pb("metal1", (3630, 1000, 3770, 1140))     # widen vbias column for the via
pb("via1", (3670, 1040, 3730, 1100))

# ---- M6 : even -> VDD , odd -> vout
bundle_dev("M6", (4630, 4690), (4870, 4930),
           [(3428, 4590, 10852, 4730)],
           [(3686, 4830, 10594, 4970), (10400, 4960, 10600, 5100)])
pb("metal1", (3420, 4600, 3550, 4746))     # extend island-0 VDD landing
pb("via1", (3440, 4640, 3500, 4700))

# ---- M7 : even -> vout , odd -> GND
bundle_dev("M7", (2940, 3000), (2740, 2800),
           [(3814, 2900, 10206, 3040)],
           [(4072, 2700, 10464, 2840), (10400, 300, 10500, 2840)])
pb("metal3", (3840, 2900, 3980, 3040))     # widen the vout m3 column
pb("via2", (3880, 2940, 3940, 3000))


# ------------------------------------------------------------------ emit
def emit(ops, path, header):
    out = ["# " + "=" * 72,
           "#  " + path + "  -- AUTO-GENERATED by gen_fix.py, do not hand-edit",
           "# " + "=" * 72,
           "#  UNIT: magic `box` takes LAMBDA (1 lambda = 2 internal units).",
           "#  Every value below is therefore internal/2.",
           "#  " + header,
           "# " + "=" * 72, ""]
    for kind, layer, r in ops:
        x1, y1, x2, y2 = r
        assert x1 % 2 == 0 and y1 % 2 == 0 and x2 % 2 == 0 and y2 % 2 == 0, \
            "internal coord not even: %s" % (r,)
        out.append("box %d %d %d %d" % (x1 // 2, y1 // 2, x2 // 2, y2 // 2))
        out.append("%s %s" % (kind, layer))
        out.append("")
    open(os.path.join(HERE, path), "w", encoding="ascii", newline="\n").write(
        "\n".join(out) + "\n")
    print("wrote %-12s  %3d ops" % (path, len(ops)))


emit(A, "fix_a.tcl", "cleanup + opens + gate wiring")
emit(B, "fix_b.tcl", "source/drain bundling (m1 wing -> via1 -> m2 rail)")

# ------------------------------------------------------------------ verify
from sim import Layout, report, overlap

lo = Layout()
na = lo.apply_tcl(os.path.join(HERE, "fix_a.tcl"))
nb = lo.apply_tcl(os.path.join(HERE, "fix_b.tcl"))
print("applied fix_a=%d fix_b=%d ops" % (na, nb))

EXPECT = {
    "M5":   {"A": list(range(0, 13, 2)), "B": list(range(1, 13, 2))},
    "M6":   {"A": list(range(0, 29, 2)), "B": list(range(1, 29, 2))},
    "M7":   {"A": list(range(0, 26, 2)), "B": list(range(1, 26, 2))},
    "Mref": {"A": list(range(0, 6, 2)),  "B": list(range(1, 6, 2))},
}
WANT = {"M5": dict(A="ntail", B="GND"), "M6": dict(A="VDD", B="vout"),
        "M7": dict(A="vout", B="GND"), "Mref": dict(A="vbias", B="GND")}

report(lo, "after fix_a + fix_b")

print("-- EXPECTATION")
allok = True
for name in ("M5", "M6", "M7", "Mref"):
    for g in ("A", "B"):
        got = sorted({lo.net_of_tag("%s.isl%d" % (name, i))
                      for i in EXPECT[name][g]})
        want = WANT[name][g]
        ok = got == [want]
        allok &= ok
        print("   %-5s %s  want %-6s  got %-28s %s"
              % (name, g, want, ",".join(got), "OK" if ok else "**FAIL**"))
    gn = sorted({lo.net_of_tag("%s.g%d" % (name, k))
                 for k in range(DEV[name]["n"] - 1)})
    print("   %-5s gates -> %s" % (name, ",".join(gn)))
print()
print("ALL ISLAND NETS CORRECT" if allok else "*** STILL WRONG ***")
