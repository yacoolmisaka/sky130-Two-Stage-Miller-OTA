#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fix_float.py <netlist> —— 给浮空节点补一个大电阻到地。

【问题】
  magic 提取会把悬空的金属岛也当成一个独立节点，并给出它到邻近网络的
  耦合电容（如 C17 m1_3660_752# vbias / C19 m1_3660_752# GND）。
  这类节点没有任何 DC 通路，于是 ngspice 报：
      Warning: singular matrix: check node m1_3660_752#
      Dynamic gmin stepping failed ...
      True gmin stepping failed -> source stepping failed
  DC 工作点求不出来，后面的 AC 结果就是假的（曾出现 av0 = -157dB）。

【做法】
  找出"只出现在寄生电容行、没出现在任何器件实例上"的节点，
  给每个挂一个 1T 欧姆到 0。
  1TΩ x 几十 fF 的转折频率在 mHz 量级，远低于关注的 1Hz~1GHz，
  对 AC 曲线没有可见影响，纯粹是为了给矩阵一条收敛用的 DC 通路。
"""
import sys

if len(sys.argv) < 2:
    sys.exit("usage: fix_float.py <netlist>")

src = sys.argv[1]
lines = open(src, encoding="utf-8").read().splitlines()

dev_nodes, cap_nodes = set(), set()
for ln in lines:
    s = ln.strip()
    if not s or s.startswith("*"):
        continue
    t = s.split()
    head = t[0]
    # 器件实例 X 行：t[1:-1] 是端口(最后一项是模型名)，但要剔除 ad=/pd=/w=/l= 参数
    if head.startswith("X") and len(t) > 2:
        dev_nodes.update(x for x in t[1:-1] if "=" not in x)
    # 电容行：C<name> n1 n2 value
    elif head.upper().startswith("C") and len(t) >= 4:
        cap_nodes.update(t[1:3])

floating = sorted(cap_nodes - dev_nodes)

out = list(lines)
if floating:
    out.append("")
    out.append("* --- auto-fixed floating nodes (no DC path) by fix_float.py ---")
    for i, n in enumerate(floating):
        out.append("Rfix%d %s 0 1T" % (i, n))

open(src, "w", encoding="utf-8").write("\n".join(out) + "\n")
print("fix_float: %s" % (", ".join(floating) if floating else "none"))
