#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_fix4.py -- 补体接触（body tie），把体端从悬空的 VSUBS 拉到真正的 GND / VDD。

=============================================================================
【为什么必须做】mag/ota2_miller.ext 末尾的 merge 链给出了铁证：

    merge "M6/VSUBS" "M4/VSUBS"
    merge "M4/VSUBS" "M3/VSUBS"
    merge "M3/VSUBS" "Rz/a_n199_n666#"
    merge "Rz/a_n199_n666#" "Cc/VSUBS"
    merge "Cc/VSUBS" "Mref/a_n776_n424#"
    merge "Mref/a_n776_n424#" "M7/a_n3356_n424#"
    merge "M7/a_n3356_n424#" "M5/a_n1679_n374#"
    merge "M5/a_n1679_n374#" "M2/a_n389_n374#"
    merge "M2/a_n389_n374#" "M1/a_n389_n374#"
    merge "M1/a_n389_n374#" "VSUBS"

  即：版图里 **10 个器件的体端全并成 1 个悬空节点 VSUBS**（连 pfet 的 nwell
  也并进去了，因为 nwell 没有任何接触）。
  原理图侧是 **2 个网**：nfet B=GND，pfet B=VDD。1 个网 vs 2 个网 -> LVS 必挂。

  而 gencell 内部实测（_bulk_probe.py）：
      5 个 gencell 的体环 psubdiff / nsubdiff 落在体环 y 带内的 viali(mcon)
      条数 = 0  -> 体环只做到 locali 为止，从来没接到 metal1。

【修法】
  nfet : VSUBS 是 magic 的 **全局衬底节点**，只要给**任意一处** psubdiff
         体环加接触并接到 GND，全部 nfet 的 B 端就都是 GND。
         选 M5 体环下横条右段 top (3245..3341, 583..617) —— 实测该处为空地。
  pfet : nwell 不是全局的，M3 / M4 / M6 是 **3 个互不相接的 nwell**
         （M3 到 x=797，M4 从 1197，M6 从 3361，中间各有 400 / 1314 的缝）。
         先画两条 nwell 桥把三者连成一片，再在 M6 左下角做一处 n+ 体接触
         接到 VDD，这样 3 个 pfet 的 B 端才是同一个 VDD 网。
