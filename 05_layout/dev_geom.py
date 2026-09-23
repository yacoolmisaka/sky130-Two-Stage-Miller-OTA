#!/usr/bin/env python3
"""
dev_geom.py -- 解析 gencell 生成的 sky130 器件 .mag，量出「源漏岛焊盘」的
               真实可接入几何，并判断能否打 via1 / 走 metal1。

为什么需要它（背景见 M5-M7多指管LVS阻塞根因终局报告.md）：
  sky130.tcl 生成的器件 (conn_gates=0, doverlap=1) 内部不做 stitching：
    - 多指器件的源漏共 nf+1 个岛，交替 D,S,D,S...，顶层必须捆扎才能并联
    - 但每个岛的 m1 只包了 0.03um，总宽 0.23um
    - 而 via1 需要 m1 >= 0.31um (0.19 + 2*0.06)
  => 必须先从 .mag 里把尺寸量出来，才知道能不能接、怎么接。

用法:
  python3 05_layout/dev_geom.py                 # 量 ota2_miller 里 10 个实例
  python3 05_layout/dev_geom.py M5 M6           # 只量指定实例
  python3 05_layout/dev_geom.py --exp           # 量 expE*.mag 实验组
  python3 05_layout/dev_geom.py --cells expE0 expE1   # 量指定 cell
"""
import os
import re
import sys
import glob

U = 0.005          # 1 magic internal unit = 5 nm (sky130, lambda=0.005um)

# ota2_miller.mag 里的实例放置 transform (1 0 TX 0 1 TY)
INSTANCES = {
    'Cc':   ('sky130_fd_pr__cap_mim_m3_1_PMLRN3',        14916, 3470),
    'M1':   ('sky130_fd_pr__nfet_01v8_7KZ2AN',             372, 2757),
    'M2':   ('sky130_fd_pr__nfet_01v8_7KZ2AN',            1622, 2757),
    'M3':   ('sky130_fd_pr__pfet_01v8_8FHKLD',             372, 4166),
    'M4':   ('sky130_fd_pr__pfet_01v8_8FHKLD',            1622, 4166),
    'M5':   ('sky130_fd_pr__nfet_01v8_SND6KL',            1662,  957),
    'M6':   ('sky130_fd_pr__pfet_01v8_8MY6K8',            7140, 4766),
    'M7':   ('sky130_fd_pr__nfet_01v8_9A3M24',            7139, 2807),
    'Mref': ('sky130_fd_pr__nfet_01v8_RNGHDB',            4589, 1007),
    'Rz':   ('sky130_fd_pr__res_xhigh_po_0p69_96AYDP',   11582, 1649),
}

# via1 的 DRC 约束（sky130）
VIA1_SIZE   = 0.19     # um，via1 方形边长
M1_SURROUND = 0.06     # um，m1 对 via1 的包围（每边）
M1_MIN_SPACE = 0.14    # um，m1 最小间距
MIN_PAD_FOR_VIA1 = VIA1_SIZE + 2 * M1_SURROUND   # 0.31 um

HERE = os.path.dirname(os.path.abspath(__file__))
MAGDIR = os.path.join(HERE, 'mag')

RECT = re.compile(r'^rect\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)\s*$')
SEC = re.compile(r'^<<\s*(\w+)\s*>>')


def parse_mag(path):
    """返回 (layers, params, bbox)；layers = {layer: [(x0,y0,x1,y1), ...]}"""
    layers, cur = {}, None
    params, bbox = {}, None
    with open(path, encoding='utf-8', errors='replace') as fh:
        for line in fh:
            line = line.strip()
            m = SEC.match(line)
            if m:
                cur = m.group(1)
                layers.setdefault(cur, [])
                continue
            m = RECT.match(line)
            if m and cur:
                x0, y0, x1, y1 = map(int, m.groups())
                layers[cur].append((min(x0, x1), min(y0, y1),
                                    max(x0, x1), max(y0, y1)))
                continue
            if line.startswith('string parameters'):
                toks = line.split()[2:]
                for i in range(0, len(toks) - 1, 2):
                    params[toks[i]] = toks[i + 1]
            elif line.startswith('string FIXED_BBOX'):
                bbox = tuple(map(int, line.split()[2:6]))
    return layers, params, bbox


