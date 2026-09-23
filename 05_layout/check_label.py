# -*- coding: utf-8 -*-
"""
check_label.py -- 精确核对 label 是否压在真正的金属上
不再猜，直接读 .mag 里所有 met1/met2/poly 的矩形，和 label 的矩形求交
"""
import re

MAG = r"D:\WorkBuddy\workspace\sky130 Two-Stage Miller OTA\05_layout\mag\ota2_miller.mag"
SC = 200.0

txt = open(MAG, "r", encoding="utf-8", errors="ignore").read()

# ---- 提取各层的矩形（只到第一个 use 为止，即顶层自己的几何）----
def grab_layer(name):
    m = re.search(r"<< %s >>(.*?)(?=<< \w+ >>|<< labels >>)" % name, txt, re.S)
    if not m:
        return []
    out = []
    for line in m.group(1).strip().splitlines():
        mm = re.match(r"rect\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)", line.strip())
        if mm:
            x1, y1, x2, y2 = map(int, mm.groups())
            out.append((x1, y1, x2, y2))
    return out

layers = {}
for nm in ["metal1", "metal2", "metal3", "via1", "via2", "via3", "pcontact", "poly"]:
    layers[nm] = grab_layer(nm)
    print("%-8s : %3d 个矩形" % (nm, len(layers[nm])))

# ---- 解析 label ----
labels = []
for mm in re.finditer(r"rlabel\s+(\S+)\s+\S+\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+\d+\s+(\S+)", txt):
    lay, x1, y1, x2, y2, name = mm.groups()
    labels.append((lay, int(x1), int(y1), int(x2), int(y2), name))

print("\n" + "=" * 70)
print(" label 有效性检查（label 矩形是否与所属层的金属相交）")
print("=" * 70)

def overlap(a, b):
    return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])

for lay, x1, y1, x2, y2, name in labels:
    L = (x1, y1, x2, y2)
    # 找同层金属
    hits = [r for r in layers.get(lay, []) if overlap(L, r)]
    # 也找所有层的（诊断用）
    allhits = {k: len([r for r in v if overlap(L, r)]) for k, v in layers.items()}

    status = "✅ 压在 %s 上 (%d 个矩形)" % (lay, len(hits)) if hits else "❌ 悬空！同层金属数 = 0"

    print("\n  label %-8s 层=%-7s 矩形 (%.3f,%.3f)-(%.3f,%.3f) um"
          % (name, lay, x1/SC, y1/SC, x2/SC, y2/SC))
    print("     %s" % status)
    if not hits:
        nz = {k: v for k, v in allhits.items() if v > 0}
        print("     其它层命中: %s" % (nz if nz else "全都没有"))