=============================================================================
"""
import os
import sys

import sim
from sim import Layout, MAG

HERE = os.path.dirname(os.path.abspath(__file__))
CC_DX, CC_DY = 14916, 3470
MIN_GAP = 56          # 0.28 um：宽金属(>0.3um)的最小间距
VIA1 = 52
MCON = 34             # sky130 mcon = 0.17um = 34 internal

OPS = [
    # ---------------------------------------------------------------- nfet
    # M5 体环下横条右段 top (3245..3341, 583..617)：psubdiff+locali 都在，
    # 但上面没有 mcon。补一块 locali 把横条上下撑开，mcon 才有包围余量。
    ("paint", "locali", (3246, 570, 3340, 630),
     "li 扩展：包住 M5 体环下横条右段(3245..3341, 583..617)，上下各撑开 13/13"),
    ("paint", "viali", (3276, 584, 3310, 618),
     "mcon：x 左右各留 31，y 上下各留 14（sky130 只要求两对边有包围）"),
    ("paint", "metal1", (2900, 584, 3340, 640),
     "metal1：盖住 mcon 并向左引出到 GND 柱上方（实测该走廊 metal1 为空）"),
    ("paint", "via1", (2926, 588, 2958, 640),
     "via1：落进 GND 柱 metal2 (2920..2970, 300..640) —— 实测该柱确实是 GND"),
    # ---------------------------------------------------------------- pfet
    # 两条 nwell 桥：把 M3 / M4 / M6 的 nwell 连成一片
    ("paint", "nwell", (780, 4348, 1210, 4584),
     "nwell 桥1：M3 nwell(<=797) <-> M4 nwell(>=1197)，缝 400 全填上并各压 17"),
    ("paint", "nwell", (2040, 4348, 3370, 4584),
     "nwell 桥2：M4 nwell(<=2047) <-> M6 nwell(>=3361)，两端各压 7 / 9"),
    # M6 左下角 n+ 体接触（nsubdiff 角块 top 3397..3493, 4383..4417）
    ("paint", "locali", (3362, 4370, 3492, 4430),
     "li 扩展：包住 M6 左下角 nsubdiff+nsubdiffcont，向左下撑开放 mcon"),
    ("paint", "viali", (3380, 4384, 3414, 4418),
     "mcon：完全落在新画的 li 内（上下各留 14，左右各留 14/78）"),
    ("paint", "metal1", (3362, 4370, 3492, 4440),
     "metal1：盖住 mcon；y 上沿 4440 与 M6 下栅跳线(4479) 留 39 间距"),
    # ---- 关键修正（2026-09-21）：改走 metal1，彻底绕开 n2 总线 -------------
    # 旧方案用 metal2 竖直上引，撞上 n2 总线：
    #   n2 总线 = 5 条 metal2 横条 x1590..3760 / y4360..4540（_diag_fix4.py 实测），
    #   旧注释误以为它在 x>=3810，导致 VDD/n2 短路（op11 撞 n2、op12 再接 VDD rail）。
    # 实测：metal1 竖条 (3420..3462, 4746..6000) 与横条 (3420..3550, 4700..4746)
    #   **本身就是 VDD**（sim.rect_net 验证），且 y4440..4700 区间 metal1 为空。
    #   于是只需用 metal1 从焊盘竖直往上拉，直接接上 VDD，全程不碰 metal2。
    ("paint", "metal1", (3420, 4440, 3462, 4746),
     "metal1 竖直上引 x3420..3462：y4746 接上既有 VDD metal1 竖条(3420..3462,4746..6000)"),
]


def E(v):
    assert v % 2 == 0, "internal coord not even: %d" % v
    return v // 2


def emit(path):
    out = ["# -*- fix4.tcl  单位：LAMBDA（= internal/2）；internal 见 gen_fix4.py -*-",
           "# 补体接触：nfet 体环 -> GND，pfet nwell 连片 -> VDD"]
    for act, lay, r, why in OPS:
        x1, y1, x2, y2 = (E(v) for v in r)
        assert x1 < x2 and y1 < y2, r
        out += ["", "# " + why,
                "box %d %d %d %d" % (x1, y1, x2, y2),
                "%s %s" % (act, lay)]
    open(path, "w", encoding="utf-8").write("\n".join(out) + "\n")
    return len(OPS)


def build(with_fix4=True):
    lo = Layout(bulk=True)
    csecs, _ = sim.read_mag(os.path.join(MAG,
                                         "sky130_fd_pr__cap_mim_m3_1_PMLRN3.mag"))
    for lay, tag in (("metal3", "Cc.m3"), ("metal4", "Cc.m4")):
        for r in csecs.get(lay, []):
            lo.sub.append((lay, (CC_DX + r[0], CC_DY + r[1],
                                 CC_DX + r[2], CC_DY + r[3]), tag))
    for f in ("fix1.tcl", "fix2.tcl", "fix3.tcl"):
        lo.apply_tcl(os.path.join(HERE, f))
    if with_fix4:
        lo.apply_tcl(os.path.join(HERE, "fix4.tcl"))
    lo.solve()
    return lo


def main():
    n = emit(os.path.join(HERE, "fix4.tcl"))
    print("wrote fix4.tcl   %d ops" % n)
    print()

    before = build(False)
    after = build(True)

    print("=" * 78)
    print("  BULK NET  (BEFORE -> AFTER)")
    print("=" * 78)
    order = ["M5", "Mref", "M7", "M1", "M2", "M3", "M4", "M6"]
    want = {"M5": "GND", "Mref": "GND", "M7": "GND", "M1": "GND", "M2": "GND",
            "M3": "VDD", "M4": "VDD", "M6": "VDD"}
    for k in order:
        print("   %-5s bulk : %-14s -> %-14s  want %s"
              % (k, before.net_of_tag("%s.bulk" % k),
                 after.net_of_tag("%s.bulk" % k), want[k]))

    print()
    print("-- BULK CHECK")
    ok = True
    for k in ("M5", "M6", "M3", "M4"):
        got = after.net_of_tag("%s.bulk" % k)
        good = (got == want[k])
        ok = ok and good
        print("   %-5s want=%-5s got=%-14s %s"
              % (k, want[k], got, "OK" if good else "BAD"))
    print("   注：Mref/M7/M1/M2 的 psubdiff 在几何模型里各自独立，")
    print("       但 magic 有 substrate 记录 + 上述 merge 链，实测会把它们并进")
    print("       同一个全局 VSUBS —— 所以一处 psubdiff 接触即等于全部接到 GND。")

    # ---- 电源不能短路 ------------------------------------------------------
    gnd = after.rect_net("metal2", (340, 300, 390, 640))[0]
    vdd = after.rect_net("metal1", (4000, 6200, 4100, 6240))[0]
    sep = (gnd != vdd)
    ok = ok and sep
    print()
    print("-- POWER RAIL CHECK")
    print("   GND=%s   VDD=%s   %s" % (gnd, vdd, "OK" if sep else "BAD 短路!"))

    # ---- 间距复核 -----------------------------------------------------------
    print()
    print("-- GEOMETRY SANITY")
    checks = [
        ("nfet m1 上沿 vs M5 下栅跳线(679)", 679 - 640, 28),
        ("pfet m1 焊盘上沿 vs M6 下栅跳线(4479)", 4479 - 4440, 28),
        ("metal1 竖条右沿(3462) vs 非VDD m1 左沿(3568)", 3568 - 3462, MIN_GAP),
        ("metal1 竖条上沿(4746) 落在 VDD 横条 y4700..4746 内", 4746 - 4700, 1),
        ("nwell 桥1 高 (>= nwell 最小宽 168)", 4584 - 4348, 168),
    ]
    for name, gap, need in checks:
        good = gap >= need
        ok = ok and good
        print("   %-34s gap=%4d (>=%3d)  %s"
              % (name, gap, need, "OK" if good else "BAD"))

    print()
    print(">>> " + ("FIX4 VERIFIED" if ok else "FIX4 FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