def _cluster_by_x(rects, tol=2):
    """
    按 x0 把矩形聚成「列」，每列取 x/y 的外接矩形。
    magic 里同一个焊盘常被拆成多条矩形（框的 4 条边），必须先聚回整体。
    """
    cols = {}
    for r in sorted(rects):
        key = None
        for k in cols:
            if abs(k - r[0]) <= tol:
                key = k
                break
        if key is None:
            cols[r[0]] = list(r)
        else:
            o = cols[key]
            cols[key] = [min(o[0], r[0]), min(o[1], r[1]),
                         max(o[2], r[2]), max(o[3], r[3])]
    return [tuple(cols[k]) for k in sorted(cols)]


def find_islands(layers):
    """
    提取源漏岛焊盘。
    magic 把岛的 m1 画成「框」= 左右竖条 + 上下封口（4 条矩形），
    所以先按 x 聚类还原整体，再按尺寸判据筛选。

    判据（聚类后）：
        x 宽 35~75 单位 (0.175~0.375 um)   <- 岛焊盘宽度
        y 高 >= 200 单位 (>= 1.0 um)      <- 岛焊盘高度（典型 2.0 um）

    doverlap=1 时相邻指的岛共享 -> nf 指得 nf+1 个岛。
    """
    return [r for r in _cluster_by_x(layers.get('metal1', []))
            if 35 <= r[2] - r[0] <= 75 and r[3] - r[1] >= 200]


def find_viali(layers):
    """
    li->m1 接触孔（长条）。
    聚类后 x 宽 30~40 单位 = 0.17 um（sky130 接触孔最小尺寸）。
    """
    return [r for r in _cluster_by_x(layers.get('viali', []))
            if 28 <= r[2] - r[0] <= 45 and r[3] - r[1] >= 150]


def find_gate_pads(layers):
    """
    栅极 m1 焊盘。

    每个指的栅极焊盘在 cell 里是【上下两段】，每段由 2 条窄横条组成
    （draw_contact 的 metal_surround 环，上下各一条 6 单位高）。

    这里用 y 坐标把矩形分成 top / bot 两组，再各自按 x0 聚类成整段。
    返回 (top, bot)，元素为 (x0, y_lo, x1, y_hi)。
    """
    boxes = [r for r in layers.get('metal1', [])
             if r[2] - r[0] >= 150 and r[3] - r[1] <= 40]
    if not boxes:
        return [], []
    ys = [r[1] for r in boxes] + [r[3] for r in boxes]
    mid = (min(ys) + max(ys)) / 2.0
    top_raw = [r for r in boxes if (r[1] + r[3]) / 2.0 >= mid]
    bot_raw = [r for r in boxes if (r[1] + r[3]) / 2.0 < mid]

    def merge(rs):
        """同一 x 位置的上下两条窄横条合并成一段"""
        if not rs:
            return []
        out = {}
        for r in sorted(rs):
            found = None
            for k in out:
                if abs(k - r[0]) <= 2:
                    found = k
                    break
            if found is None:
                out[r[0]] = list(r)
            else:
                o = out[found]
                out[found] = [min(o[0], r[0]), min(o[1], r[1]),
                              max(o[2], r[2]), max(o[3], r[3])]
        return [tuple(out[k]) for k in sorted(out)]

    return merge(top_raw), merge(bot_raw)


