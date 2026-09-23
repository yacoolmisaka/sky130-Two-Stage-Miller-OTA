#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
阶跃响应绘制 —— 纯标准库, 输出 SVG
用法:  python3 plot_tran.py tran_step.txt [输出.svg]
输入格式(ngspice wrdata):  时间(s)  vout(V)  vinp(V)
"""
import sys
import math

W, H = 1000, 480
ML, MR, MT, MB = 78, 24, 30, 52

BG    = "#0f1115"
GRID  = "#242a34"
AXIS  = "#5b6472"
TXT   = "#e6e8ee"
C_OUT = "#58a6ff"
C_IN  = "#8b949e"


def read_data(path):
    rows = []
    with open(path, "r", errors="ignore") as f:
        for line in f:
            p = line.split()
            if len(p) < 3:
                continue
            try:
                rows.append((float(p[0]), float(p[1]), float(p[2])))
            except ValueError:
                continue
    rows.sort()
    return rows


def nice_ticks(lo, hi, n=6):
    span = hi - lo
    if span <= 0:
        return [lo]
    raw = span / n
    mag = 10 ** math.floor(math.log10(raw))
    for m in (1, 2, 2.5, 5, 10):
        if raw <= mag * m:
            step = mag * m
            break
    v = math.ceil(lo / step) * step
    out = []
    while v <= hi + 1e-9:
        out.append(v)
        v += step
    return out


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "tran_step.txt"
    dst = sys.argv[2] if len(sys.argv) > 2 else "tran.svg"
    rows = read_data(src)
    if len(rows) < 3:
        print("数据太少或格式不对:", src)
        sys.exit(1)

    ts = [r[0] for r in rows]
    vs = [r[1] for r in rows]
    vi = [r[2] for r in rows]
    t_lo, t_hi = min(ts), max(ts)
    v_lo = min(min(vs), min(vi))
    v_hi = max(max(vs), max(vi))
    pad = (v_hi - v_lo) * 0.12
    v_lo -= pad; v_hi += pad

    # 时间统一按 ns 显示
    tsc = 1e9
    tunit = "ns"

    def sx(t): return ML + (t - t_lo) / (t_hi - t_lo) * (W - ML - MR)
    def sy(v): return MT + (v_hi - v) / (v_hi - v_lo) * (H - MT - MB)

    o = []
    a = o.append
    a(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
      f'viewBox="0 0 {W} {H}" font-family="Consolas,Menlo,monospace">')
    a(f'<rect width="{W}" height="{H}" fill="{BG}"/>')

    for t in nice_ticks(t_lo * tsc, t_hi * tsc):
        x = sx(t / tsc)
        a(f'<line x1="{x:.1f}" y1="{MT}" x2="{x:.1f}" y2="{H-MB}" stroke="{GRID}"/>')
        a(f'<text x="{x:.1f}" y="{H-MB+20}" fill="{TXT}" font-size="12" '
          f'text-anchor="middle">{t:g}</text>')
    for v in nice_ticks(v_lo, v_hi):
        y = sy(v)
        a(f'<line x1="{ML}" y1="{y:.1f}" x2="{W-MR}" y2="{y:.1f}" stroke="{GRID}"/>')
        a(f'<text x="{ML-8}" y="{y+4:.1f}" fill="{TXT}" font-size="12" text-anchor="end">{v:g}</text>')
    a(f'<rect x="{ML}" y="{MT}" width="{W-ML-MR}" height="{H-MT-MB}" fill="none" stroke="{AXIS}"/>')

    step = max(1, len(rows) // 2000)
    pi = " ".join(f"{sx(t):.1f},{sy(v):.1f}" for t, _, v in rows[::step])
    po = " ".join(f"{sx(t):.1f},{sy(v):.1f}" for t, v, _ in rows[::step])
    a(f'<polyline points="{pi}" fill="none" stroke="{C_IN}" stroke-width="1.6" '
      f'stroke-dasharray="5 4"/>')
    a(f'<polyline points="{po}" fill="none" stroke="{C_OUT}" stroke-width="2.2"/>')

    a(f'<text x="{ML}" y="{MT-10}" fill="{C_OUT}" font-size="15">vout</text>')
    a(f'<text x="{ML+70}" y="{MT-10}" fill="{C_IN}" font-size="15">--- vin (输入阶跃)</text>')
    a(f'<text x="{W//2}" y="{H-8}" fill="{TXT}" font-size="13" text-anchor="middle">时间 ({tunit})</text>')
    a(f'<text x="16" y="{H//2}" fill="{TXT}" font-size="13" '
      f'transform="rotate(-90 16 {H//2})" text-anchor="middle">电压 (V)</text>')

    # 过冲检测
    vfin = vs[-1]
    vmax = max(vs)
    ov = (vmax - vfin) / (vfin - vs[0]) * 100 if abs(vfin - vs[0]) > 1e-6 else 0
    a(f'<text x="{ML+10}" y="{MT+20}" fill="{TXT}" font-size="13">'
      f'过冲 = {ov:.2f} %   (过冲大 -> 相位裕度不足, 要加大 Cc 或 gm6)</text>')

    a('</svg>')
    with open(dst, "w", encoding="utf-8") as f:
        f.write("\n".join(o))
    print("已生成:", dst)
    print(f"  过冲 = {ov:.2f} %")


if __name__ == "__main__":
    main()
