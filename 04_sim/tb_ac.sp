* ============================================================================
*  TB2: 开环交流特性 (.ac) —— 增益 / GBW / 相位裕度
*
*  开环测试的经典 L-C 手法:
*    - Lfb = 1e9 H : DC 时短路 -> vout 被反馈拉到与 vinm 相等, 工作点自动建立
*                    AC 时阻抗 jwL 极大 -> 反馈断开, 真正开环
*    - Cin = 1 F   : DC 时开路 (不影响工作点)
*                    AC 时短路 -> 把 AC 激励注入 vinm
*    - vinp 直接接直流源 Vcm, 所以它同时是 DC 偏置源和 AC 地
*    - 差分 AC 幅度 = 1V (0 - (-1)), 所以 |v(vout)| 数值上就等于开环增益
* ============================================================================

.include "models.inc"
.include "../03_sch/ota2_miller.sp"

.param VDDV = 1.8
.param VCMV = 0.9
.param CLV  = 2p

VDD   vdd   0      dc {VDDV}
VCM   vinp  0      dc {VCMV}          $ 同相端: DC 偏置 + AC 地

VAC   vin_ac 0     dc 0    ac 1       $ AC 激励源
CIN   vin_ac vinm  1                  $ 1F, AC 短路 / DC 开路

XOTA  vinm vinp vout vdd 0 vbias  ota2_miller
XBIAS vbias vdd 0  bias_gen

LFB   vout vinm  1e9                  $ DC 反馈 / AC 开路
CL    vout 0     {CLV}

.ac dec 20 1 1e9

.control
run

echo ""
echo "=================================================================="
echo " 开环 AC 结果"
echo "------------------------------------------------------------------"
meas ac av0  FIND vdb(vout) AT=10               $ 10Hz 处低频增益 (dB)
meas ac gbw  WHEN vdb(vout)=0                   $ 增益过 0dB 的频率 (Hz)
* 注意1: ngspice 的 meas FIND 后面不能直接写 (180+vp(vout)) 这种复合表达式,
*        会报 "no such vector". 必须先 find 纯向量, 再用 let 算。
* 注意2: 本测试台激励加在反相端 (vinm), 所以 vout 已含一次反相,
*        0dB 点处 vp(vout) 直接就等于 PM, 不需要再加 180。
*        下面两种算法都打出来, 交叉验证。
* 注意3: ngspice 的 vp()/wrdata 返回【弧度】! 实测低频 = 3.1412 = π。
*        所以 meas 出来的 pm_xxx 要乘 180/PI 才是度数 (0.8788 rad = 50.3 deg)。
meas ac pm_at FIND vp(vout) WHEN vdb(vout)=0
meas ac pm_atgbw FIND vp(vout) AT=gbw
echo ""
echo " >>> 相位裕度 PM (deg)   [两种测法 x 180/PI, 应接近]"
print (pm_at*180/PI) (pm_atgbw*180/PI)
echo ""
echo " 读取方式:  av0 = 低频增益(dB)   gbw = 单位增益带宽(Hz)   pm = 相位裕度(度)"
echo " 目标:      av0 >= 60dB   gbw = 10~20MHz   pm >= 60deg"
echo " 判据:      pm < 55deg  -> 加宽 M6 或加调零电阻 Rz (见 README 微调表)"
echo "            pm > 75deg  -> M6 太宽, 可收窄省面积"
echo "=================================================================="

* 把幅频/相频曲线写出, 供 plot_bode.py 画波特图
let freqv     = frequency
let gain_db   = vdb(vout)
let phase_deg = vp(vout)
wrdata ac_bode.txt freqv gain_db phase_deg
echo " >> 已写出 ac_bode.txt (频率 / 增益dB / 相位deg), 运行:"
echo "    python3 plot_bode.py ac_bode.txt"
.endc

.end
