#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_pm.py —— 从 ac_bode.txt 独立验算 GBW / PM, 不依赖 ngspice 的 meas

背景: tb_ac.sp 的 AC 激励加在**反相端** vinm (vinp 是 AC 地),
      所以 vout 已经含一次反相, 0dB 穿越点处
          vp(vout) = PM 本身
      而不是 "PM = 180 + vp(vout)" (那是激励加同相端时的口径)。
      ngspice 的 meas 在这两种口径下容易搞混, 所以直接从数据算最可靠。

用法: python3 verify_pm.py ac_bode.txt
"""
import sys, math

def load(path):
    rows = []
    with open(path, encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or line.startswith('*'):
                continue
            p = line.split()
            if len(p) < 3:
                continue
            try:
                # ngspice wrdata 对每个向量写 "x y" (复数则 "x re im"),
                # 本项目 wrdata freqv gain_db phase_deg 实测输出 7 列:
                #   [0]freq  [1]freqv  [2]freqv.imag  [3]freq  [4]gain_db
                #   [5]freq  [6]phase
                if len(p) >= 7:
                    freq, gain, phase = float(p[0]), float(p[4]), float(p[6])
                elif len(p) == 6:          # 每向量 2 列的情况
                    freq, gain, phase = float(p[0]), float(p[1]), float(p[3])
                else:
                    freq, gain, phase = float(p[0]), float(p[1]), float(p[2])
                # ngspice 的 vp()/wrdata 输出是【弧度】(实测: 低频 = π), 转成度
                if abs(phase) < 4.0:      # 弧度 |x|<=π≈3.14; 度数相位不会这么小
                    phase = math.degrees(phase)
                rows.append((freq, gain, phase))
            except ValueError:
                continue
    rows.sort(key=lambda r: r[0])
    return rows

def interp(rows, x, xi=1, yi=2):
    """在列 xi 上插值 x, 返回列 yi 的值"""
    if x <= rows[0][xi]:
        return rows[0][yi]
    if x >= rows[-1][xi]:
        return rows[-1][yi]
    for i in range(len(rows) - 1):
        x0, x1 = rows[i][xi], rows[i + 1][xi]
        if x0 <= x <= x1:
            t = (x - x0) / (x1 - x0)
            return rows[i][yi] + t * (rows[i + 1][yi] - rows[i][yi])
    return rows[-1][yi]

def find_gbw(rows):
    """找增益从 + 变 - 的过零点 (线性插值)"""
    for i in range(len(rows) - 1):
        g0, g1 = rows[i][1], rows[i + 1][1]
        if g0 >= 0 > g1:
            t = g0 / (g0 - g1)
            f0, f1 = rows[i][0], rows[i + 1][0]
            return f0 * (f1 / f0) ** t   # 对数插值
    return None

def main():
    path = sys.argv[1] if len(sys.argv) > 1 else 'ac_bode.txt'
    rows = load(path)
    if not rows:
        print("!! 没读到数据, 检查 %s" % path)
        return

    print("=" * 62)
    print(" 从 %s 独立验算 (%d 个频点)" % (path, len(rows)))
    print("=" * 62)

    av0 = rows[0][1]
    print(" 低频增益 Av0      = %.2f dB" % av0)

    gbw = find_gbw(rows)
    if gbw is None:
        print(" !! 增益在整个扫描范围内没过 0dB, 无法算 GBW/PM")
        return

    ph = interp(rows, gbw, xi=0, yi=2)
    print(" GBW (0dB 穿越)    = %.3f MHz" % (gbw / 1e6))
    print(" 该频点相位 vp     = %.2f deg" % ph)
    print("-" * 62)
    print(" PM (反相激励口径) = %.2f deg      <<< 本测试台正确值" % ph)
    print(" 180+vp (同相口径) = %.2f deg      (若激励在 vinp 才用这个)" % (180 + ph))
    print("-" * 62)

    # 判读
    pm = ph
    if pm < 0:
        pm_j = pm + 360
        print(" 注: vp 为负, 若按缠绕解读则 PM = %.2f deg" % pm_j)
    if 30 <= pm <= 90:
        verdict = "相位裕度合理, 电路稳定"
    elif pm > 90:
        verdict = "PM 异常偏大, 检查相位口径是否取反"
    else:
        verdict = "PM 偏小, 可能不稳定 -> 加宽 M6 或加大 Cc 或加 Rz"
    print(" 判读: %s" % verdict)

    # 关键频点相位, 便于人工核对
    print("-" * 62)
    print(" 关键频点 (频率 / 增益dB / 相位deg):")
    for f in (1e3, 1e5, 1e6, gbw / 10, gbw, gbw * 3, gbw * 10):
        if rows[0][0] <= f <= rows[-1][0]:
            print("   %12.4g Hz   %8.2f dB   %8.2f deg"
                  % (f, interp(rows, f, 0, 1), interp(rows, f, 0, 2)))
    print("=" * 62)

if __name__ == '__main__':
    main()
