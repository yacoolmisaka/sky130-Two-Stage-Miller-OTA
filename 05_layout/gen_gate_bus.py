# -*- coding: utf-8 -*-
"""
gen_gate_bus.py -- 为多指器件生成「栅极总线」的 magic TCL 命令

=============================================================================
背景（2026-09-19 定位出的 LVS 根因）
-----------------------------------------------------------------------------
magic::gencell 生成的 sky130 器件，多指的栅极是 N 个独立的"口"字形 poly 环，
彼此间隔 0.29um 不相连。magic 提取时每个 finger 的 G 成为独立节点，于是
netgen 判定它们【不并联】，无法用 parallel {w add} 合并回单管。
→ LVS 报 80 devices vs 10 devices。

解决：画栅极总线（gate bus）把所有栅极环连成同一网络。

=============================================================================
为什么总线必须走 metal2
-----------------------------------------------------------------------------
栅极环所在的高度上，S/D 引出线（metal1）要穿过去接到 GND / ntail 电源轨。
如果总线也用 metal1，两者就会短路。所以：
    metal1 填充块（盖住 polycont）→ via1 → metal2 总线（从上方跨过引出线）

=============================================================================
用法：python3 gen_gate_bus.py > gate_bus.tcl
      magic 里：source ../gate_bus.tcl
      然后：extract all / ext2spice lvs / ext2spice / save / writeall force
"""
import re, os

SC = 200.0
MAG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mag')

# top cell 名, 子 cell 文件, transform x, transform y, 栅极要接的信号
DEVICES = [
    ('M1',   'sky130_fd_pr__nfet_01v8_7KZ2AN',  372, 2757, 'vinm'),
    ('M2',   'sky130_fd_pr__nfet_01v8_7KZ2AN', 1622, 2757, 'vinp'),
    ('M3',   'sky130_fd_pr__pfet_01v8_8FHKLD',  372, 4166, 'n1'),
    ('M4',   'sky130_fd_pr__pfet_01v8_8FHKLD', 1622, 4166, 'n1'),
    ('M5',   'sky130_fd_pr__nfet_01v8_SND6KL', 1662,  957, 'vbias'),
    ('M6',   'sky130_fd_pr__pfet_01v8_8MY6K8', 7140, 4766, 'n2'),
    ('M7',   'sky130_fd_pr__nfet_01v8_9A3M24', 7139, 2807, 'vbias'),
    ('Mref', 'sky130_fd_pr__nfet_01v8_RNGHDB', 4589, 1007, 'vbias'),
]

# via1 最小尺寸 0.26um
VIA = 0.26
# metal1 填充块高度：0.26 的 via1 + 上下各 0.02 包边 = 0.30
FILL_H = 0.30
# 填充块中心【向远离有源区的方向】偏移，拉开与 S/D 列金属的距离。
# 实测：栅极 polycont 在 y=±(1.235~1.405)，列金属(有源区)在 y=-0.940~0.940。
# 不偏移时填充块下沿约 -1.47，与列金属仅差 0.53 但外扩后仍偏紧 → 加 0.06 外推更稳。
FILL_SHIFT = 0.06


def rects_of(path, layer):
    txt = open(path, encoding='utf-8', errors='ignore').read()
    m = re.search(r'<< %s >>(.*?)(?=<< |\Z)' % layer, txt, re.S)
    if not m:
        return []
    out = []
    for l in m.group(1).strip().splitlines():
        mm = re.match(r'rect\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)', l.strip())
        if mm:
            out.append(tuple(int(x) for x in mm.groups()))
    return out


