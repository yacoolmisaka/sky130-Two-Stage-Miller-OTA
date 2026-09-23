#!/usr/bin/env python3
"""dump_layers.py -- 把 mag 文件按层段 dump 出来，支持 y 区间过滤"""
import re, os, sys
from collections import defaultdict

MAG = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mag')
SEC = re.compile(r'^<<\s*(\w+)\s*>>')
RECT = re.compile(r'^rect\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)\s*$')


def load(path):
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


def main():
    cell = sys.argv[1]
    p = os.path.join(MAG, cell + '.mag')
    lay = load(p)
    only = sys.argv[2] if len(sys.argv) > 2 else None        # 层名过滤
    ylo = int(sys.argv[3]) if len(sys.argv) > 3 else None
    yhi = int(sys.argv[4]) if len(sys.argv) > 4 else None

    print(f'== {cell}.mag ==')
    for name in sorted(lay):
        rects = lay[name]
        print(f'  {name:12s} n={len(rects)}')

    if only:
        print(f'\n---- {only} ----')
        rs = lay.get(only, [])
        if ylo is not None:
            sel = [r for r in rs if r[1] >= ylo and r[3] <= yhi]
            print(f'(过滤 y in [{ylo},{yhi}] -> {len(sel)}/{len(rs)})')
            rs = sel
        ys = sorted({r[1] for r in rs} | {r[3] for r in rs})
        print(f'  出现过的 y 边界: {ys[:40]}')
        for r in sorted(rs, key=lambda r: (r[0], r[1])):
            print(f'    x {r[0]:6d}..{r[2]:6d}   y {r[1]:6d}..{r[3]:6d}'
                  f'   cx={(r[0]+r[2])//2:6d} cy={(r[1]+r[3])//2:6d}'
                  f'   w={r[2]-r[0]:5d} h={r[3]-r[1]:5d}')


if __name__ == '__main__':
    main()
