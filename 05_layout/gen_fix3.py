#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_fix3.py -- 修复 Miller 补偿支路 Rz / Cc 的拓扑错误，生成 fix3.tcl，并离线验证。

=============================================================================
【问题】原理图拓扑是    n2 --[Rz]-- nz --[Cc]-- vout
                        (net2)      (net4)

    XRz net4 net2 GND   ->  R0=net4(nz)  R1=net2(n2)  B=GND
    XCc net4 vout       ->  C0=net4(nz)  C1=vout

但版图提取出来的网表是：

    XRz vout VSUBS n2      <- R0 端是 vout，不是 nz
    XCc vout  ..._PMLRN3   <- Cc 只剩 1 个端口，C0(顶板) 根本没引出来

根因（已用几何实测确认，见下方 COORD LEDGER）：
  1. Cc 单元的两个极板
       - 底板 = metal3 框   -> top x 12300..17532, y 1000..5940
       - 顶板 = metal4 细框 -> top x 12379..17161, y 1079..5861（四条边框）
       magic 提取的 .ext 里 c1 节点层是 "mim"，即 mimcapcontact 那一层，
       对外只把 metal3(底板) 提成了端口。
  2. 右下角 via2 (17430..17530, 5070..5170)
       把 vout 的 metal2 总线 接到了 Cc 底板  ->  底板 = vout  [这是对的]
  3. 右下角 via3 (17430..17530, 5070..5170) 与 via2 同位置
       它压在 Cc 的 metal4 引出块 (top x 17432..17448 / 17512..17528) 上，
       而下方就是 Cc 底板 metal3  ->  **把 Cc 顶/底板直接短路**
  4. 左下角那簇 m1/via1/m2/via2/m3 堆栈 (top x 12292..12520, y 2080..2260)
       它的 metal3 环压在 Cc 底板上，往下经 via2->via1->metal1 落到 nz 网
       -> **把 nz 焊到了 vout 上**，nz 节点因此消失，Rz 与 Cc 变成并联

【修法】
  a. 擦掉左下簇的 via2   -> 断开 nz 与 Cc 底板
  b. 擦掉右下角的 via3   -> 解开 Cc 顶/底板短路
  c. 新建 顶板->nz 的堆栈：
       metal4(压住 Cc 顶板左边框) -> via3 -> metal3 -> via2 -> metal2 -> via1 -> metal1(nz)
     注意：所有 metal3 必须落在 Cc 底板 metal3 之外（x < 12292 - 56），
           否则又会焊回底板。
