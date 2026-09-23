#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SKY130 两级 Miller 补偿 OTA —— 手算定尺寸 (sizing)
=====================================================
用法:  python3 sizing.py            # 用默认设计目标
       python3 sizing.py --gbw 12e6 --cl 3p --cc 1.5p --iss 20u

输出: 每个管子的 W/L / finger 分配 / 电流，以及预估的 Av / GBW / PM / SR / 功耗。
注意: 这是**手算起点**，不是最终结果。SKY130 实际模型与这里的长沟道近似
      (K'、Vth、lambda 均取典型值) 有偏差，跑完 .op 后必须按 README 的
      "微调规则表" 迭代 2-3 轮。
"""
import math
import argparse

# ============================================================
# 0. SKY130 1.8V 器件的手算近似参数 (典型值，TT corner, 300K)
#    K' = mu*Cox    单位 A/V^2
#    Vth            单位 V
#    lam = 1/(VA)   沟长调制系数，按 L=1um 给，lam 与 L 近似成反比
# ============================================================
KN   = 173e-6      # NMOS  nfet_01v8
KP   = 73e-6       # PMOS  pfet_01v8  (~0.42 x KN)
VTHN = 0.45
VTHP = 0.50
LAMN = 0.05        # @ L = 1um
LAMP = 0.08        # @ L = 1um

def sat_region_check(vds, vgs, vth):
    return vds >= (vgs - vth)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--vdd', type=float, default=1.8)
    ap.add_argument('--gbw', type=float, default=15e6,   help='目标单位增益带宽 Hz')
    ap.add_argument('--cl',  type=float, default=2e-12,  help='负载电容 F')
    ap.add_argument('--cc',  type=float, default=1.2e-12,help='米勒补偿电容 F')
    ap.add_argument('--iss', type=float, default=20e-6,  help='尾电流 A')
    ap.add_argument('--sr',  type=float, default=10e6,   help='目标压摆率 V/s')
    ap.add_argument('--i6',  type=float, default=50e-6,  help='第二级静态电流 A')
    ap.add_argument('--iref',type=float, default=10e-6,  help='基准电流 A')
    ap.add_argument('--vicm_min', type=float, default=0.8, help='输入共模下限 V')
    ap.add_argument('--vicm_max', type=float, default=1.4, help='输入共模上限 V')
    ap.add_argument('--pm',   type=float, default=60.0, help='目标相位裕度 deg')
    a = ap.parse_args()

    VDD, GBW, CL, CC, ISS, SR, I6, IREF = (
        a.vdd, a.gbw, a.cl, a.cc, a.iss, a.sr, a.i6, a.iref)

    print("=" * 68)
    print(" SKY130 两级 Miller OTA —— 手算 sizing")
    print("=" * 68)
    print(f" 设计目标 : GBW={GBW/1e6:.1f}MHz  CL={CL*1e12:.2f}pF  Cc={CC*1e12:.2f}pF"
          f"  SR>={SR/1e6:.0f}V/us  Iss={ISS*1e6:.0f}uA")

    # ---------- Step 1: Cc 下限 (PM>60deg 的经典判据 Cc > 0.22*CL) ----------
    print("\n[Step 1] 米勒电容 Cc 校验")
    print(f"  Cc/CL = {CC/CL:.3f}   判据 Cc >= 0.22*CL = {0.22*CL*1e12:.3f} pF"
          f"   -> {'OK' if CC >= 0.22*CL else 'FAIL, 加大 Cc'}")

    # ---------- Step 2: 尾电流 Iss (由压摆率定) ----------
    print("\n[Step 2] 尾电流 (由 SR 定)")
    iss_sr = SR * CC
    print(f"  SR = Iss/Cc  =>  Iss >= {iss_sr*1e6:.2f} uA")
    print(f"  取 Iss = {ISS*1e6:.2f} uA  -> SR = {ISS/CC/1e6:.2f} V/us "
          f"{'OK' if ISS >= iss_sr else 'FAIL, 加大 Iss'}")
    ID1 = ISS / 2.0

    # ---------- Step 3: M1/M2 差分对 (由 GBW 定 gm1) ----------
    print("\n[Step 3] M1/M2 差分输入对 (由 GBW 定)")
    gm1 = 2 * math.pi * GBW * CC
    WL1 = gm1**2 / (2 * KN * ID1)
    vov1 = 2 * ID1 / gm1
    print(f"  gm1 = 2*pi*GBW*Cc = {gm1*1e6:.1f} uS")
    print(f"  Id1 = Iss/2 = {ID1*1e6:.2f} uA   ->  Vov1 = 2*Id1/gm1 = {vov1:.3f} V"
          f"  {'(偏小,注意亚阈值)' if vov1 < 0.10 else 'OK'}")
    print(f"  (W/L)1 = gm1^2/(2*Kn'*Id1) = {WL1:.2f}")
    NF1_W = 2.0                                   # 单指栅宽, 便于共质心拆 2 finger
    nf1 = max(2, int(math.ceil(WL1 / NF1_W)))     # 至少 2 指, 好做 ABBA 共质心
    W1 = nf1 * NF1_W
    L1 = 1.0
    gm1_r = math.sqrt(2 * KN * (W1/L1) * ID1)
    gbw_r = gm1_r / (2 * math.pi * CC)
    print(f"  => 取 M1/M2: W={W1}um ({nf1} finger x {NF1_W}um)  L={L1}um  (W/L={W1/L1:.1f})"
          f"   实际 gm1={gm1_r*1e6:.1f}uS  GBW={gbw_r/1e6:.2f}MHz")

    # ---------- Step 4: M3/M4 PMOS 电流镜负载 (由 ICMR 上限定) ----------
    print("\n[Step 4] M3/M4 PMOS 电流镜负载 (由 ICMR 上限定)")
    # Vicm(max) = VDD - |Vthp| - |Vov3| + Vthn
    vov3_max = VDD - abs(VTHP) + VTHN - a.vicm_max
    ID3 = ID1
    WL3 = 2 * ID3 / (KP * vov3_max**2) if vov3_max > 0 else 0
    WL3 = max(WL3, 1.0)
    NF3_W = 2.0
    nf3 = max(2, int(math.ceil(WL3 / NF3_W)))
    W3 = nf3 * NF3_W
    L3 = 1.0
    vov3 = math.sqrt(2 * ID3 / (KP * (W3/L3)))
    gm3 = 2 * ID3 / vov3
    vicm_max = VDD - abs(VTHP) - vov3 + VTHN
    print(f"  Vicm(max) = VDD-|Vthp|-|Vov3|+Vthn >= {a.vicm_max} V"
          f"  =>  |Vov3| <= {vov3_max:.3f} V  =>  (W/L)3 >= {WL3:.2f}")
    print(f"  => 取 M3/M4: W={W3}um ({nf3} finger x {NF3_W}um)  L={L3}um  (W/L={W3/L3:.1f})"
          f"   |Vov3|={vov3:.3f}V  gm3={gm3*1e6:.1f}uS")
    print(f"  实际 Vicm(max) = {vicm_max:.3f} V  {'OK' if vicm_max >= a.vicm_max else 'FAIL'}")

    # ---------- Step 5: M5 尾电流源 (由 ICMR 下限 + 基准镜像定) ----------
    print("\n[Step 5] M5 尾电流源 (由 ICMR 下限定)")
    vov5_max = a.vicm_min - VTHN - vov1
    WL5_min = 2 * ISS / (KN * vov5_max**2) if vov5_max > 0 else 1e9
    # 同时满足与基准管 (W/L)ref 的镜像比: (W/L)5 = (Iss/Iref)*(W/L)ref
    # 先定基准管: 取 Vov_ref = 0.15V 左右, (W/L)ref = 2*Iref/(Kn*Vov^2)
    vov_ref = 0.15
    WLref = 2 * IREF / (KN * vov_ref**2)
    WLref = round(WLref * 2) / 2
    WLref = max(WLref, 1.0)
    vov_ref = math.sqrt(2 * IREF / (KN * WLref))
    WL5 = WLref * (ISS / IREF)
    W5 = WL5
    L5 = 1.0
    vov5 = math.sqrt(2 * ISS / (KN * (W5/L5)))
    vicm_min = vov5 + VTHN + vov1
    print(f"  基准管 Mref: (W/L)ref = {WLref:.1f}  (Iref={IREF*1e6:.1f}uA,"
          f" Vov_ref={vov_ref:.3f}V, Vgs={VTHN+vov_ref:.3f}V)")
    print(f"  Vicm(min) = Vov5 + Vthn + Vov1 >= ... 要求 <= {a.vicm_min} V"
          f" => (W/L)5 >= {WL5_min:.2f}")
    print(f"  按镜像比 (W/L)5 = (Iss/Iref)*(W/L)ref = {WL5:.1f}"
          f"  {'OK' if WL5 >= WL5_min else '小于 ICMR 下限要求, 需加大'}")
    print(f"  => 取 M5: W={W5}um  L={L5}um   Vov5={vov5:.3f}V"
          f"   实际 Vicm(min) = {vicm_min:.3f} V")

    # ---------- Step 6: M6 第二级 PMOS 共源 (由相位裕度定 gm6) ----------
    print("\n[Step 6] M6 第二级共源放大管 (由 PM>=60deg 定 gm6)")
    # PM=60deg 判据: gm6 >= 2.2 * (CL/Cc) * gm1
    gm6_req = 2.2 * (CL / CC) * gm1_r
    # 同时 I6 >= SR*(CL+Cc) 保证负向压摆率
    i6_sr = SR * (CL + CC)
    print(f"  gm6 >= 2.2*(CL/Cc)*gm1 = {gm6_req*1e6:.1f} uS")
    print(f"  I6  >= SR*(CL+Cc)      = {i6_sr*1e6:.2f} uA   (取 I6={I6*1e6:.1f}uA)"
          f" {'OK' if I6 >= i6_sr else 'FAIL, 加大 I6'}")
    WL6 = gm6_req**2 / (2 * KP * I6)
    print(f"  (W/L)6 >= gm6^2/(2*Kp'*I6) = {WL6:.2f}   <- 仅为 2.2 系数粗估")
    # 2.2 系数是粗略判据, 真正要按 PM 目标迭代:
    #   p2 = gm6/(2*pi*CL),  z1 = gm6/(2*pi*Cc)   (RHP 零点, 吃掉相位)
    #   PM = 90 - atan(GBW/p2) - atan(GBW/z1)
    fw6 = 4.0
    nf6 = max(1, int(math.ceil(WL6 / fw6)))
    print(f"  按 PM >= {a.pm:.0f} deg 迭代 M6 栅宽:")
    for _ in range(40):
        W6 = nf6 * fw6
        L6 = 1.0
        gm6 = math.sqrt(2 * KP * (W6/L6) * I6)
        p2 = gm6 / (2 * math.pi * CL)
        z1 = gm6 / (2 * math.pi * CC)
        pm_i = 90 - math.degrees(math.atan(gbw_r / p2)) - math.degrees(math.atan(gbw_r / z1))
        print(f"    W6={W6:5.1f}um (nf={nf6:2d})  gm6={gm6*1e6:6.1f}uS  "
              f"p2={p2/1e6:6.2f}MHz  z1={z1/1e6:6.2f}MHz  PM={pm_i:5.1f} deg")
        if pm_i >= a.pm:
            break
        nf6 += 1
    vov6 = 2 * I6 / gm6
    print(f"  => 取 M6: W={W6}um ({nf6} finger x {fw6}um)  L={L6}um"
          f"   gm6={gm6*1e6:.1f}uS  |Vov6|={vov6:.3f}V  PM={pm_i:.1f} deg"
          f"  {'OK' if gm6 >= gm6_req else 'FAIL'}")

    # ---------- Step 7: M7 第二级 NMOS 电流沉 (镜像自 Mref) ----------
    print("\n[Step 7] M7 第二级电流沉 (镜像自 Mref)")
    WL7 = WLref * (I6 / IREF)
    fw7 = 5.0
    nf7 = max(1, int(round(WL7 / fw7)))
    W7 = nf7 * fw7
    L7 = 1.0
    vov7 = math.sqrt(2 * I6 / (KN * (W7/L7)))
    print(f"  (W/L)7 = (I6/Iref)*(W/L)ref = {WL7:.1f}")
    print(f"  => 取 M7: W={W7}um ({nf7} finger x {fw7}um)  L={L7}um   Vov7={vov7:.3f}V")

    # ---------- Step 8: 性能预估 ----------
    print("\n[Step 8] 性能预估")
    ro1 = 1 / (LAMN * ID1)
    ro3 = 1 / (LAMP * ID3)
    ro6 = 1 / (LAMP * I6)
    ro7 = 1 / (LAMN * I6)
    R1 = ro1 * ro3 / (ro1 + ro3)
    R2 = ro6 * ro7 / (ro6 + ro7)
    Av1 = gm1_r * R1
    Av2 = gm6 * R2
    Av = Av1 * Av2
    print(f"  第一级: ro2||ro4 = {R1/1e6:.3f} Mohm  Av1 = {Av1:.1f} ({20*math.log10(Av1):.1f} dB)")
    print(f"  第二级: ro6||ro7 = {R2/1e6:.3f} Mohm  Av2 = {Av2:.1f} ({20*math.log10(Av2):.1f} dB)")
    print(f"  总增益 Av  = {Av:.0f} V/V = {20*math.log10(Av):.1f} dB   (未计 CL 加载/体效应, 实际低 5-10dB)")
    print(f"  GBW        = {gbw_r/1e6:.2f} MHz")
    # 极点零点
    p1 = 1 / (2 * math.pi * R1 * gm6 * ro6 * ro7 / (ro6 + ro7) * CC)
    p2 = -gm6 / (2 * math.pi * CL)
    z1 = gm6 / (2 * math.pi * CC)
    pm = 90 - math.degrees(math.atan(gbw_r / abs(p2))) - math.degrees(math.atan(gbw_r / z1))
    print(f"  主极点 p1  = {p1/1e3:.2f} kHz   (米勒分裂后)")
    print(f"  次极点 p2  = gm6/(2*pi*CL) = {abs(p2)/1e6:.2f} MHz")
    print(f"  RHP 零点 z1= gm6/(2*pi*Cc) = {z1/1e6:.2f} MHz  (z1/GBW = {z1/gbw_r:.2f})")
    print(f"  粗略 PM    = {pm:.1f} deg   (无 Rz 时 z1 会吃掉相位, 若 <55deg 需加 Rz 或加大 gm6)")
    sr_pos = ISS / CC
    sr_neg = I6 / (CL + CC)
    idd = IREF + ISS + I6
    print(f"  SR(+) = Iss/Cc     = {sr_pos/1e6:.2f} V/us")
    print(f"  SR(-) = I6/(CL+Cc) = {sr_neg/1e6:.2f} V/us")
    print(f"  静态电流 = {idd*1e6:.1f} uA   功耗 = {VDD*idd*1e6:.1f} uW")

    # ---------- 汇总表 ----------
    print("\n" + "=" * 68)
    print(" 尺寸汇总表 (手算起点)")
    print("=" * 68)
    print(f"{'器件':<8}{'类型':<6}{'W总(um)':>9}{'L(um)':>7}{'单指W':>7}{'nf':>5}"
          f"{'W/L':>7}{'Id(uA)':>8}  说明")
    rows = [
        ("M1,M2", "NMOS", W1, L1, NF1_W, nf1, W1/L1, ID1*1e6, "差分输入对 (共质心)"),
        ("M3,M4", "PMOS", W3, L3, NF3_W, nf3, W3/L3, ID3*1e6, "电流镜负载 (M3 二极管)"),
        ("M5",    "NMOS", W5, L5, 5.0,   max(1,int(W5/5)), W5/L5, ISS*1e6, "尾电流源"),
        ("M6",    "PMOS", W6, L6, fw6,   nf6, W6/L6, I6*1e6,  "第二级共源 (主增益)"),
        ("M7",    "NMOS", W7, L7, fw7,   nf7, W7/L7, I6*1e6,  "第二级电流沉"),
        ("Mref",  "NMOS", WLref, 1.0, WLref, 1, WLref, IREF*1e6,"偏置基准 (二极管连接)"),
    ]
    for r in rows:
        print(f"{r[0]:<8}{r[1]:<6}{r[2]:>9.1f}{r[3]:>7.1f}{r[4]:>7.1f}{r[5]:>5d}"
              f"{r[6]:>7.1f}{r[7]:>8.1f}  {r[8]}")
    print("\n  >> ngspice 网表写法: W = 单指W, nf = 指数 (BSIM4 约定, 总宽 = W * nf)")
    print("  >> 例: XM6 vout n2 vdd vdd pfet W=4u L=1u nf=14   (总宽 56um)")
    print("\n  Cc = %.2f pF (MiM 优先, 其次 MOSCAP)    CL = %.2f pF"
          % (CC*1e12, CL*1e12))
    print("=" * 68)

if __name__ == "__main__":
    main()
