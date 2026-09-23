# -*- coding: utf-8 -*-
"""
gen_gate_strap.py -- 用 poly 填充「栅极环之间的缝」，把多指器件的栅极连成一个网络

=============================================================================
为什么这么做（先说清原理，避免以后又绕弯）
-----------------------------------------------------------------------------
magic::gencell 生成的多指器件，每根指有一个独立的"口"字形 poly 栅极环，
相邻环之间只差 0.29um 的缝（全器件统一间距）。

    环1: x -7.595~-6.595  ┃缝 0.29um┃  环2: x -6.305~-5.305

这 0.29um 的缝里【没有别的图形】（S/D 列金属在环的高度之外，引出线是 metal1
不同层），所以直接用 poly 填满即可把所有环连成一条连续的栅极 poly。

相比 metal 总线的优势：
  · 同层直连，不需要 via1/via2，少两个可能出错的地方
  · poly 层在那个高度是空的，不会撞 n2 / vout 这些 metal2 横线
  · 同层重叠天然合法，不产生间距类 DRC

结果：magic 提取时所有 finger 共享同一个 G 网络
     → netgen 可用 parallel {w add} 把 N 个 finger 合并回单管。

=============================================================================
用法：
    cd 05_layout
    python3 gen_gate_strap.py > gate_strap.tcl      # 生成填充脚本
    python3 gen_gate_strap.py --erase > gate_strap_erase.tcl   # 生成撤销脚本
    magic 里：source ../gate_strap.tcl
"""
from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from typing import Dict, List, Tuple

# --------------------------------------------------------------------------- #
# 常量
# --------------------------------------------------------------------------- #
SC = 200.0                          # 1 um = 200 internal
MAG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mag")

# 栅极环宽度 1.0um，环中心间距 1.29um  →  缝宽 0.29um
RING_HALF = 0.50                    # 环半宽
# 填充块深入环内的量。
# ⚠️ 实测教训：设 0.02um 时 magic 提取识别不了这么薄的重叠，
#    填充块自己变成了孤立网络（网表里出现 a_856_680# 这类无名节点），
#    器件数反而从 65 涨到 66。必须大幅重叠。
OVERLAP = 0.30

# 顶层器件 -> (子 cell, transform x, transform y)
DEVICES: List[Tuple[str, str, int, int]] = [
    ("M1",   "sky130_fd_pr__nfet_01v8_7KZ2AN",  372, 2757),
    ("M2",   "sky130_fd_pr__nfet_01v8_7KZ2AN", 1622, 2757),
    ("M3",   "sky130_fd_pr__pfet_01v8_8FHKLD",  372, 4166),
    ("M4",   "sky130_fd_pr__pfet_01v8_8FHKLD", 1622, 4166),
    ("M5",   "sky130_fd_pr__nfet_01v8_SND6KL", 1662,  957),
    ("M6",   "sky130_fd_pr__pfet_01v8_8MY6K8", 7140, 4766),
    ("M7",   "sky130_fd_pr__nfet_01v8_9A3M24", 7139, 2807),
    ("Mref", "sky130_fd_pr__nfet_01v8_RNGHDB", 4589, 1007),
]


@dataclass
class Rect:
    x1: int
    y1: int
    x2: int
    y2: int

    def overlaps_y(self, lo: int, hi: int) -> bool:
        return not (self.y2 < lo or self.y1 > hi)


# --------------------------------------------------------------------------- #
# .mag 解析
# --------------------------------------------------------------------------- #
def read_layer(path: str, layer: str) -> List[Rect]:
    """读 .mag 中某个 << layer >> 段的全部 rect。"""
    text = open(path, encoding="utf-8", errors="ignore").read()
    m = re.search(r"<< %s >>(.*?)(?=<< |\Z)" % layer, text, re.S)
    if not m:
        return []
    out: List[Rect] = []
    for line in m.group(1).splitlines():
        mm = re.match(r"\s*rect\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)", line)
        if mm:
            out.append(Rect(*(int(v) for v in mm.groups())))
    return out


def group_by_row(rects: List[Rect]) -> List[List[Rect]]:
    """把 rect 按 y 区间分成若干「排」（顶部栅极环排 / 底部栅极环排）。"""
    groups: List[List[Rect]] = []
    for r in sorted(rects, key=lambda z: z.y1):
        placed = False
        for g in groups:
            ref = g[0]
            if not (r.y2 < ref.y1 - 40 or r.y1 > ref.y2 + 40):
                g.append(r)
                placed = True
                break
        if not placed:
            groups.append([r])
    return groups


