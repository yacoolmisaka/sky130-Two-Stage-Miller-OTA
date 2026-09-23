# -*- coding: utf-8 -*-
"""
analyze_drc2.py -- 把 DRC 错误坐标和我画的每条走线做交叉比对
目标：判定每个错误是「我引起的(met1.2间距)」还是「PDK器件固有」
"""
import re
from collections import defaultdict

MAG = r"D:\WorkBuddy\workspace\sky130 Two-Stage Miller OTA\05_layout\mag\ota2_miller.mag"
SC = 200.0
TOL = 0.05   # 0.05um 容差（internal=10）

txt = open(MAG, "r", encoding="utf-8", errors="ignore").read()

# ---------- error_s ----------
m = re.search(r"<< error_s >>(.*?)<< metal1 >>", txt, re.S)
errs = []
if m:
    for line in m.group(1).strip().splitlines():
        mm = re.match(r"rect\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)", line.strip())
        if mm:
            x1, y1, x2, y2 = map(int, mm.groups())
            errs.append((x1/SC, y1/SC, x2/SC, y2/SC))

# ---------- 器件 ----------
devs = []
for mm in re.finditer(
    r"use\s+(\S+)\s+(\S+)\s*\ntimestamp\s+\d+\s*\ntransform\s+1\s+0\s+(-?\d+)\s+0\s+1\s+(-?\d+)\s*\nbox\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)",
    txt):
    cell, name, tx, ty, bx1, by1, bx2, by2 = mm.groups()
    tx, ty, bx1, by1, bx2, by2 = int(tx), int(ty), int(bx1), int(by1), int(bx2), int(by2)
    devs.append(dict(name=name, cell=cell,
                     x1=(tx+bx1)/SC, y1=(ty+by1)/SC, x2=(tx+bx2)/SC, y2=(ty+by2)/SC))

# ---------- 我画的 met1 走线（route_v3_phase1 全文）----------
ROUTES = [
    ("A VDD M3.S列1",   0.455, 21.80, 0.685, 30.20),
    ("A VDD M3.S列3",   3.035, 21.80, 3.265, 30.20),
    ("A VDD M4.S列1",   6.705, 21.80, 6.935, 30.20),
    ("A VDD M4.S列3",   9.285, 21.80, 9.515, 30.20),
    ("A VDD M6.S列1",  17.520, 24.80, 17.750, 30.20),
    ("A VDD M6.S列29", 53.640, 24.80, 53.870, 30.20),
    ("B GND M5.S列2",   1.745,  1.30, 1.975,  3.78),
    ("B GND M5.S列12", 14.645,  1.30, 14.875, 3.78),
    ("B GND Mref.S列6",26.055,  1.30, 26.285, 3.78),
    ("B GND M7.S列26", 51.705,  1.30, 51.935, 12.80),
    ("C ntail 总线",    0.400, 10.80, 16.200, 11.30),
    ("C ntail M1.S列1", 0.455, 11.00, 0.685, 12.85),
    ("C ntail M1.S列3", 3.035, 11.00, 3.265, 12.85),
    ("C ntail M2.S列1", 6.705, 11.00, 6.935, 12.85),
    ("C ntail M2.S列3", 9.285, 11.00, 9.515, 12.85),
    ("C ntail M5.D列1", 0.455,  3.72, 0.685, 11.00),
    ("C ntail M5.D列13",15.935, 3.72, 16.165, 11.00),
    ("D n1 M3短接",     1.745, 21.70, 2.100, 22.40),
    ("D n1 M3G-M4G",    2.950, 19.35, 7.000, 19.65),
    ("D n1 M1.D",       1.745, 14.70, 1.975, 19.70),
    ("E vbias Mref短接",19.605,  6.20, 20.850,  6.80),
    ("E vbias 底部栅环", 1.700,  3.35, 20.900,  3.68),
    ("E vbias 上行",    18.300,  3.50, 18.700, 12.70),
    ("E vbias 接M7G",   18.300, 12.40, 20.200, 12.70),
    # phase2
    ("P2 n2 M2D-M4D",   7.995, 14.70, 8.225, 19.80),
    ("P2 n2 met1接RzP", 57.600,  5.50, 59.900,  5.75),
    ("P2 vout M7D",     19.455, 12.78, 19.685, 18.40),
    ("P2 vout 空隙",    18.810, 18.00, 19.700, 18.40),
    ("P2 vout M6D",     18.810, 18.00, 19.040, 25.70),
    ("P2 nz met1",      58.200, 10.70, 62.000, 11.00),
    # fix_drc4
    ("F4 M7D焊盘",      19.330, 13.340, 19.810, 13.820),
]

def in_route(r, rt):
    _, x1, y1, x2, y2 = rt
    cx, cy = (r[0]+r[2])/2.0, (r[1]+r[3])/2.0
    return (x1 - TOL <= cx <= x2 + TOL) and (y1 - TOL <= cy <= y2 + TOL)

def in_dev(r, d):
    cx, cy = (r[0]+r[2])/2.0, (r[1]+r[3])/2.0
    return d["x1"]-TOL <= cx <= d["x2"]+TOL and d["y1"]-TOL <= cy <= d["y2"]+TOL

print("=" * 74)
print(" 错误归属判定：%d 个错误矩形" % len(errs))
print("=" * 74)

stat = defaultdict(int)
mine, theirs = [], []
for r in errs:
    hit_route = None
    for rt in ROUTES:
        if in_route(r, rt):
            hit_route = rt[0]
            break
    hit_dev = None
    for d in devs:
        if in_dev(r, d):
            hit_dev = d["name"]
            break
    if hit_route:
        mine.append((r, hit_route))
        stat["我的走线: " + hit_route] += 1
    elif hit_dev:
        theirs.append((r, hit_dev))
        stat["器件固有: " + hit_dev] += 1
    else:
        theirs.append((r, "器件外/空隙"))
        stat["器件外/空隙"] += 1

print("\n---- 归属统计 ----")
for k in sorted(stat, key=lambda k: -stat[k]):
    print("  %-26s %3d" % (k, stat[k]))

print("\n  我的走线引起: %d 个" % len(mine))
print("  器件固有/其他: %d 个" % len(theirs))

print("\n---- 我的走线引起的前 30 个（坐标 um）----")
for r, who in mine[:30]:
    print("  (%.3f,%.3f)-(%.3f,%.3f)  w=%.3f h=%.3f  @ %s"
          % (r[0], r[1], r[2], r[3], r[2]-r[0], r[3]-r[1], who))

# ---------- 对 met1.2 spacing：看错误坐标是否落在器件内部等间距结构 ----------
print("\n" + "=" * 74)
print(" 补充：器件内部错误的空间分布（间距）")
print("=" * 74)
devcnt = defaultdict(list)
for r, who in theirs:
    devcnt[who].append(r)
for who in sorted(devcnt, key=lambda k: -len(devcnt[k])):
    rs = devcnt[who]
    xs = sorted(set(round((r[0]+r[2])/2.0, 2) for r in rs))
    print("\n  %s : %d 个" % (who, len(rs)))
    # 相邻 x 中心差
    diffs = [round(xs[i+1]-xs[i], 2) for i in range(len(xs)-1)]
    print("    x 中心: %s" % xs[:14])
    print("    相邻差: %s" % diffs[:14])
