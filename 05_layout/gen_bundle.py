#!/usr/bin/env python3
"""
gen_bundle.py -- 生成「顶层 metal2 + via1 捆扎」脚本

数据来源（全部实测，无一推测）：
  1. 器件子 cell 的 .mag   -> 每个源漏岛的接触列 x 中心、metal1 焊盘 y 范围
  2. 器件子 cell 的 .ext   -> magic 亲自提取的 device 记录，
                             每条给出该指的 Source 节点 / Drain 节点
                             -> 据此对 nf+1 个岛做二分图着色，得到 D 组 / S 组
  3. 顶层 ota2_miller.mag  -> use 块的 transform，把子 cell 坐标搬到顶层坐标

捆扎原理（为什么这样设计）：
  器件内部通往外界的 m1 只有 0.23 µm 的岛焊盘，且相邻栅极环 m1 距它仅 0.05 µm，
  m1 无论横竖都挤不出去（见 LVS连通性诊断报告 §二）。
  但【顶层可以额外画 metal1 wing】：顶层 m1 与子 cell 的 m1 焊盘相压即同网，
  把每个岛的焊盘向右侧拓宽到 1.15 µm -> 足以合法容纳 via1（0.26 µm + 包围）。
  再用两条不同高度的 metal2 总线分别收纳 D 组/S 组的 via1 -> 源漏各自并联。
"""
import re, os, sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.abspath(__file__))
MAG = os.path.join(ROOT, 'mag')

SEC = re.compile(r'^<<\s*(\w+)\s*>>')
RECT = re.compile(r'^rect\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)\s*$')

# 单位换算：1 magic 内部单位 = 5 nm
UM = 0.005
M1_W = 28        # metal1 最小宽 0.14um
M1_S = 28        # metal1 最小间距 0.14um
M2_W = 28
M2_S = 28
VIA1 = 52        # via1 最小宽 0.26um（tech: width v1/m1 260）
LI_S = 34


def load_mag(path):
    layers, cur = defaultdict(list), None
    for line in open(path, encoding='utf-8', errors='replace'):
        line = line.strip()
        m = SEC.match(line)
        if m:
            cur = m.group(1); continue
        m = RECT.match(line)
        if m and cur:
            x0, y0, x1, y1 = map(int, m.groups())
            layers[cur].append((min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)))
    return layers


def parse_ext_node_layers(path):
    """.ext 里 node 记录的第 7 个字段就是层名：'p'=poly, 'ndif'/'pdif'=扩散"""
    lay = {}
    for line in open(path, encoding='utf-8', errors='replace'):
        if not line.startswith('node '):
            continue
        t = line.split()
        name = t[1].strip('"')
        if len(t) < 7:
            continue
        lay[name] = t[6]
    return lay


def parse_ext_devices(path):
    """返回 [(x, y, {'G':..,'T1':..,'T2':..}), ...]
    节点角色由【节点自身的层】判定，不靠位置：
        p/polysilicon  -> 栅
        ndif/pdif/...  -> 源漏端子
    """
    nlay = parse_ext_node_layers(path)
    out = []
    for line in open(path, encoding='utf-8', errors='replace'):
        if not line.startswith('device '):
            continue
        t = line.split()
        x, y = int(t[3]), int(t[4])
        names = re.findall(r'"([^"]+)"', line)
        gate = [n for n in names if nlay.get(n) in ('p', 'polysilicon', 'xpolycontact')]
        sd = [n for n in names
              if n not in gate and nlay.get(n) in ('ndif', 'pdif', 'mvndif', 'mvpdiff')]
        if len(gate) != 1 or len(sd) != 2:
            print('   ⚠ device 节点解析异常: gate=%d term=%d (%s)'
                  % (len(gate), len(sd), names))
            continue
        out.append((x, y, {'G': gate[0], 'T1': sd[0], 'T2': sd[1]}))
    return out


def node_x(name):
    """a_n1577_n200#  ->  -1577 ;  a_1519_n200# -> 1519"""
    m = re.match(r'^a_(n?\d+)_', name)
    s = m.group(1)
    return -int(s[1:]) if s.startswith('n') else int(s)


