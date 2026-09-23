# -*- coding: utf-8 -*-
"""
diag_lvs.py -- LVS 问题诊断工具
=============================================================================
两项诊断：
  1. label 悬空检测：读出 .mag 的 labels，逐个检查它下方是否真有对应层的金属。
     label 悬空 → magic 提取时不产生网络 → ext2spice 不输出为端口。
  2. finger 并联检测：解析版图网表，对每个多指器件检查 N 个 finger 是否真并联。
     不并联 → netgen 无法用 parallel {w add} 合并 → 器件数对不上。

用法：
    cd 05_layout && python3 diag_lvs.py
=============================================================================
"""
from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# --------------------------------------------------------------------------- #
# 常量
# --------------------------------------------------------------------------- #
SC = 200.0                       # 1 um = 200 internal units
MAG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mag")

# 顶层器件 -> (子 cell, transform x, transform y, 期望栅极信号)
DEVICES: List[Tuple[str, str, int, int, str]] = [
    ("M1",   "sky130_fd_pr__nfet_01v8_7KZ2AN",  372, 2757, "vinm"),
    ("M2",   "sky130_fd_pr__nfet_01v8_7KZ2AN", 1622, 2757, "vinp"),
    ("M3",   "sky130_fd_pr__pfet_01v8_8FHKLD",  372, 4166, "n1"),
    ("M4",   "sky130_fd_pr__pfet_01v8_8FHKLD", 1622, 4166, "n1"),
    ("M5",   "sky130_fd_pr__nfet_01v8_SND6KL", 1662,  957, "vbias"),
    ("M6",   "sky130_fd_pr__pfet_01v8_8MY6K8", 7140, 4766, "n2"),
    ("M7",   "sky130_fd_pr__nfet_01v8_9A3M24", 7139, 2807, "vbias"),
    ("Mref", "sky130_fd_pr__nfet_01v8_RNGHDB", 4589, 1007, "vbias"),
]

MAG_FILE = os.path.join(MAG_DIR, "ota2_miller.mag")
SPICE_FILE = os.path.join(MAG_DIR, "ota2_miller.spice")


# --------------------------------------------------------------------------- #
# 数据结构
# --------------------------------------------------------------------------- #
@dataclass
class Rect:
    """internal 单位的矩形。"""
    x1: int
    y1: int
    x2: int
    y2: int

    @property
    def width(self) -> float:
        return (self.x2 - self.x1) / SC

    @property
    def height(self) -> float:
        return (self.y2 - self.y1) / SC

    def area(self) -> int:
        return max(0, self.x2 - self.x1) * max(0, self.y2 - self.y1)

    def overlap(self, other: "Rect") -> int:
        """与另一矩形的重叠面积（internal^2）。"""
        ox = min(self.x2, other.x2) - max(self.x1, other.x1)
        oy = min(self.y2, other.y2) - max(self.y1, other.y1)
        return max(0, ox) * max(0, oy)

    def um(self) -> str:
        return (f"x {self.x1/SC:7.3f}~{self.x2/SC:7.3f}  "
                f"y {self.y1/SC:6.3f}~{self.y2/SC:6.3f}")


@dataclass
class Label:
    """一个 label（可能带 port 编号）。"""
    layer: str
    rect: Rect
    name: str
    port: Optional[int] = None


# --------------------------------------------------------------------------- #
# .mag 解析
# --------------------------------------------------------------------------- #
def parse_mag_layers(path: str) -> Dict[str, List[Rect]]:
    """读出 .mag 里所有 << layer >> 段中的 rect。"""
    text = open(path, encoding="utf-8", errors="ignore").read()
    layers: Dict[str, List[Rect]] = {}
    for m in re.finditer(r"<< (\w+) >>(.*?)(?=<< |\Z)", text, re.S):
        name, body = m.group(1), m.group(2)
        rects: List[Rect] = []
        for line in body.splitlines():
            mm = re.match(r"\s*rect\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)", line)
            if mm:
                rects.append(Rect(*(int(v) for v in mm.groups())))
        if rects:
            layers[name] = rects
    return layers


def parse_mag_labels(path: str) -> List[Label]:
    """读出 << labels >> 段里的 rlabel / port 行。"""
    text = open(path, encoding="utf-8", errors="ignore").read()
    m = re.search(r"<< labels >>(.*?)(?=<< end >>)", text, re.S)
    if not m:
        return []

    labels: List[Label] = []
    pending: Optional[Label] = None
    for line in m.group(1).splitlines():
        line = line.strip()
        if not line:
            continue
        # rlabel <layer> <s> <x1> <y1> <x2> <y2> <1> <name>
        rm = re.match(
            r"rlabel\s+(\S+)\s+\S+\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+\S+\s+(\S+)",
            line,
        )
        if rm:
            layer = rm.group(1)
            rect = Rect(*(int(rm.group(i)) for i in (2, 3, 4, 5)))
            pending = Label(layer=layer, rect=rect, name=rm.group(6))
            labels.append(pending)
            continue
        # port <n> <dir>
        pm = re.match(r"port\s+(\d+)\s+(\S+)", line)
        if pm and pending is not None:
            pending.port = int(pm.group(1))
    return labels


