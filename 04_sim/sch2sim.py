#!/usr/bin/env python3
"""sch2sim.py —— 把 xschem 导出的 sky130 原理图网表转成"可仿真版"。

为什么需要
----------
sky130 的器件 subckt 里：w = 总宽，nf = 指数，单指宽 = w / nf。
但本 PDK 的 BSIM4 模型对 w >= 10 会落进 bin 边界外，
ngspice 运行时算出负的 Pclm / Drout / Eta0，直接 fatal 退出。

而原理图为了和版图一一对应，w 必须写总宽（24 / 56 / 62.5 …）。
所以仿真前做一次电学等价的改写：

    w=4    nf=2    -->   w=2   nf=1 m=2
    w=24   nf=12   -->   w=2   nf=1 m=12
    w=56   nf=28   -->   w=2   nf=1 m=28
    w=62.5 nf=25   -->   w=2.5 nf=1 m=25
    w=12.5 nf=5    -->   w=2.5 nf=1 m=5

单指宽 = 总宽 / 指数，落在 2~2.5µm 的安全区；m= 保证总电流不变。

用法
----
    python3 sch2sim.py ota2_miller.spice
    # -> 生成 ota2_miller_sim.spice

    python3 sch2sim.py ota2_miller.spice -o /tmp/x.spice
"""
import argparse
import pathlib
import re

W_RE = re.compile(r'\bw=([0-9.eE+-]+)', re.I)
NF_RE = re.compile(r'\bnf=([0-9.eE+-]+)', re.I)
M_RE = re.compile(r'\bm=([0-9.eE+-]+)', re.I)


def clean_line(line):
    """只做结构清理，保留 w/nf 原始写法。

    剥掉两类 xschem 的「层次化标记」，否则网表无法被单独 include：

      * ``**.subckt`` / ``**.ends``
            xschem 给子电路声明加的前缀。ngspice 把 ``**`` 整行当注释，
            于是子电路根本没被定义，运行时报
            ``Error: unknown subckt: ...``。这里去掉前缀还原成真声明。

      * ``.end``
            被 ``.include`` 进来会让 ngspice 提前结束解析，
            后面所有器件都读不到。直接删掉。

    这一档输出的就是 **LVS 需要的形式**：版图提取出来的器件是总宽 / finger
    写法，必须拿同样写法的原理图网表去比，才能对上。
    """
    if line.startswith('**.'):
        line = line[2:]
    if line.strip() == '.end':
        return ''
    return line


def convert_line(line):
    """clean_line + 把 w/nf 拆成「单指宽 / nf=1」+ m=。仿真用。"""
    line = clean_line(line)
    if not line.strip() or 'sky130_fd_pr__' not in line:
        return line
    mw = W_RE.search(line)
    if not mw:
        return line

    mn = NF_RE.search(line)
    nf = float(mn.group(1)) if mn else 1.0
    if nf <= 1.0:
        return line

    w_finger = float(mw.group(1)) / nf
    mm = M_RE.search(line)
    mult = float(mm.group(1)) if mm else 1.0

    line = W_RE.sub('w=%g' % w_finger, line, count=1)
    line = NF_RE.sub('nf=1', line, count=1)
    m_new = mult * nf
    if M_RE.search(line):
        line = M_RE.sub('m=%g' % m_new, line, count=1)
    else:
        line = line.rstrip() + ' m=%g' % m_new
    return line


def main():
    ap = argparse.ArgumentParser(description='xschem 原理图网表 -> 可仿真网表')
    ap.add_argument('src', help='xschem 导出的 .spice 文件')
    ap.add_argument('-o', '--out', help='输出路径（默认 <src>_sim.spice）')
    ap.add_argument('--clean-only', action='store_true',
                    help='只做结构清理（去 ** 前缀 / 删 .end），不做 w/nf 拆分。'
                         ' LVS 用的原理图网表要用这一档')
    args = ap.parse_args()

    src = pathlib.Path(args.src)
    dst = pathlib.Path(args.out) if args.out else src.with_name('%s_sim%s' % (src.stem, src.suffix))

    n = 0
    out = []
    fn = clean_line if args.clean_only else convert_line
    for raw in src.read_text().splitlines():
        new = fn(raw)
        if new != raw:
            n += 1
        out.append(new)
    dst.write_text('\n'.join(out) + '\n')
    print('[sch2sim] 改写 %d 行 -> %s' % (n, dst))


if __name__ == '__main__':
    main()
