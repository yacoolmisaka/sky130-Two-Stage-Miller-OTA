#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_fix2.py -- 生成 ota2_miller 的完整连通性修复脚本（第 2 代，全部坐标实测推导）

=============================================================================
单位（已用三重独立证据钉死，见 UNIT_PROOF）
  .mag rect 值      : magic INTERNAL unit, 1 unit = 0.005 um
  magic `box` 命令  : LAMBDA,            1 lambda  = 2 internal = 0.01 um
  => internal = 2 * (box 的值)
  本文件所有坐标一律用 INTERNAL unit 计算，输出时除以 2 并取整。
  顶层 transform 有奇数偏移(ty=957 等)，所以已有几何可落在奇数 internal 坐标；
  我们新画的只能落在偶数 internal 坐标（box 只能给整数 lambda），
  误差 <= 1 unit = 5 nm，对重叠判定无影响。

UNIT_PROOF
  器件 .mag 里 viali(=mcon) 宽 34 unit；sky130 mcon = 0.17 um  -> 1 unit = 0.005 um
  nmos 栅极 rect 200 x 400 unit = 1.0 x 2.0 um，spice 报 l=1 w=2       -> 吻合
  wiring 段 scalefactor 10 nanometers => lambda = 10 nm = 2 internal   -> 吻合
=============================================================================

器件几何（顶层坐标，从 .mag + transform 实测）
  M5   13 岛  x 114 ..3210  step258   岛 y 757..1157   栅跳线 y 1189..1235 / 679..725
  Mref  6 岛  x 3944..5234  step258   岛 y 757..1257   栅跳线 y 1289..1335 / 679..725
  M7   26 岛  x 3914..10364 step258   岛 y 2557..3057  栅跳线 y 3089..3135 / 2479..2525
  M6   29 岛  x 3528..10752 step258   岛 y 4566..4966  栅跳线 y 5007..5053 / 4479..4525

每个 finger 的源漏（由 .ext 的 device 行确认，权威）
  finger j : S = 岛 j , D = 岛 j+1      (12/28/25/5 个 finger)
  => 要让 12 个 finger 并联，必须 偶数岛一组 / 奇数岛一组；
     netgen 靠 `permute 1 3` 自动把奇数 finger 翻转，所以组内极性无所谓。

目标分组
  M5   偶->ntail  奇->GND    gate->vbias
  Mref 偶->vbias  奇->GND    gate->vbias (已是)
  M7   偶->vout   奇->GND    gate->vbias (已是)
  M6   偶->VDD    奇->vout   gate->n2
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MAG = os.path.join(HERE, "mag")

# ------------------------------------------------------------------ 器件参数
PITCH = 258
PAD_W = 80          # metal1 pad 宽度 (0.40 um)
VIA1 = 52           # via1 0.26 um
VIA2 = 56           # via2 0.28 um
MARGIN = 40         # pad 上下相对岛 m1 环的内缩
VIA_GAP = 22        # m2 rail 相对 via1 的包围余量

DEV = {
    # name : (岛0 中心 x, 岛数, 岛 y 范围, 偶数组网络, 奇数组网络)
    "M5":   dict(x0=114,  n=13, iy=(757, 1157),   na="ntail", nb="GND"),
    "Mref": dict(x0=3944, n=6,  iy=(757, 1257),   na="vbias", nb="GND"),
    "M7":   dict(x0=3914, n=26, iy=(2557, 3057),  na="vout",  nb="GND"),
    "M6":   dict(x0=3528, n=29, iy=(4566, 4966),  na="VDD",   nb="vout"),
}
# rail y 需要额外加宽以容纳 via2 的两个器件
RAIL_Y_OVERRIDE = {"M7": (2900, 3040), "M6B": (4580, 4720)}


def centres(d):
    return [d["x0"] + k * PITCH for k in range(d["n"])]


def E(v):
    """偶数化（box 只能收整数 lambda => internal 必须偶数）"""
    return int(round(v / 2.0)) * 2


# ------------------------------------------------------------------ 操作容器
OPS_A = []          # 清理 + 栅极
OPS_B = []          # 捆扎 + 引出


def ea(layer, r):
    OPS_A.append(("erase", layer, tuple(E(v) for v in r)))


def pa(layer, r):
    OPS_A.append(("paint", layer, tuple(E(v) for v in r)))


def eb(layer, r):
    OPS_B.append(("erase", layer, tuple(E(v) for v in r)))


def pb(layer, r):
    OPS_B.append(("paint", layer, tuple(E(v) for v in r)))


# =====================================================================
# A 段 1：清掉把 M5/Mref 的岛短接到 vbias 的坏总线
# =====================================================================
# 元凶：metal1 x340..4180 y776..836 横穿 M5 岛 1..12 与 Mref 岛 0/1
ea("metal1", (340, 776, 4180, 836))

