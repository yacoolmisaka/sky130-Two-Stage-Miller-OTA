#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_conn.py  --  LVS 前置连通性核对器（纯离线，不需要 magic / netgen）

【为什么需要它】
  netgen 失败时只会甩一句 "Netlists do not match"，看不到是哪根线没接。
  真正要看的是：**版图网表里每颗管子的每个端子上挂的是哪张网**。
  本脚本把 ext2spice 出来的 ota2_miller.spice 逐管逐端子拆开，分成三段报：

    ① 顶层实例分组表   —— 每颗管的 栅/源漏/衬底 各自挂在哪张网上
    ② 悬浮网络清单     —— magic 自动命名(<层>_x_y#) = 没 label 的孤立金属 = 断点
    ③ 器件内部断点     —— 子电路内部只被一个器件用到、又没引出来的节点

【怎么判断端子类型】
  不靠猜端口名后缀，直接读子电路内部的器件行：
  spice 语法  X<名> D G S B <模型>  → 第 2 token 是栅，第 3/4 是源漏。
  阻/容是两端器件，单独归类。

用法：
    python check_conn.py                       # 读 mag/ota2_miller.spice
    python check_conn.py <netlist.spice>
"""

import os
import re
import sys
from collections import OrderedDict, defaultdict

U = 0.005                                   # 1 magic internal unit = 5 nm
AUTO = re.compile(r'^([a-z0-9]+)_(-?\d+)_(-?\d+)#$')   # magic 自动命名
SKIP = {'VSUBS', 'VDD', 'GND'}              # 衬底/电源总线，不算断点
TWO_TERM = ('cap_', 'res_')                 # 两端器件关键字


# --------------------------------------------------------------------------
# 1. 解析 spice（必须处理行首 '+' 续行，否则 26 端口的子电路会错位）
# --------------------------------------------------------------------------
def read_subckts(path):
    if not os.path.exists(path):
        sys.exit(f'!! 找不到网表：{path}\n'
                 f'   先在 magic 里跑 extract all / ext2spice lvs / ext2spice，\n'
                 f'   或显式指定路径： python3 check_conn.py 05_layout/mag/ota2_miller.spice')
    subs = OrderedDict()
    cur = buf = None
    last = None
    with open(path, errors='replace') as fp:
        for raw in fp:
            s = raw.strip()
            if not s or s.startswith('*'):
                continue
            if s.startswith('+'):
                if last == 'head':
                    subs[cur]['ports'].extend(s[1:].split())
                elif last == 'body' and buf:
                    buf[-1] += ' ' + s[1:].strip()
                continue
            if s.startswith('.subckt'):
                tk = s.split()
                cur = tk[1]
                buf = []
                subs[cur] = {'ports': tk[2:], 'body': buf}
                last = 'head'
                continue
            if s.startswith('.ends'):
                cur, last = None, None
                continue
            if cur is None:
                continue
            buf.append(s)
            last = 'body'
    return subs


def group_ports(cell, child):
    """→ [(组名, {该组的端口名}), ...]，顺序与端口表一致。"""
    if any(k in cell for k in TWO_TERM):                    # 电阻 / 电容
        return [('端子 T', list(child['ports']))]
    gate, sd, bulk, order = set(), set(), set(), []
    for line in child['body']:
        tk = line.split()
        if len(tk) < 5 or not tk[0].startswith('X'):
            continue
        _, d, g, s, b = tk[0], tk[1], tk[2], tk[3], tk[4]
        sd.update(n for n in (d, s) if n in child['ports'])
        if g in child['ports']:
            gate.add(g)
        if b in child['ports']:
            bulk.add(b)
    return [('栅 G  ', gate), ('源漏S/D', sd), ('衬底 B ', bulk)]


def is_auto(n):
    return bool(AUTO.match(n))


def pos_of(n):
    m = AUTO.match(n)
    return (int(m.group(2)), int(m.group(3))) if m else None


# --------------------------------------------------------------------------
# 2. 主报告
# --------------------------------------------------------------------------
def report(path):
    subs = read_subckts(path)
    if 'ota2_miller' not in subs:
        sys.exit(f'!! {path} 里没有 .subckt ota2_miller')
    top = subs['ota2_miller']

    insts = []
    for line in top['body']:
        tk = line.split()
        if len(tk) >= 3 and tk[0].startswith('X'):
            insts.append((tk[0], tk[-1], tk[1:-1]))

    floating = defaultdict(list)                 # 自动命名网络 -> [(实例, 序号)]
    for inst, cell, nets in insts:
        for i, n in enumerate(nets):
            if is_auto(n):
                floating[n].append((inst, i))

    hdr = '=' * 82
    print(hdr)
    print(f' 连通性核对   {os.path.basename(path)}')
    print(hdr)
    print(f' 顶层端口 {len(top["ports"])} 个 : {" ".join(top["ports"])}')
    print(f' 顶层实例 {len(insts)} 个 ；真·悬浮网络 {len(floating)} 个')
    print()

    # ---------------- ① 逐器件分组表 ----------------
    print('-' * 82)
    print(' ① 逐器件端子归属')
    print('-' * 82)
    for inst, cell, nets in insts:
        child = subs.get(cell)
        short = cell.replace('sky130_fd_pr__', '')
        if child is None:
            print(f'\n  {inst:<6s} {short}   (无内部定义)')
            continue
        bad = sum(1 for n in nets if is_auto(n))
        tag = f'  ★ {bad} 个悬浮' if bad else '  ✔ 全通'
        print(f'\n  {inst:<6s} = {short:<30s}{tag}')
        for label, members in group_ports(cell, child):
            if isinstance(members, list):            # 两端器件
                row = [f'{"!!" if is_auto(n) else "  "}{n}' for n in members]
            else:
                row = [f'{"!!" if is_auto(n) else "  "}{nets[i]}'
                       for i, p in enumerate(child['ports']) if p in members]
            if row:
                print(f'      {label}  ' + '   '.join(row))

    # ---------------- ② 悬浮网络清单 ----------------
    print()
    print('-' * 82)
    print(f' ② 悬浮网络清单（{len(floating)} 个）← 这些是必须补的断点')
    print('-' * 82)
    rows = []
    for n, users in floating.items():
        p = pos_of(n) or (0, 0)
        rows.append((p[1], p[0], n, sorted({u for u, _ in users}), len(users)))
    rows.sort()
    if not rows:
        print('     （没有悬浮网络，连通性完整）')
    for y, x, n, devs, cnt in rows:
        where = f'({x*U:6.2f},{y*U:6.2f})um' if (x or y) else '  -- 无坐标 -- '
        print(f'     {where}  {n:<20s} ×{cnt:<3d} {", ".join(devs[:8])}'
              + (' …' if len(devs) > 8 else ''))

    # ---------------- ③ 器件内部断点 ----------------
    print()
    print('-' * 82)
    print(' ③ 器件内部断点（子电路里只被 1 处用到、又没做成端口的节点）')
    print('-' * 82)
    found = False
    for name, ch in subs.items():
        if name == 'ota2_miller':
            continue
        use = defaultdict(int)
        for line in ch['body']:
            tk = line.split()
            if len(tk) < 5 or not tk[0].startswith('X'):
                continue
            for n in (tk[1], tk[3], tk[4]):
                if n not in ch['ports']:
                    use[n] += 1
        dead = [n for n, c in use.items() if c <= 1]
        if dead:
            found = True
            print(f'     {name.replace("sky130_fd_pr__", ""):<30s} → {dead}')
    if not found:
        print('     （无）')

    # ---------------- ④ 器件内部"死节点" ----------------
    #  magic 层次化提取：子 cell 的 .ext 里列的是它【全部】内部节点；
    #  而 .spice 里 .subckt 的端口表 = 【顶层真正碰得到】的那些节点。
    #  两者之差 = 顶层根本连不进去的节点。这些节点在网表里直接消失，
    #  netgen 连看都看不到 —— 但实物上就是断的。
    print()
    print('-' * 82)
    print(' ④ 器件内部死节点（.ext 有、.spice 端口表里没有 → 顶层永远接不上）')
    print('-' * 82)
    ext_dir = os.path.join(os.path.dirname(os.path.abspath(path)))
    total = 0
    for cell, ch in subs.items():
        if cell == 'ota2_miller':
            continue
        fp = os.path.join(ext_dir, cell + '.ext')
        if not os.path.exists(fp):
            continue
        nodes = []
        for line in open(fp, errors='replace'):
            if line.startswith('node '):
                nodes.append(line.split()[1].strip('"'))
        dead = len(nodes) - len(ch['ports'])
        total += max(dead, 0)
        n_sd = sum(1 for n in nodes if re.search(r'_n(200|250)#$', n))
        n_g = sum(1 for n in nodes if re.search(r'_n(288|297|338)#$', n))
        n_b = len(nodes) - n_sd - n_g
        verdict = '★ 有死节点' if dead > 0 else '✔ 全通'
        print(f'     {cell.replace("sky130_fd_pr__", ""):<30s}'
              f'内部 {len(nodes):>3d} (源漏{n_sd}/栅{n_g}/其它{n_b})  '
              f'顶层可见 {len(ch["ports"]):>3d}  差 {dead:>3d}   {verdict}')
    print(f'\n     合计死节点 {total} 个')
    print()
    return floating


if __name__ == '__main__':
    p = (sys.argv[1] if len(sys.argv) > 1 else
         os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mag', 'ota2_miller.spice'))
    report(p)
