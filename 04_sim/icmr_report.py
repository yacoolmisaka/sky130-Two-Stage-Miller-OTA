#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ICMR 报告 —— 读 icmr.txt, 自动给出输入共模范围
用法:  python3 icmr_report.py icmr.txt
输入格式(ngspice wrdata): vcm  vout  ntail  n1  n2
判据:  |vout - vcm| < 5mV  且  v(ntail) > 0.20V (尾管 M5 未进线性区)
"""
import sys

ERR_MV   = 5.0     # 跟随误差上限 (mV)
VDS5_MIN = 0.20    # 尾管 Vds 下限 (V)


def read_data(path):
    rows = []
    with open(path, "r", errors="ignore") as f:
        for line in f:
            p = line.split()
            if len(p) < 5:
                continue
            try:
                rows.append(tuple(float(x) for x in p[:5]))
            except ValueError:
                continue
    rows.sort()
    return rows


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "icmr.txt"
    rows = read_data(src)
    if not rows:
        print("没读到数据:", src)
        sys.exit(1)

    ok = [r for r in rows
          if abs(r[1] - r[0]) * 1000 < ERR_MV and r[2] > VDS5_MIN]

    print("=" * 58)
    print(" ICMR 报告")
    print("=" * 58)
    print(f" 判据: |vout - vcm| < {ERR_MV} mV   且   Vds5 > {VDS5_MIN} V")
    print(f" 扫描点数: {len(rows)}    合格点数: {len(ok)}")

    if not ok:
        print("\n !! 全区间不合格 —— 检查偏置是否建立、管子是否饱和")
        print("    先跑 tb_op.sp 看 region")
        sys.exit(1)

    lo, hi = ok[0][0], ok[-1][0]
    print(f"\n   ICMR = {lo:.3f} V  ~  {hi:.3f} V   (宽度 {hi-lo:.3f} V)")
    print(f"   手算期望 0.78 V ~ 1.45 V")

    # 分别报: 仅跟随误差合格 / 仅尾管合格, 帮助定位是哪个先失效
    follow = [r[0] for r in rows if abs(r[1] - r[0]) * 1000 < ERR_MV]
    tailok = [r[0] for r in rows if r[2] > VDS5_MIN]
    if follow:
        print(f"\n   仅按跟随误差: {follow[0]:.3f} ~ {follow[-1]:.3f} V")
    if tailok:
        print(f"   仅按尾管饱和: {tailok[0]:.3f} ~ {tailok[-1]:.3f} V"
              f"   -> 尾管在 Vds5={min(r[2] for r in rows):.3f}V 处受限")

    print("\n 下限太高 (>0.9V): Vicm(min)=Vov5+Vthn+Vov1, 要降低就减小 Vov5")
    print("                   -> 加大 M5 的 (W/L)  (或减小 Iref 后重配镜像比)")
    print(" 上限太低 (<1.2V): Vicm(max)=VDD-|Vthp|-|Vov3|+Vthn, 要提高就减小 |Vov3|")
    print("                   -> 加大 M3/M4 的 (W/L)")
    print("=" * 58)


if __name__ == "__main__":
    main()