def islands_from_mag(cell):
    """返回 [(cx, ys), ...] 每个岛：接触列中心 x，metal1 焊盘 x/y 范围"""
    lay = load_mag(os.path.join(MAG, cell + '.mag'))
    # 接触列：ndiffc / pdiffc
    diffl = 'ndiffc' if 'ndiffc' in lay else 'pdiffc'
    cols = sorted({(r[0] + r[2]) // 2 for r in lay[diffl]})
    pads = []
    for cx in cols:
        xs = [r for r in lay.get('metal1', [])
              if r[0] >= cx - 40 and r[2] <= cx + 40 and abs((r[0] + r[2]) // 2 - cx) <= 40]
        if not xs:
            continue
        x0 = min(r[0] for r in xs); x1 = max(r[2] for r in xs)
        y0 = min(r[1] for r in xs); y1 = max(r[3] for r in xs)
        pads.append((cx, x0, x1, y0, y1))
    return diffl, pads


def bipartition(devs, pads):
    """
    用 .ext 的 device 记录把 nf+1 个岛二分成 D 组 / S 组。
    做法：指j夹在两个相邻岛之间 -> 该指的 S 节点属于一个岛、D 节点属于另一个岛。
    直接建图做二染色。
    """
    cx2idx = {p[0]: i for i, p in enumerate(pads)}
    offs = []
    for x, y, n in devs:
        for tag in ('T1', 'T2'):
            nx = node_x(n[tag])
            best = min(pads, key=lambda p: abs(p[0] - nx))
            offs.append(best[0] - nx)
    off = max(set(offs), key=offs.count)
    def idx_of(node):
        nx = node_x(node) + off
        return cx2idx.get(nx)
    adj = defaultdict(set)
    term_names = {}          # (a,b) -> 该指的端子名
    for x, y, n in devs:
        a, b = idx_of(n['T1']), idx_of(n['T2'])
        if a is None or b is None:
            continue
        adj[a].add(b); adj[b].add(a)
    color = {}
    for s in sorted(adj):
        if s in color:
            continue
        color[s] = 0
        stack = [s]
        while stack:
            u = stack.pop()
            for v in adj[u]:
                if v not in color:
                    color[v] = 1 - color[u]
                    stack.append(v)
                elif color[v] == color[u]:
                    raise SystemExit('✗ 二染色失败：岛 %d 与 %d 冲突' % (u, v))
    grp = defaultdict(list)
    for i in range(len(pads)):
        grp[color.get(i, 0)].append(i)
    # 含「最左器件 T1」的那一组命名為 T1 组
    first = None
    for x, y, n in sorted(devs, key=lambda d: d[0]):
        first = idx_of(n['T1'])
        if first is not None:
            break
    if first is not None and color.get(first, 0) != 0:
        grp = {0: grp.get(1, []), 1: grp.get(0, [])}
    return off, grp[0], grp[1]      # 0 = T1 组, 1 = T2 组


def emit(name, cell, tx, ty, diffl, pads, sgrp, dgrp, via1_side='right'):
    """
    输出 tcl 片段。
    wing：向 via1_side 侧延展，使 metal1 局部宽度达到 ~230 单位(1.15um)，足以放 via1
    S 组走低处的 metal2 总线，D 组走高处的，两者 y 完全错开 -> 不会互压
    """
    L = []
    n = len(pads)
    pit = pads[1][0] - pads[0][0] if n > 1 else 258
    # 全局 x 范围（顶层坐标）
    gx0 = tx + pads[0][1]                      # 最左岛的 m1 左边沿
    lead = n and None
    # 每条 wing 的可用宽度上限：右到下一相邻列的 m1 保持 M1_S 间距
    half_r = pit - 23 - M1_S                   # = 258-23-28 = 207
    WING = 230
    assert half_r + 23 >= WING, 'wing 宽度放不下'

    ys = [p[3] for p in pads]
    ye = [p[4] for p in pads]
    pad_top = tx and None
    y_lo = min(ys) + ty
    y_hi = max(ye) + ty
    H = y_hi - y_lo
    if H < 2 * (60 + M1_S):
        print('  ✗ %s 焊盘高度 %d 太矮，塞不下两条 band' % (name, H))
        return None
    # S 组 wing/过孔/pad 走下半，D 组走上半
    band_h = 100
    gap = 40
    yb_s_lo = y_lo + 10
    yb_s_hi = yb_s_lo + band_h
    yb_d_hi = y_hi - 10
    yb_d_lo = yb_d_hi - band_h
    assert yb_d_lo - yb_s_hi >= gap, '两条 band 间距不足'
    vy_s = (yb_s_lo + yb_s_hi) // 2
    vy_d = (yb_d_lo + yb_d_hi) // 2
    VS = VIA1 + 8            # via1 实际画 60x60，留 0.04um 余量
    rh = VS + 40             # metal2 总线高 100

    L.append('# ---------------------------------------------------------------')
    L.append('#  %s  (%s)  nf=%d  islands=%d  pitch=%d' % (name, cell, len(sgrp) + len(dgrp) - 1, n, pit))
    L.append('#   instance offset = (%d, %d)   pad y = %d..%d' % (tx, ty, y_lo, y_hi))
    L.append('#   S-group islands %s' % (sgrp if len(sgrp) < 8 else '%s..%s' % (sgrp[:4], sgrp[-2:])))
    L.append('#   D-group islands %s' % (dgrp if len(dgrp) < 8 else '%s..%s' % (dgrp[:4], dgrp[-2:])))
    L.append('# ---------------------------------------------------------------')
    out_x = tx + pads[-1][0] + 207 + 30
    for tag, grp, vy, band_lo, band_hi in (
            ('S', sgrp, vy_s, yb_s_lo, yb_s_hi),
            ('D', dgrp, vy_d, yb_d_lo, yb_d_hi)):
        L.append('# -- %s %s group: %d islands' % (name, tag, len(grp)))
        for i in grp:
            cx, _, _, _, _ = pads[i]
            X = tx + cx
            w0 = X - 23
            w1 = w0 + WING
            L.append('box %d %d %d %d' % (w0, band_lo, w1, band_hi))
            L.append('paint metal1')
            v0 = w0 + (WING - VS) // 2
            L.append('box %d %d %d %d' % (v0, vy - VS // 2, v0 + VS, vy + VS // 2))
            L.append('paint via1')
        rx0 = tx + pads[0][0] - 23 - 20
        L.append('box %d %d %d %d' % (rx0, vy - rh // 2, out_x, vy + rh // 2))
        L.append('paint metal2')
        L.append('#      ^ %s_%s rail m2  y %d..%d' % (name, tag, vy - rh // 2, vy + rh // 2))
        L.append('')
    return L, {'name': name, 'S': vy_s, 'D': vy_d,
               'x0': tx + pads[0][0] - 43, 'x1': out_x, 'cell': cell}


def main():
    only = sys.argv[1:]
    tx_table = {
        'M5':   ('sky130_fd_pr__nfet_01v8_SND6KL',  1662,  957),
        'M6':   ('sky130_fd_pr__pfet_01v8_8MY6K8',  7140, 4766),
        'M7':   ('sky130_fd_pr__nfet_01v8_9A3M24',  7139, 2807),
        'Mref': ('sky130_fd_pr__nfet_01v8_RNGHDB',  4589, 1007),
    }
    bodies, meta = [], []
    for name, (cell, tx, ty) in tx_table.items():
        if only and name not in only:
            continue
        diffl, pads = islands_from_mag(cell)
        devs = parse_ext_devices(os.path.join(MAG, cell + '.ext'))
        print('== %-5s %-38s 岛=%2d  device=%2d  diffl=%s' %
              (name, cell, len(pads), len(devs), diffl))
        if len(devs) != len(pads) - 1:
            print('   ⚠ device 数 != 岛数-1，请检查')
        off, sgrp, dgrp = bipartition(devs, pads)
        print('   node->island 偏移 = %d   S组=%s' % (off, sgrp))
        print('   %s D组=%s' % (' ' * 3, dgrp))
        r = emit(name, cell, tx, ty, diffl, pads, sgrp, dgrp)
        if r:
            bl, info = r
            bodies += bl; meta.append(info)
        print()

    out = []
    out.append('# ========================================================================')
    out.append('#  bundle_top.tcl -- auto-generated by gen_bundle.py, do not hand-edit')
    out.append('#  Purpose: bundle the source/drain islands of the multi-finger devices')
    out.append('#           from the TOP level, using metal2 + via1.')
    out.append('#  It does NOT touch any geometry inside the device cells,')
    out.append('#  so the 0.05 um built-in gap inside those cells is never an issue.')
    out.append('#')
    out.append('#  Structure (one set per island):')
    out.append('#      [child m1 pad] ==(same-layer overlap)== [top m1 wing 1.15um wide]')
    out.append('#                                            --via1--> [top m2 rail]')
    out.append('#  The S rail runs low, the D rail runs high; the two m2 rails are at')
    out.append('#  completely different y, so they never short.')
    out.append('# ========================================================================')
    out.append('')
    out += bodies
    p = os.path.join(ROOT, 'bundle_top.tcl')
    open(p, 'w', encoding='ascii', newline='\n').write('\n'.join(out) + '\n')
    print('已写出 %s  (%d 行)' % (p, len(out)))
    print()
    print('=== 生成的总线一览（顶层坐标） ===')
    for m in meta:
        print('  %-5s S总线 y=%-6d  D总线 y=%-6d   x %d..%d' %
              (m['name'], m['S'], m['D'], m['x0'], m['x1']))


if __name__ == '__main__':
    main()