def analyse(path, label=None, tx=0, ty=0):
    """量一个 cell，打印报告。tx/ty = 换算到顶层坐标的平移量。"""
    label = label or os.path.basename(path)[:-4]
    layers, params, bbox = parse_mag(path)

    isl = find_islands(layers)
    via = find_viali(layers)
    gtop, gbot = find_gate_pads(layers)

    try:
        w = float(params.get('w', 0))
        nf = int(params.get('nf', 0))
    except ValueError:
        w, nf = 0, 0

    print(f'\n{"=" * 80}')
    print(f'  {label}')
    print(f'  file   : {os.path.basename(path)}')
    print(f'  w={w} l={params.get("l", "?")} nf={nf}   '
          f'(单指宽 = {w / nf if nf else 0:.3f} um)')
    print(f'  bbox   : {bbox}')
    if tx or ty:
        print(f'  顶层偏移: ({tx}, {ty})')
    print(f'{"=" * 80}')

    # ---- 源漏岛 ----
    print(f'\n  [源漏岛] 共 {len(isl)} 个  (理论 {nf + 1 if nf else "?"})')
    if not isl:
        print('     !! 没找到岛 —— 判据需要调整，或该 cell 不是 MOS')
    else:
        mw = isl[0][2] - isl[0][0]
        print(f'     岛宽(m1外接) = {mw} 单位 = {mw * U:.3f} um')
        print(f'     岛高         = {isl[0][3] - isl[0][1]} 单位 '
              f'= {(isl[0][3] - isl[0][1]) * U:.3f} um')
        if len(isl) > 1:
            dx = isl[1][0] - isl[0][0]
            print(f'     指间距 dx    = {dx} 单位 = {dx * U:.3f} um')
            print(f'     相邻岛间隙   = {(dx - mw) * U:.3f} um')
        print(f'     岛中心 x     : {[ (r[0]+r[2])//2 + tx for r in isl ]}')
        # 判定
        print()
        print(f'     >>> via1 判定: 需要 m1 >= {MIN_PAD_FOR_VIA1:.3f} um '
              f'({VIA1_SIZE} + 2*{M1_SURROUND})')
        if mw * U >= MIN_PAD_FOR_VIA1:
            print(f'         ✔ 岛宽 {mw * U:.3f} um >= {MIN_PAD_FOR_VIA1:.3f} '
                  f'—— 可以打 via1！')
        else:
            print(f'         ✗ 岛宽 {mw * U:.3f} um < {MIN_PAD_FOR_VIA1:.3f} '
                  f'—— 打不下 via1（差 {MIN_PAD_FOR_VIA1 - mw * U:.3f} um）')

    # ---- viali 接触孔 ----
    if via:
        vw = via[0][2] - via[0][0]
        print(f'\n  [viali li->m1 接触孔] {len(via)} 条')
        print(f'     接触孔宽 = {vw} 单位 = {vw * U:.3f} um')
        surround = (isl[0][2] - isl[0][0] - vw) / 2 if isl else 0
        print(f'     m1 包围  = {surround:.0f} 单位 = {surround * U:.3f} um')

    # ---- 栅极焊盘 ----
    print(f'\n  [栅极焊盘] 顶排 {len(gtop)} 段 / 底排 {len(gbot)} 段'
          f'  (理论各 {nf} 段)')
    for nm, grp in (('顶排', gtop), ('底排', gbot)):
        if not grp:
            continue
        gw = grp[0][2] - grp[0][0]
        gy0 = min(r[1] for r in grp) + ty
        gy1 = max(r[3] for r in grp) + ty
        print(f'     {nm}: 每段宽 {gw} 单位 = {gw * U:.3f} um, '
              f'顶层 y = {gy0} .. {gy1}')
        if len(grp) > 1:
            gdx = grp[1][0] - grp[0][0]
            print(f'          段间距 {gdx} 单位 = {gdx * U:.3f} um, '
                  f'段间空隙 {(gdx - gw) * U:.3f} um')

    # ---- 关键走廊：岛顶 <-> 栅极底 的垂直间隙 ----
    if isl and gtop:
        iy1 = max(r[3] for r in isl) + ty
        gy0 = min(r[1] for r in gtop) + ty
        gap = (gy0 - iy1) * U
        print(f'\n  [走廊 · 岛顶->栅极顶排] 间隙 {gap:.3f} um  '
              f'{"✔ 够" if gap >= M1_MIN_SPACE else "✗ 不够走 m1 (需 >= 0.14)"}')
    if isl and gbot:
        iy0 = min(r[1] for r in isl) + ty
        gy1 = max(r[3] for r in gbot) + ty
        gap = (iy0 - gy1) * U
        print(f'  [走廊 · 栅极底排->岛底] 间隙 {gap:.3f} um  '
              f'{"✔ 够" if gap >= M1_MIN_SPACE else "✗ 不够走 m1 (需 >= 0.14)"}')

    # ---- 水平间隙：岛 <-> 最近栅极段 ----
    if isl and gtop:
        ix1 = isl[0][2] + tx
        gx0 = gtop[0][0] + tx
        gap = (gx0 - ix1) * U
        print(f'  [间隙 · 岛右->栅极段左] {gap:.3f} um  '
              f'{"✔" if gap >= M1_MIN_SPACE else "✗ 无法向右扩展 m1"}')

    return {
        'label': label, 'isl': isl, 'n_isl': len(isl),
        'pad_w_um': (isl[0][2] - isl[0][0]) * U if isl else 0,
        'via_ok': bool(isl and (isl[0][2] - isl[0][0]) * U >= MIN_PAD_FOR_VIA1),
        'w': w, 'nf': nf,
    }


