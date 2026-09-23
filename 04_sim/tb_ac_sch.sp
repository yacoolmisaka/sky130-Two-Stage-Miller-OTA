* ============================================================================
*  TB2b: 开环 AC —— 【原理图网表版】交叉验证
*
*  目的: 检验 03_sch/ota2_miller.sch 画得对不对。
*        如果这份网表的 AC 结果和手写网表(ota2_miller.sp)几乎一致,
*        就说明原理图的连接和参数都对, 可以放心进版图做 LVS。
*
*  与 tb_ac.sp 的三点区别:
*    1) include 的是 xschem 导出的网表 (已用 sch2sim.py 转成可仿真版)
*    2) 该网表自带 Mref (二极管接法), 所以不需要 bias_gen 子电路,
*       只补一个 10uA 的 Iref 电流源即可
*    3) 端口顺序按 xschem 导出顺序: GND vinp vinm vout vbias VDD
*       (手写网表是 vinm vinp vout vdd vss vbias, 顺序不同, 别接错)
* ============================================================================

.include "models.inc"
.include "../03_sch/ota2_miller_sim.spice"

.param VDDV = 1.8
.param VCMV = 0.9
.param CLV  = 2p

VDD   vdd   0      dc {VDDV}
VCM   vinp  0      dc {VCMV}          $ 同相端: DC 偏置 + AC 地

VAC   vin_ac 0     dc 0    ac 1       $ AC 激励源
CIN   vin_ac vinm  1                  $ 1F, AC 短路 / DC 开路

IREF  vdd   vbias  dc 10u             $ 基准电流 (Mref 已在 XOTA 内部)

XOTA  0 vinp vinm vout vbias vdd  ota2_miller   $ 按导出的端口顺序

LFB   vout vinm  1e9                  $ DC 反馈 / AC 开路
CL    vout 0     {CLV}

.ac dec 20 1 1e9

.control
run

echo ""
echo "=================================================================="
echo "  原理图网表 开环 AC 结果"
echo "  对照基线(手写网表): av0=72.65dB  gbw=10.39MHz  pm=63.28deg"
echo "------------------------------------------------------------------"
meas ac av0  FIND vdb(vout) AT=10               $ 10Hz 处低频增益 (dB)
meas ac gbw  WHEN vdb(vout)=0                   $ 单位增益带宽 (Hz)
meas ac pm_at FIND vp(vout) WHEN vdb(vout)=0
meas ac pm_atgbw FIND vp(vout) AT=gbw
echo ""
echo " >>> 相位裕度 PM (deg)   [两种测法 x 180/PI, 应接近]"
print (pm_at*180/PI) (pm_atgbw*180/PI)
echo ""
echo " 判读: 三个数落在基线附近(增益 +-1dB / gbw +-10% / pm +-3deg)"
echo "       => 原理图与手写网表电学等价, 连接无误"
echo "       明显偏离 => 原理图还有连错的地方"
echo "=================================================================="

* 写出曲线供 plot_bode.py 画图对比
let freqv     = frequency
let gain_db   = vdb(vout)
let phase_deg = vp(vout)
wrdata ac_bode_sch.txt freqv gain_db phase_deg
echo " >> 已写出 ac_bode_sch.txt (可与手写的 ac_bode.txt 叠加对比)"
.endc

.end
