# -*- coding: utf-8 -*-
"""
analyze_drc.py -- 从 ota2_miller.mag 的 << error_s >> 段聚类分析 DRC 错误
把错误矩形映射到：器件内部几何 / 我画的走线 / 电源轨
"""
import re
from collections import defaultdict

MAG = r"D:\WorkBuddy\workspace\sky130 Two-Stage Miller OTA\05_layout\mag\ota2_miller.mag"
SC = 200.0  # 1 um = 200 internal

with open(MAG, "r", encoding="utf-8", errors="ignore") as f:
    txt = f.read()

# ---- 1. 提取 error_s 段 ----
m = re.search(r"<< error_s >>(.*?)<< metal1 >>", txt, re.S)
errs = []
if m:
    for line in m.group(1).strip().splitlines():
        mm = re.match(r"rect\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)", line.strip())
        if mm:
            x1, y1, x2, y2 = map(int, mm.groups())
            errs.append((x1, y1, x2, y2))

print("=" * 72)
print(" DRC 错误总数: %d" % len(errs))
print("=" * 72)

# ---- 2. 器件定义（从 .mag 的 use 段）----
devs = []
for mm in re.finditer(
    r"use\s+(\S+)\s+(\S+)\s*\ntimestamp\s+\d+\s*\ntransform\s+1\s+0\s+(-?\d+)\s+0\s+1\s+(-?\d+)\s*\nbox\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)",
    txt):
    cell, name, tx, ty, bx1, by1, bx2, by2 = mm.groups()
    tx, ty, bx1, by1, bx2, by2 = int(tx), int(ty), int(bx1), int(by1), int(bx2), int(by2)
    devs.append(dict(
        name=name, cell=cell,
        x1=tx + bx1, y1=ty + by1, x2=tx + bx2, y2=ty + by2,
        tx=tx, ty=ty, bx1=bx1, by1=by1, bx2=bx2, by2=by2,
    ))

print("\n---- 器件占位（um） ----")
for d in devs:
    print("  %-5s x %7.3f ~ %7.3f   y %7.3f ~ %7.3f   (%s)" % (
        d["name"], d["x1"]/SC, d["x2"]/SC, d["y1"]/SC, d["y2"]/SC, d["cell"][:34]))

# ---- 3. 我画的走线（手工列出 route_v3_phase1/2 + fix_* 的关键几何，um）----
# 只列 met2/met3/via2/via3 相关（因为错误集中在这些层）
routing = [
    # name, x1,y1,x2,y2, layer
    ("vout met2 横线(phase2 L55)", 19.000, 25.30, 87.900, 25.90, "metal2"),
    ("vout via2/via3 叠放(L57-58)", 87.150, 25.35, 87.650, 25.85, "via2/3"),
    ("nz via2+met2 块(L66-68)", 61.600, 10.60, 62.400, 11.10, "via2"),
    ("n2 met2 横线(L41)", 8.000, 21.80, 59.900, 22.60, "metal2"),
    ("n2 met2 竖线(L44)", 59.300, 5.80, 59.900, 22.60, "metal2"),
    ("fix_drc3 met3 竖线(L67)", 19.440, 13.300, 19.700, 25.950, "metal3"),
    ("fix_drc3 met2 焊盘(L50)", 19.240, 13.250, 19.900, 13.910, "metal2"),
    ("fix_drc3 met2 焊盘(L60)", 18.595, 23.450, 19.255, 24.110, "metal2"),
    ("fix_drc3 met2 补块(L69)", 19.420, 23.450, 19.720, 23.770, "metal2"),
    ("fix_drc3 met2 补块(L72)", 18.595, 23.480, 19.720, 23.740, "metal2"),
    ("fix_drc3 met2 (L78)", 18.760, 24.06, 19.60, 25.99, "metal2"),
    ("fix_drc3 met2 (L79)", 18.760, 25.380, 87.900, 25.990, "metal2"),
]

# ---- 4. 聚类：把错误矩形按 (x,y) 邻近分组 ----
# 简单连通聚类（阈值 40 internal = 0.2um）
def close(a, b, tol=60):
    return not (a[2] + tol < b[0] or b[2] + tol < a[0] or
                a[3] + tol < b[1] or b[3] + tol < a[1])

parent = list(range(len(errs)))
def find(x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x
def union(a, b):
    ra, rb = find(a), find(b)
    if ra != rb:
        parent[rb] = ra

for i in range(len(errs)):
    for j in range(i + 1, len(errs)):
        if close(errs[i], errs[j]):
            union(i, j)

groups = defaultdict(list)
for i in range(len(errs)):
    groups[find(i)].append(errs[i])

print("\n---- 错误聚类（共 %d 簇） ----" % len(groups))
srt = sorted(groups.values(), key=lambda g: -len(g))
for gi, g in enumerate(srt, 1):
    xs1 = min(r[0] for r in g); ys1 = min(r[1] for r in g)
    xs2 = max(r[2] for r in g); ys2 = max(r[3] for r in g)
    cx, cy = (xs1+xs2)/2.0/SC, (ys1+ys2)/2.0/SC

    # 判定归属
    owner = "??"
    for d in devs:
        if d["x1"]-60 <= xs1 and xs2 <= d["x2"]+60 and d["y1"]-60 <= ys1 and ys2 <= d["y2"]+60:
            owner = "器件 " + d["name"]
            break
    if owner == "??":
        for nm, x1, y1, x2, y2, lay in routing:
            if abs(cx - (x1+x2)/2.0) < 3.0 and abs(cy - (y1+y2)/2.0) < 3.0:
                owner = "走线 " + nm
                break
    if owner == "??":
        if cy > 29.5: owner = "VDD 轨区"
        elif cy < 1.5: owner = "GND 轨区"
        else: owner = "孤立/其他"

    print("\n  [簇 %2d] %3d 个错误  中心 (%.3f, %.3f) um" % (gi, len(g), cx, cy))
    print("         范围 x %.3f~%.3f  y %.3f~%.3f um" % (xs1/SC, xs2/SC, ys1/SC, ys2/SC))
    print("         归属: %s" % owner)

# ---- 5. 按器件汇总 ----
print("\n" + "=" * 72)
print(" 汇总：每个错误矩形落在哪个器件框内")
print("=" * 72)
cnt = defaultdict(int)
for r in errs:
    cx, cy = (r[0]+r[2])/2.0/SC, (r[1]+r[3])/2.0/SC
    hit = "器件外"
    for d in devs:
        if d["x1"]/SC <= cx <= d["x2"]/SC and d["y1"]/SC <= cy <= d["y2"]/SC:
            hit = d["name"]
            break
    cnt[hit] += 1
for k in sorted(cnt, key=lambda k: -cnt[k]):
    print("  %-12s %3d 个" % (k, cnt[k]))