# 岛12 原本靠这条坏总线挂到 vbias，留下会与 ntail 组打架
ea("metal1", (3180, 720, 3312, 776))
ea("metal1", (3180, 836, 3312, 1160))

# =====================================================================
# A 段 2：清掉所有 2 unit 高的 metal2 细线
#         它们 (a) 低于最小宽度 0.14um，(b) 会静默缝合网络
# =====================================================================
for r in [(160, 740, 3166, 742), (3990, 740, 5190, 742),
          (160, 1172, 3166, 1174), (3990, 1272, 5190, 1274),
          (160, 2540, 586, 2542), (1410, 2540, 1836, 2542),
          (3960, 2540, 10320, 2542),
          (160, 2972, 586, 2974), (1410, 2972, 1836, 2974),
          (160, 3940, 586, 3942), (1410, 3940, 1836, 3942),
          (160, 4390, 586, 4392), (1410, 4390, 3760, 4392),
          (3960, 3072, 10320, 3074),
          (3572, 4540, 10708, 4542), (3572, 4990, 10708, 4992)]:
    ea("metal2", r)

# =====================================================================
# A 段 3：清掉之前错位脚本留下的 junk（画到了 2x 位置，全部悬空）
# =====================================================================
for r in [(7144, 8720, 7620, 9080), (7504, 9970, 7920, 10160),
          (7504, 10160, 7920, 10192), (7624, 10192, 7920, 10208),
          (7624, 10208, 7768, 10312), (7872, 10208, 7920, 10312),
          (7624, 10312, 7920, 10360)]:
    ea("metal2", r)
for r in [(7720, 10160, 7920, 10208), (7720, 10208, 7768, 10312),
          (7872, 10208, 7920, 10312), (7720, 10312, 7920, 10380)]:
    ea("metal3", r)
ea("via2", (7768, 10208, 7872, 10312))

# =====================================================================
# A 段 3b：M6 左下角有一堆半成品 vout 堆栈碎片（x3710..4000, y4640..5000）
#          它们把 M6 岛1 吊在半空，且会把 VDD rail 桥到 vout rail。全部清掉，
#          岛1 改由 B 段新画的 pad -> via1 -> railB 接管。
# =====================================================================
ea("metal2", (3710, 4640, 4000, 5000))
ea("via1", (3772, 4730, 3822, 4782))

# =====================================================================
# A 段 4：接通 GND 柱（下半截 y300..640 是 GND，上半截 y742..830 悬空）
#         补上 640..742 的缺口后，柱顶 via1 -> m1 -> M5 岛1/岛11 即成 GND
# =====================================================================
pa("metal2", (340, 640, 390, 742))
pa("metal2", (2920, 640, 2970, 742))

# =====================================================================
# A 段 5：n2 总线缺口 x3572..3810；补上后 M6 的栅极才够得着 n2
# =====================================================================
pa("metal2", (3572, 4360, 3810, 4540))

# =====================================================================
# A 段 6：M6 栅极 -> n2
#   M6 最左栅跳线 m1 在 x3561..3753, y4479..4525；先把它加宽再打 via1
# =====================================================================
pa("metal1", (3561, 4380, 3753, 4530))
pa("via1", (3600, 4450, 3652, 4502))

# =====================================================================
# A 段 7：M5 栅极 -> vbias
#   M5 的 12 个栅极已被 gate_strap 用 poly 连成一体，只需把最右侧栅跳线
#   (x2985..3177, y1189..1235) 拉到 vbias 柱 (x3660..3740, y836..2480)
# =====================================================================
pa("metal1", (2990, 1189, 3700, 1235))