=============================================================================
"""
import os
import sys

import sim
from sim import Layout, MAG

HERE = os.path.dirname(os.path.abspath(__file__))

# ----------------------------------------------------------------- 坐标账本
# Cc 的 transform：use ... Cc / transform 1 0 14916 0 1 3470
CC_DX, CC_DY = 14916, 3470
CC_M3 = (12300, 1000, 17532, 5940)      # 底板 metal3 外框（top 坐标）
CC_M4L = (12379, 1079, 12381, 5861)     # 顶板 metal4 左边框
CC_M4R = (17159, 1079, 17161, 5861)     # 顶板 metal4 右边框
CC_M4T = (12379, 5859, 17161, 5861)     # 顶板 metal4 上边框
CC_M4B = (12379, 1079, 17161, 1081)     # 顶板 metal4 下边框

# 既有几何（来自 _dump_region.py 实测）
RZ_UPPER_M1 = (11510, 1100, 11980, 1340)   # Rz 上端 metal1 -> 经 via1/m2 竖柱 -> n2
RZ_LOWER_M1 = (11640, 2140, 12330, 2200)   # Rz 下端 metal1 -> nz (nz label 压在这条上)
N2_COL_M2   = (11860, 1160, 11980, 4360)   # n2 的 metal2 竖柱，新 m2 必须避开
LB_M3_RING  = (12292, 2092, 12428, 2248)   # 左下簇 metal3 环（= Cc 底板）
LB_M2_RING  = (12280, 2080, 12520, 2260)   # 左下簇 metal2 环（= nz）
LB_M1_RING  = (12320, 2120, 12480, 2220)   # 左下簇 metal1 环（= nz）
VOUT_BUS_M2 = (3812, 5096, 17430, 5170)    # vout metal2 总线

MIN_GAP = 56          # 0.28 um，sky130 宽金属(>0.3um)的最小间距
VIA = 56              # via 边长（与 gen_fix2.py 保持一致）

# fix3 的操作表：(动作, 层, internal 矩形, 说明)
OPS = [
    # ---- a. 断开左下簇 via2：让 Cc 底板脱离 nz -----------------------------
    ("erase", "via2",  (12300, 2100, 12420, 2240),
     "断 nz<->Cc底板：左下簇 m2/m3 之间的 via2 全部擦掉"),
    # ---- b. 解开右下角顶/底板短路 ------------------------------------------
    ("erase", "via3",  (17430, 5070, 17530, 5170),
     "擦掉误画的 via3：它把 Cc 底板(m3) 与 metal4 顶板引出块焊在一起"),
    # ---- c. 建 顶板 -> nz 的堆栈 -------------------------------------------
    ("paint", "metal4", (12160, 2100, 12420, 2260),
     "metal4：x>=12379 压住 Cc 顶板左边框，左端伸到 Cc 外以便落 via3"),
    ("paint", "metal3", (12020, 2120, 12236, 2224),
     "metal3：完全在 Cc 底板(x>=12300) 与左下簇 m3 环(x>=12292) 之外"),
    ("paint", "via3",   (12180, 2140, 12230, 2196),
     "via3：metal4 -> metal3"),
    ("paint", "metal2", (12040, 2120, 12520, 2224),
     "metal2：避开 n2 竖柱(<=11980) 60u，右端与左下簇 m2 环重叠并入 nz"),
    ("paint", "via2",   (12050, 2140, 12106, 2196),
     "via2：metal3 -> metal2"),
    ("paint", "via1",   (12200, 2140, 12256, 2196),
     "via1：metal2 -> metal1(nz 横线 11640..12330)"),
]


def E(v):
    """internal -> lambda，并要求 internal 为偶数（magic 栅格）"""
    assert v % 2 == 0, "internal coord not even: %d" % v
    return v // 2


def emit(path):
    out = []
    out.append("# -*- fix3.tcl  单位：LAMBDA（= internal/2）；internal 见 gen_fix3.py -*-")
    out.append("# 修复 Miller 支路 Rz/Cc：断开 nz<->vout 短路，把 Cc 顶板接到 nz")
    for act, lay, r, why in OPS:
        x1, y1, x2, y2 = (E(v) for v in r)
        assert x1 < x2 and y1 < y2, r
        out.append("")
        out.append("# " + why)
        out.append("box %d %d %d %d" % (x1, y1, x2, y2))
        out.append("%s %s" % (act, lay))
    open(path, "w", encoding="utf-8").write("\n".join(out) + "\n")
    return len(OPS)


# ------------------------------------------------------------------ 验证模型
def build(with_fix3=True):
    lo = Layout()
    # 把 Cc 的两个极板塞进模型（tag 区分底板/顶板）
    csecs, _ = sim.read_mag(os.path.join(MAG,
                                         "sky130_fd_pr__cap_mim_m3_1_PMLRN3.mag"))
    for lay, tag in (("metal3", "Cc.m3"), ("metal4", "Cc.m4")):
        for r in csecs.get(lay, []):
            lo.sub.append((lay,
                           (CC_DX + r[0], CC_DY + r[1],
                            CC_DX + r[2], CC_DY + r[3]), tag))
    lo.apply_tcl(os.path.join(HERE, "fix1.tcl"))
    lo.apply_tcl(os.path.join(HERE, "fix2.tcl"))
    if with_fix3:
        lo.apply_tcl(os.path.join(HERE, "fix3.tcl"))
    lo.solve()
    return lo


def probe(lo, title):
    print("=" * 78)
    print(" ", title)
    print("=" * 78)
    rows = [
        ("Cc 底板 (m3)", lo.net_of_tag("Cc.m3")),
        ("Cc 顶板 (m4)", lo.net_of_tag("Cc.m4")),
        ("Rz 上端 m1 ", lo.rect_net("metal1", RZ_UPPER_M1)[0]),
        ("Rz 下端 m1 ", lo.rect_net("metal1", RZ_LOWER_M1)[0]),
    ]
    for k, v in rows:
        print("   %-13s -> %s" % (k, v))
    return dict(rows)


def main():
    n = emit(os.path.join(HERE, "fix3.tcl"))
    print("wrote fix3.tcl   %d ops" % n)
    print()

    before = probe(build(False), "BEFORE（只应用 fix1+fix2）")
    print()
    after = probe(build(True), "AFTER（fix1+fix2+fix3）")
    print()

    # ---- 期望 ---------------------------------------------------------------
    want = {
        "Cc 顶板 (m4)": "nz",
        "Cc 底板 (m3)": "vout",
        "Rz 上端 m1 ": "n2",
        "Rz 下端 m1 ": "nz",
    }
    ok = True
    print("-- EXPECTATION CHECK (目标拓扑  n2 -[Rz]- nz -[Cc]- vout)")
    for k, w in want.items():
        got = after[k]
        good = (got == w)
        ok = ok and good
        print("   %-13s want=%-6s got=%-12s %s" % (k, w, got, "OK" if good else "BAD"))

    # ---- 关键：nz 与 vout 必须是两个不同的网 --------------------------------
    nz_net = after["Cc 顶板 (m4)"]
    vo_net = after["Cc 底板 (m3)"]
    sep = (nz_net != vo_net)
    ok = ok and sep
    print("   %-13s %s" % ("nz / vout 分离",
                           "OK" if sep else "BAD (仍然短路!)"))

    # ---- 间距复核（防止自己画的东西违规 / 短路）-----------------------------
    print()
    print("-- GEOMETRY SANITY")
    checks = [
        ("新 m3 右沿 vs 左下簇 m3 环左沿", LB_M3_RING[0] - 12236, MIN_GAP),
        ("新 m3 右沿 vs Cc 底板 m3 左沿", CC_M3[0] - 12236, MIN_GAP),
        ("新 m2 左沿 vs n2 竖柱 m2 右沿", 12040 - N2_COL_M2[2], MIN_GAP),
    ]
    for name, gap, need in checks:
        good = gap >= need
        ok = ok and good
        print("   %-32s gap=%3d (>=%d)  %s"
              % (name, gap, need, "OK" if good else "BAD"))
    # 新 m4 必须真的压到 Cc 顶板左边框
    hit = not (12420 < CC_M4L[0] or CC_M4L[2] < 12160 or
               2260 < CC_M4L[1] or CC_M4L[3] < 2100)
    ok = ok and hit
    print("   %-32s %s" % ("新 m4 压住 Cc 顶板左边框",
                           "OK" if hit else "BAD"))
    print()
    print(">>> " + ("FIX3 VERIFIED" if ok else "FIX3 FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
