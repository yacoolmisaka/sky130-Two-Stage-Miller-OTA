#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
波特图绘制 —— 纯标准库, 输出 SVG (不需要 matplotlib)
用法:  python3 plot_bode.py ac_bode.txt [输出.svg]
输入格式(ngspice wrdata):  频率(Hz)  增益(dB)  相位(deg)
"""
import sys
import math

W, H = 1000, 640
ML, MR, MT, MB = 78, 24, 26, 52          # 边距
GAP = 60                                  # 上下两图间距
PH = (H - MT - MB - GAP) // 2             # 每个子图高度

BG     = "#0f1115"
GRID   = "#242a34"
AXIS   = "#5b6472"
TXT    = "#e6e8ee"
C_GAIN = "#58a6ff"
C_PHSE = "#ff7b72"
C_MARK = "#3fb950"


def read_data(path):
    rows = []
    with open(path, "r", errors="ignore") as f:
        for line in f:
            p = line.split()
            if len(p) < 3:
                continue
            try:
                # ngspice wrdata 对每个向量写 "x y" (复数向量则 "x re im")。
                # 本项目 wrdata freqv gain_db phase_deg, freqv 是复数,
                # 实测每行 7 列: [0]freq [1]freqv [2]im [3]freq [4]gain [5]freq [6]phase
                if len(p) >= 7:
                    freq, gain, phase = float(p[0]), float(p[4]), float(p[6])
                elif len(p) == 6:
                    freq, gain, phase = float(p[0]), float(p[1]), float(p[3])
                else:
                    freq, gain, phase = float(p[0]), float(p[1]), float(p[2])
                # vp()/wrdata 输出【弧度】(实测低频 = π), 转成度
                if abs(phase) < 4.0:
                    phase = math.degrees(phase)
                rows.append((freq, gain, phase))
            except ValueError:
                continue
    rows = [r for r in rows if r[0] > 0]
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
    start = math.ceil(lo / step) * step
    out = []
    v = start
    while v <= hi + 1e-9:
        out.append(v)
        v += step
    return out


def fmt_freq(f):
    if f >= 1e9:  return f"{f/1e9:g}G"
    if f >= 1e6:  return f"{f/1e6:g}M"
    if f >= 1e3:  return f"{f/1e3:g}k"
    return f"{f:g}"


def crossing(rows, level):
    """找增益曲线穿过 level(dB) 的频率 (线性插值, 取第一次下降穿越)"""
    for i in range(1, len(rows)):
        f0, g0, _ = rows[i-1]
        f1, g1, _ = rows[i]
        if g0 >= level > g1:
            t = (g0 - level) / (g0 - g1) if g0 != g1 else 0
            return f0 * (f1 / f0) ** t     # 频率轴是对数, 用几何插值
    return None


def phase_at(rows, f):
    for i in range(1, len(rows)):
        if rows[i-1][0] <= f <= rows[i][0]:
            f0, _, p0 = rows[i-1]
            f1, _, p1 = rows[i]
            if f1 == f0:
                return p0
            return p0 + (p1 - p0) * (math.log(f/f0) / math.log(f1/f0))
    return None


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "ac_bode.txt"
    dst = sys.argv[2] if len(sys.argv) > 2 else "bode.svg"
    rows = read_data(src)
    if len(rows) < 3:
        print("数据太少或格式不对:", src)
        sys.exit(1)

    freqs = [r[0] for r in rows]
    gains = [r[1] for r in rows]
    phses = [r[2] for r in rows]

    f_lo, f_hi = min(freqs), max(freqs)
    lg_lo, lg_hi = math.log10(f_lo), math.log10(f_hi)
    g_lo, g_hi = min(gains), max(gains)
    g_hi += (g_hi - g_lo) * 0.08
    p_lo, p_hi = min(phses), max(phses)
    p_lo -= 8; p_hi += 8

    def sx(f):
        return ML + (math.log10(f) - lg_lo) / (lg_hi - lg_lo) * (W - ML - MR)

    def sy_g(db):
        return MT + (g_hi - db) / (g_hi - g_lo) * PH

    def sy_p(d):
        return MT + PH + GAP + (p_hi - d) / (p_hi - p_lo) * PH

    o = []
    a = o.append
    a(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
      f'viewBox="0 0 {W} {H}" font-family="Consolas,Menlo,monospace">')
    a(f'<rect width="{W}" height="{H}" fill="{BG}"/>')

    # ---------- 网格 + 轴 ----------
    decs = list(range(int(math.floor(lg_lo)), int(math.ceil(lg_hi)) + 1))
    for d in decs:
        for m in range(1, 10):
            f = m * 10 ** d
            if f_lo <= f <= f_hi:
                x = sx(f)
                col = GRID if m != 1 else AXIS
                a(f'<line x1="{x:.1f}" y1="{MT}" x2="{x:.1f}" '
                  f'y2="{MT+PH}" stroke="{col}" stroke-width="1"/>')
                a(f'<line x1="{x:.1f}" y1="{MT+PH+GAP}" x2="{x:.1f}" '
                  f'y2="{MT+2*PH+GAP}" stroke="{col}" stroke-width="1"/>')
    for d in decs:
        f = 10 ** d
        if f_lo <= f <= f_hi:
            a(f'<text x="{sx(f):.1f}" y="{H-MB+20}" fill="{TXT}" font-size="13" '
              f'text-anchor="middle">{fmt_freq(f)}</text>')

    for t in nice_ticks(g_lo, g_hi):
        y = sy_g(t)
        a(f'<line x1="{ML}" y1="{y:.1f}" x2="{W-MR}" y2="{y:.1f}" stroke="{GRID}" stroke-width="1"/>')
        a(f'<text x="{ML-8}" y="{y+4:.1f}" fill="{TXT}" font-size="12" text-anchor="end">{t:g}</text>')
    # 0dB 线
    if g_lo < 0 < g_hi:
        y0 = sy_g(0)
        a(f'<line x1="{ML}" y1="{y0:.1f}" x2="{W-MR}" y2="{y0:.1f}" '
          f'stroke="{AXIS}" stroke-width="1.4" stroke-dasharray="6 4"/>')
        a(f'<text x="{W-MR-4}" y="{y0-6:.1f}" fill="{AXIS}" font-size="12" text-anchor="end">0 dB</text>')

    for t in nice_ticks(p_lo, p_hi):
        y = sy_p(t)
        a(f'<line x1="{ML}" y1="{y:.1f}" x2="{W-MR}" y2="{y:.1f}" stroke="{GRID}" stroke-width="1"/>')
        a(f'<text x="{ML-8}" y="{y+4:.1f}" fill="{TXT}" font-size="12" text-anchor="end">{t:g}</text>')

    # 边框
    a(f'<rect x="{ML}" y="{MT}" width="{W-ML-MR}" height="{PH}" fill="none" stroke="{AXIS}"/>')
    a(f'<rect x="{ML}" y="{MT+PH+GAP}" width="{W-ML-MR}" height="{PH}" fill="none" stroke="{AXIS}"/>')

    # ---------- 曲线 ----------
    pg = " ".join(f"{sx(f):.1f},{sy_g(g):.1f}" for f, g, _ in rows)
    pp = " ".join(f"{sx(f):.1f},{sy_p(p):.1f}" for f, _, p in rows)
    a(f'<polyline points="{pg}" fill="none" stroke="{C_GAIN}" stroke-width="2.2"/>')
    a(f'<polyline points="{pp}" fill="none" stroke="{C_PHSE}" stroke-width="2.2"/>')

    # 标题
    a(f'<text x="{ML}" y="{MT-8}" fill="{C_GAIN}" font-size="15">'
      f'开环增益 (dB)</text>')
    a(f'<text x="{ML}" y="{MT+PH+GAP-8}" fill="{C_PHSE}" font-size="15">'
      f'相位 (deg)</text>')
    a(f'<text x="{W//2}" y="{H-8}" fill="{TXT}" font-size="13" text-anchor="middle">'
      f'频率 (Hz)</text>')

    # ---------- 关键点标注 ----------
    gbw = crossing(rows, 0.0)
    info = []
    if gbw:
        x = sx(gbw)
        a(f'<line x1="{x:.1f}" y1="{MT}" x2="{x:.1f}" y2="{MT+PH}" '
          f'stroke="{C_MARK}" stroke-width="1.2" stroke-dasharray="4 3"/>')
        a(f'<line x1="{x:.1f}" y1="{MT+PH+GAP}" x2="{x:.1f}" y2="{MT+2*PH+GAP}" '
          f'stroke="{C_MARK}" stroke-width="1.2" stroke-dasharray="4 3"/>')
        a(f'<circle cx="{x:.1f}" cy="{sy_g(0):.1f}" r="4" fill="{C_MARK}"/>')
        ph = phase_at(rows, gbw)
        if ph is not None:
            a(f'<circle cx="{x:.1f}" cy="{sy_p(ph):.1f}" r="4" fill="{C_MARK}"/>')
            # 本测试台激励加在反相端 vinm, vout 已含 180° 反相,
            # 所以 0dB 穿越点处 vp(vout) 直接就是 PM (不要再 +180)
            a(f'<text x="{x+8:.1f}" y="{sy_p(ph)-8:.1f}" fill="{C_MARK}" '
              f'font-size="13">PM = {ph:.1f}°</text>')
        a(f'<text x="{x+8:.1f}" y="{MT+18}" fill="{C_MARK}" font-size="13">'
          f'GBW = {gbw/1e6:.2f} MHz</text>')
        info.append(f"GBW = {gbw/1e6:.3f} MHz")
        if ph is not None:
            info.append(f"PM  = {ph:.2f} deg")
    a0 = rows[0][1] if rows else 0
    info.append(f"低频增益 Av0 = {a0:.2f} dB")
    a(f'<text x="{ML+10}" y="{MT+PH-10}" fill="{TXT}" font-size="13">'
      f'Av0 = {a0:.1f} dB</text>')

    a('</svg>')

    with open(dst, "w", encoding="utf-8") as f:
        f.write("\n".join(o))

    print("已生成:", dst)
    print("  " + "   ".join(info))


if __name__ == "__main__":
    main()