# --------------------------------------------------------------------------- #
# 核心：为单个器件生成填充命令
# --------------------------------------------------------------------------- #
def build_device(name: str, cell: str, tx: int, ty: int, erase: bool) -> List[str]:
    path = os.path.join(MAG_DIR, cell + ".mag")
    if not os.path.exists(path):
        return ["#  跳过 %s：缺 %s.mag" % (name, cell)]

    contacts = read_layer(path, "polycont")
    if not contacts:
        return ["#  跳过 %s：无 polycont" % name]

    # 关键：y 范围要取【栅极环的完整高度】，不能用 polycont 的高度。
    # 实测：环高 0.44um(14.785~15.225)，而 polycont 只有 0.17um(14.975~15.145)。
    # 若按 polycont±0.03 填，两个方向的重叠只剩 0.03um，magic 提取判定为不连通。
    polys = read_layer(path, "poly")

    cmd = "ep" if erase else "bp"
    cmds: List[str] = []

    for row in group_by_row(contacts):
        row.sort(key=lambda r: r.x1)
        centers = [((r.x1 + r.x2) / 2.0) for r in row]

        # y 覆盖：取与该排 y 区间【有交叠】的所有 poly 矩形的并集，即整个环的高度
        y_lo = min(r.y1 for r in row)
        y_hi = max(r.y2 for r in row)
        band = [p for p in polys if p.overlaps_y(y_lo - 40, y_hi + 40)]
        if band:
            fy1 = min(p.y1 for p in band)
            fy2 = max(p.y2 for p in band)
        else:                                   # 兜底：向外扩 0.22
            fy1, fy2 = y_lo - 44, y_hi + 44
        Y1 = (fy1 + ty) / SC
        Y2 = (fy2 + ty) / SC

        # x 覆盖：相邻环之间填缝，两侧各深入环内 OVERLAP
        for i in range(len(centers) - 1):
            left_edge = centers[i] + RING_HALF * SC
            right_edge = centers[i + 1] - RING_HALF * SC
            x1 = left_edge - OVERLAP * SC
            x2 = right_edge + OVERLAP * SC
            if x2 <= x1:
                continue
            X1 = (x1 + tx) / SC
            X2 = (x2 + tx) / SC
            cmds.append("%s %.3f %.3f %.3f %.3f    ;# %s 栅极缝 %d-%d"
                        % (cmd, X1, Y1, X2, Y2, name, i + 1, i + 2))
    return cmds


# --------------------------------------------------------------------------- #
# 主程序
# --------------------------------------------------------------------------- #
def main() -> None:
    erase = "--erase" in sys.argv
    tag = "撤销" if erase else "填充"

    print("# ============================================================")
    print("#  gate_strap.tcl -- 自动生成（gen_gate_strap.py）")
    print("#  作用：用 poly %s相邻栅极环之间的 0.29um 缝，使多指器件的" % tag)
    print("#        所有 finger 共享同一个栅极网络（供 netgen 合并）")
    print("#  用法：magic 里  source ../gate_strap%s.tcl"
          % ("_erase" if erase else ""))
    print("# ============================================================")
    print()
    print("proc L  {v} { return [expr {round($v * 100)}] }")
    if erase:
        print("proc ep {x1 y1 x2 y2} { box [L $x1] [L $y1] [L $x2] [L $y2] ; erase poly }")
    else:
        print("proc bp {x1 y1 x2 y2} { box [L $x1] [L $y1] [L $x2] [L $y2] ; paint poly }")
    print()
    print("catch {select top cell}")
    print()

    total = 0
    for name, cell, tx, ty in DEVICES:
        cmds = build_device(name, cell, tx, ty, erase)
        print('puts "-- %s --"' % name)
        for c in cmds:
            if not c.startswith("#"):
                total += 1
            print(c)
        print()

    print("catch {select top cell}")
    print("catch {expand all}")
    print('puts "%s 完成：共 %d 条命令"' % (tag, total))
    if not erase:
        print('puts "接着：extract do local / extract all / ext2spice lvs / ext2spice / save / writeall force"')


if __name__ == "__main__":
    main()