def build(name, cell, tx, ty, sig):
    p = os.path.join(MAG_DIR, cell + '.mag')
    if not os.path.exists(p):
        return ['#  跳过 %s: 缺 %s.mag' % (name, cell)], ''

    pc = rects_of(p, 'polycont')
    if not pc:
        return ['#  跳过 %s: 无 polycont' % name], ''

    # 按 y 把 polycont 分成「底部组」和「顶部组」
    groups = []
    for y1, y2 in sorted(set((r[1], r[3]) for r in pc)):
        hit = None
        for g in groups:
            if not (y2 < g[0] or y1 > g[1]):
                g[0] = min(g[0], y1); g[1] = max(g[1], y2); hit = g; break
        if not hit:
            groups.append([y1, y2])

    cmds, info = [], []
    for gy1, gy2 in groups:
        items = [r for r in pc if not (r[3] < gy1 or r[1] > gy2)]
        if not items:
            continue

        # 该行栅极接触的总 x 跨度
        x_min = min(r[0] for r in items)
        x_max = max(r[2] for r in items)
        cy = (gy1 + gy2) / 2.0

        # 填充块中心【向远离有源区】偏移 FILL_SHIFT，拉开与 S/D 列金属的距离：
        #   cy < 0（底部栅极环）→ 继续往下推；cy > 0（顶部环）→ 继续往上推。
        shift = FILL_SHIFT * SC if cy > 0 else -FILL_SHIFT * SC
        fy1 = cy + shift - FILL_H * SC / 2
        fy2 = cy + shift + FILL_H * SC / 2
        FY1 = (fy1 + ty) / SC
        FY2 = (fy2 + ty) / SC
        CY_FILL = (cy + shift + ty) / SC      # 填充块/总线/via1 共用的中心（顶层坐标）

        # 顺序很重要：① metal1 填充 → ② metal2 总线 → ③ 最后打 via1
        # 实测过「填充 → via1 → 总线」的顺序会被 magic 挡住：metal2 画在已有 via1 的区域上不生效
        # （.mag 里 metal2 在 via1 正上方是空的 → via1 悬空 → 栅极没连上）
        # 先铺好上下两层金属，最后打 via1 才能被两层金属夹住。

        # ① metal1 填充块：每个 contact 一块，不连成横条（横条会与 S/D 引出线短路）
        for r in items:
            fx1 = r[0] - 6          # x 向外扩 0.03 保证包住 contact
            fx2 = r[2] + 6
            X1 = (fx1 + tx) / SC
            X2 = (fx2 + tx) / SC
            cmds.append('bm  %.3f %.3f %.3f %.3f    ;# %s metal1 填充' % (X1, FY1, X2, FY2, name))

        # ② metal2 总线：一条横线，从上方跨过 S/D 引出线
        X1 = (x_min + tx) / SC
        X2 = (x_max + tx) / SC
        cmds.append('bm2 %.3f %.3f %.3f %.3f    ;# %s -> %s 栅极总线(met2)' % (
            X1, CY_FILL - 0.25, X2, CY_FILL + 0.25, name, sig))

        # ③ via1：最后打，夹在 metal1 与 metal2 之间
        for r in items:
            vx1 = (r[0] + tx) / SC
            vx2 = (r[2] + tx) / SC
            if (vx2 - vx1) < VIA:
                c = (vx1 + vx2) / 2
                vx1, vx2 = c - VIA / 2, c + VIA / 2
            cmds.append('bv1 %.3f %.3f %.3f %.3f    ;# %s via1' % (
                vx1 + 0.03, CY_FILL - VIA / 2 + 0.02, vx2 - 0.03, CY_FILL + VIA / 2 - 0.02, name))

        info.append('    x %.3f~%.3f  y %.3f (中心)  contact数=%d' % (X1, X2, CY_FILL, len(items)))

    return cmds, '\n'.join(info)


print('# ============================================================')
print('#  gate_bus.tcl  -- 自动生成（gen_gate_bus.py）')
print('#  为多指器件补栅极总线，顺序：metal1 填充 -> metal2 总线 -> via1（最后打）')
print('#    · metal1 填充每 contact 一块（连成横条会与 S/D 引出线短路）')
print('#    · metal2 总线从上方跨过 S/D 引出线（不同层，安全）')
print('#    · via1 最后打，被上下两层金属夹住')
print('# ============================================================')
print()
print('proc L   {v} { return [expr {round($v * 100)}] }')
print('proc bm  {x1 y1 x2 y2} { box [L $x1] [L $y1] [L $x2] [L $y2] ; paint metal1 }')
print('proc bm2 {x1 y1 x2 y2} { box [L $x1] [L $y1] [L $x2] [L $y2] ; paint metal2 }')
print('proc bv1 {x1 y1 x2 y2} { box [L $x1] [L $y1] [L $x2] [L $y2] ; paint via1 }')
print()
print('catch {select top cell}')
print()

for name, cell, tx, ty, sig in DEVICES:
    cmds, _ = build(name, cell, tx, ty, sig)
    print('puts "-- %s -> %s --"' % (name, sig))
    for c in cmds:
        print(c)
    print()

print('catch {select top cell}')
print('catch {expand all}')
print('puts "gate_bus 完成 -> extract all / ext2spice lvs / ext2spice / save / writeall force"')

# ---------------------------------------------------------------------------
# 同时生成 gate_bus_erase.tcl —— 安全网：一键撤销上面画的所有图形
# 用法：magic 里 source ../gate_bus_erase.tcl
# ---------------------------------------------------------------------------
erase_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'gate_bus_erase.tcl')
with open(erase_path, 'w', encoding='utf-8') as fh:
    fh.write('# ============================================================\n')
    fh.write('#  gate_bus_erase.tcl -- 撤销 gate_bus.tcl 画的所有图形（安全网）\n')
    fh.write('#  生成自 gen_gate_bus.py；坐标与 gate_bus.tcl 一致\n')
    fh.write('# ============================================================\n\n')
    fh.write('proc L   {v} { return [expr {round($v * 100)}] }\n')
    fh.write('proc em  {x1 y1 x2 y2} { box [L $x1] [L $y1] [L $x2] [L $y2] ; erase metal1 }\n')
    fh.write('proc em2 {x1 y1 x2 y2} { box [L $x1] [L $y1] [L $x2] [L $y2] ; erase metal2 }\n')
    fh.write('proc ev1 {x1 y1 x2 y2} { box [L $x1] [L $y1] [L $x2] [L $y2] ; erase via1 }\n\n')
    fh.write('catch {select top cell}\n\n')
    for name, cell, tx, ty, sig in DEVICES:
        cmds, _ = build(name, cell, tx, ty, sig)
        for c in cmds:
            # 把 paint 命令换成对应的 erase 命令
            c2 = c.replace('bm2 ', 'em2 ').replace('bv1 ', 'ev1 ').replace('bm  ', 'em  ')
            fh.write(c2 + '\n')
        fh.write('\n')
    fh.write('catch {select top cell}\n')
    fh.write('catch {expand all}\n')
    fh.write('puts "gate_bus 已撤销"\n')
print('# 已同时生成 gate_bus_erase.tcl（撤销用）')