def main():
    args = sys.argv[1:]

    print(f'\n{"#" * 80}')
    print(f'#  sky130 gencell 器件几何量测')
    print(f'#  1 内部单位 = {U} um   (magscale 不影响此换算)')
    print(f'#  via1 判定阈值: m1 >= {MIN_PAD_FOR_VIA1:.3f} um'
          f'  (via1 {VIA1_SIZE} + 2*包围 {M1_SURROUND})')
    print(f'{"#" * 80}')

    results = []

    if '--exp' in args:
        # 量实验组
        for p in sorted(glob.glob(os.path.join(MAGDIR, 'expE*.mag'))):
            results.append(analyse(p))
    elif '--cells' in args:
        idx = args.index('--cells')
        for nm in args[idx + 1:]:
            p = os.path.join(MAGDIR, nm + '.mag')
            if os.path.exists(p):
                results.append(analyse(p))
            else:
                print(f'\n  !! 找不到 {p}')
    else:
        want = [a for a in args if not a.startswith('-')] or list(INSTANCES)
        for inst in want:
            if inst not in INSTANCES:
                print(f'  跳过未知实例 {inst}')
                continue
            cell, tx, ty = INSTANCES[inst]
            p = os.path.join(MAGDIR, cell + '.mag')
            if not os.path.exists(p):
                print(f'\n  !! 找不到 {p}')
                continue
            results.append(analyse(p, label=f'{inst} ({cell})', tx=tx, ty=ty))

    # ---- 汇总 ----
    if results:
        print(f'\n{"#" * 80}')
        print(f'#  汇总')
        print(f'{"#" * 80}')
        print(f'  {"器件":<12s} {"岛数":>4s} {"岛宽(um)":>10s}  '
              f'{"via1":>6s}   单指宽')
        print(f'  {"-" * 58}')
        for r in results:
            mark = '✔ 可打' if r['via_ok'] else '✗ 打不下'
            print(f'  {r["label"][:12]:<12s} {r["n_isl"]:>4d} '
                  f'{r["pad_w_um"]:>10.3f}  {mark:>6s}   '
                  f'{r["w"]}/{r["nf"] if r["nf"] else "?"}'
                  f' = {r["w"] / r["nf"]:.2f}' if r['nf'] else '')
        print()
        ok = [r for r in results if r['via_ok']]
        if ok:
            print(f'  ★ 可以作为顶层接入参考的 cell:')
            for r in ok:
                print(f'      {r["label"]}  (岛宽 {r["pad_w_um"]:.3f} um)')
        else:
            print(f'  ⚠ 没有任何 cell 的岛宽达到 {MIN_PAD_FOR_VIA1:.3f} um')
            print(f'    -> 需要继续加大 gate_to_diffcont / contact_size')
        print()


if __name__ == '__main__':
    main()