# --------------------------------------------------------------------------- #
# 诊断 1：label 悬空
# --------------------------------------------------------------------------- #
def diag_labels() -> None:
    print("=" * 74)
    print("  诊断 1：label 悬空检测")
    print("=" * 74)

    if not os.path.exists(MAG_FILE):
        print("  找不到", MAG_FILE)
        return

    layers = parse_mag_layers(MAG_FILE)
    labels = parse_mag_labels(MAG_FILE)

    print(f"  共 {len(labels)} 个 label\n")
    header = f"  {'名称':<8}{'层':<8}{'端口':<6}{'金属覆盖':<12}{'位置'}"
    print(header)
    print("  " + "-" * (len(header) - 2))

    bad: List[Label] = []
    for lb in labels:
        rects = layers.get(lb.layer, [])
        ov = max((lb.rect.overlap(r) for r in rects), default=0)
        if ov == 0:
            bad.append(lb)
            cover = "❌ 悬空"
        else:
            cover = f"✅ {ov/SC/SC:8.4f} um²"
        port = f"P{lb.port}" if lb.port else "-"
        print(f"  {lb.name:<8}{lb.layer:<8}{port:<6}{cover:<12}{lb.rect.um()}")

    print()
    if bad:
        names = ", ".join(b.name for b in bad)
        print(f"  ⚠️  悬空 label: {names}")
        print("     → 这些 label 下没有金属，magic 提取时不产生网络，")
        print("       ext2spice 因此不会把它们列为端口。")
    else:
        print("  ✅ 所有 label 都有金属覆盖")


# --------------------------------------------------------------------------- #
# 诊断 2：finger 并联
# --------------------------------------------------------------------------- #
def diag_fingers() -> None:
    print()
    print("=" * 74)
    print("  诊断 2：多指器件 finger 并联检测")
    print("=" * 74)

    if not os.path.exists(SPICE_FILE):
        print("  找不到", SPICE_FILE)
        return

    text = open(SPICE_FILE, encoding="utf-8", errors="ignore").read()

    print(f"  {'器件':<7}{'finger':<8}{'栅极网络(去重)':<28}{'并联组数':<10}{'判定'}")
    print("  " + "-" * 68)

    problems: List[str] = []
    for name, cell, _tx, _ty, sig in DEVICES:
        # 抓取该 cell 的 subckt 定义
        m = re.search(r"\.subckt\s+" + re.escape(cell) + r"(.*?)\n\.ends", text, re.S)
        if not m:
            print(f"  {name:<7}{'?':<8}(未找到定义)")
            continue

        body = m.group(1)
        insts = [ln.strip() for ln in body.splitlines() if ln.strip().startswith("X")]
        if not insts:
            continue

        # 解析每个 finger 的 D/G/S/B（X 行前 4 个节点）
        ports: List[Tuple[str, str, str, str]] = []
        for ln in insts:
            parts = ln.split()
            if len(parts) >= 5:
                ports.append((parts[1], parts[2], parts[3], parts[4]))   # D G S B

        # 并联组：G、B 相同，且 {D,S} 集合相同的归为一组
        groups: Dict[Tuple[str, str, frozenset], int] = {}
        for d, g, s, b in ports:
            key = (g, b, frozenset({d, s}))
            groups[key] = groups.get(key, 0) + 1

        gates = sorted({g for _d, g, _s, _b in ports})
        gate_txt = ", ".join(gates) if len(gates) <= 2 else f"{len(gates)} 个不同网络"

        ok = len(gates) == 1 and len(groups) == 1
        verdict = "✅ 全并联" if ok else f"⚠️ {len(groups)} 组/栅极{len(gates)}种"
        if not ok:
            problems.append(name)

        print(f"  {name:<7}{len(ports):<8}{gate_txt:<28}{len(groups):<10}{verdict}")

    print()
    if problems:
        print(f"  ⚠️  未完全并联: {', '.join(problems)}")
        print("     → 需确认每个器件的列1/列3 是否接同一网络，且栅极已连通。")
    else:
        print("  ✅ 所有多指器件的 finger 均已并联")


def main() -> None:
    if not os.path.isdir(MAG_DIR):
        print("目录不存在:", MAG_DIR)
        sys.exit(1)
    diag_labels()
    diag_fingers()
    print()


if __name__ == "__main__":
    main()