# =====================================================================
# B 段 1：四个器件的源漏捆扎
#   岛 m1 环上加 m1 pad -> via1 -> m2 rail，偶数组走上 rail、奇数组走下 rail
# =====================================================================
for name, d in DEV.items():
    cx = centres(d)
    iy1, iy2 = d["iy"]
    pad_y = (iy1 + MARGIN, iy2 - MARGIN)
    # via1 的 y：偶数组贴 pad 上沿，奇数组贴 pad 下沿
    viaA_y = (iy2 - MARGIN - 14 - VIA1, iy2 - MARGIN - 14)
    viaB_y = (iy1 + MARGIN + 14, iy1 + MARGIN + 14 + VIA1)
    even = [cx[k] for k in range(0, d["n"], 2)]
    odd = [cx[k] for k in range(1, d["n"], 2)]

    for k, X in enumerate(cx):
        pb("metal1", (X - PAD_W // 2, pad_y[0], X + PAD_W // 2, pad_y[1]))
        vy = viaA_y if k % 2 == 0 else viaB_y
        pb("via1", (X - VIA1 // 2, vy[0], X + VIA1 // 2, vy[1]))

    # m2 rail 的 y
    rA = (viaA_y[0] - VIA_GAP, viaA_y[1] + VIA_GAP)
    rB = (viaB_y[0] - VIA_GAP, viaB_y[1] + VIA_GAP)
    if name == "M7":
        rA = RAIL_Y_OVERRIDE["M7"]
    if name == "M6":
        rB = RAIL_Y_OVERRIDE["M6B"]
    # m2 rail 的 x：包住本组所有 via1，Mref/M7 的左端额外外伸以接续网络
    xA = (min(even) - VIA1 // 2, max(even) + VIA1 // 2)
    xB = (min(odd) - VIA1 // 2, max(odd) + VIA1 // 2)
    if name == "Mref":
        xA = (3650, xA[1])          # 伸到 vbias 的 via1 处
    if name == "M7":
        xA = (3830, xA[1])          # 伸到 m3 柱下方
    pb("metal2", (xA[0], rA[0], xA[1], rA[1]))
    pb("metal2", (xB[0], rB[0], xB[1], rB[1]))
    print("  %-5s railA y%s x%s   railB y%s x%s" % (name, rA, xA, rB, xB))

# =====================================================================
# B 段 2：Mref 偶数组 -> vbias
#   在 vbias 柱旁扩建 m1 pad，打 via1 接到 Mref 的 railA
# =====================================================================
pb("metal1", (3600, 1100, 3800, 1270))       # 与 vbias 柱 x3660..3740 重叠
pb("via1", (3650, 1151, 3702, 1203))

# =====================================================================
# B 段 3：M7 偶数组(vout) 与 M6 奇数组(vout) 共用那根已存在的 m3 竖柱
#   m3 x3868..3952 y2660..5190 本来就在，只是缺 via2；加宽后三处打 via2
# =====================================================================
pb("metal3", (3830, 2600, 3990, 5190))       # 加宽整根柱
pb("via2", (3862, 2940, 3918, 2996))         # -> M7 railA
pb("via2", (3862, 4630, 3918, 4686))         # -> M6 railB
pb("metal2", (3820, 5060, 4040, 5190))       # vout 总线局部加宽，给 via2 留包围
pb("via2", (3876, 5100, 3932, 5156))         # -> vout


# ------------------------------------------------------------------ 输出
def emit(ops, path, header):
    out = ["# " + "=" * 72,
           "#  %s  -- AUTO-GENERATED by gen_fix2.py (do not hand-edit)" % path,
           "#  " + header,
           "#",
           "#  UNIT: magic `box` takes LAMBDA (1 lambda = 2 internal units).",
           "#        Every value below is therefore internal/2.",
           "#        internal unit = 0.005 um ; lambda = 0.01 um",
           "# " + "=" * 72, ""]
    for kind, layer, r in ops:
        x1, y1, x2, y2 = r
        assert all(v % 2 == 0 for v in r), "odd internal coord %s" % (r,)
        out.append("box %d %d %d %d" % (x1 // 2, y1 // 2, x2 // 2, y2 // 2))
        out.append("%s %s" % (kind, layer))
        out.append("")
    with open(os.path.join(HERE, path), "w", encoding="ascii", newline="\n") as f:
        f.write("\n".join(out) + "\n")
    print("wrote %-11s %3d ops" % (path, len(ops)))


emit(OPS_A, "fix1.tcl", "cleanup + GND column + n2 gap + gate wiring")
emit(OPS_B, "fix2.tcl", "source/drain bundling + vout/vbias tap")

# ------------------------------------------------------------------ 仿真验证
sys.path.insert(0, HERE)
from sim import Layout            # noqa: E402

lo = Layout()
n1 = lo.apply_tcl(os.path.join(HERE, "fix1.tcl"))
n2 = lo.apply_tcl(os.path.join(HERE, "fix2.tcl"))
print("\napplied fix1=%d  fix2=%d ops" % (n1, n2))
lo.solve()

WANT = {"M5": ("ntail", "GND"), "M6": ("VDD", "vout"),
        "M7": ("vout", "GND"), "Mref": ("vbias", "GND")}
GATE = {"M5": "vbias", "M6": "n2", "M7": "vbias", "Mref": "vbias"}

print()
allok = True
for name in ("M5", "M6", "M7", "Mref"):
    d = DEV[name]
    for g, want in (("A", WANT[name][0]), ("B", WANT[name][1])):
        idx = range(0, d["n"], 2) if g == "A" else range(1, d["n"], 2)
        got = sorted({lo.net_of_tag("%s.isl%d" % (name, i)) for i in idx})
        ok = got == [want]
        allok &= ok
        print("  %-5s %s want %-6s got %-30s %s"
              % (name, g, want, ",".join(got), "OK" if ok else "**FAIL**"))
    gn = sorted({lo.net_of_tag("%s.g%d" % (name, k)) for k in range(d["n"] - 1)})
    ok = gn == [GATE[name]]
    allok &= ok
    print("  %-5s gate want %-6s got %-24s %s"
          % (name, GATE[name], ",".join(gn), "OK" if ok else "**FAIL**"))
print()
print(">>> ALL ISLAND / GATE NETS CORRECT" if allok else ">>> *** STILL WRONG ***")
