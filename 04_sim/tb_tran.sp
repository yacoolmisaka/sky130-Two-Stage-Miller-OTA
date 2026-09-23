* ============================================================================
*  TB3: 瞬态 (.tran) —— 压摆率 SR + 大信号阶跃响应
*  接法: 单位增益缓冲 (vout 接回 vinm), 输入一个大阶跃
*        0.6V -> 1.2V  (在 ICMR 0.8~1.45V 范围内取, 别顶到轨)
*  看什么: 1) vout 上升/下降斜率 = SR
*          2) 有没有振铃 (ringing) -> 相位裕度不足的直观表现
* ============================================================================

.include "models.inc"
.include "../03_sch/ota2_miller.sp"

.param VDDV = 1.8
.param CLV  = 2p

VDD   vdd  0  dc {VDDV}

* 大信号阶跃: 0.6V -> 1.2V, 20ns 上升沿, 周期 2us
VIN   vinp 0  dc 0.6  pulse(0.6 1.2 100n 20n 20n 900n 2u)

XOTA  vout vinp vout vdd 0 vbias  ota2_miller
XBIAS vbias vdd 0  bias_gen

CL    vout 0  {CLV}

.tran 5n 2u

.control
run

echo ""
echo "=================================================================="
echo " 瞬态结果: 压摆率 SR"
echo "------------------------------------------------------------------"
* 上升压摆率: 测 vout 从 0.7V 到 1.1V 的时间, 算斜率
meas tran t_up1 WHEN v(vout)=0.7 RISE=1
meas tran t_up2 WHEN v(vout)=1.1 RISE=1
* 注意: ngspice 的 meas ... PARAM= 复合表达式不可靠 (会把 param= 当函数名),
*       改成先测两个时间点, 再用 let 算斜率, 单位是 V/s
let sr_up = (1.1-0.7)/(t_up2-t_up1)

* 下降压摆率 (第二个边沿, 1.2V -> 0.6V)
meas tran t_dn1 WHEN v(vout)=1.1 FALL=1
meas tran t_dn2 WHEN v(vout)=0.7 FALL=1
let sr_dn = (1.1-0.7)/(t_dn2-t_dn1)

echo ""
echo " >>> 压摆率 SR (V/us)   上升        下降"
print (sr_up/1e6) (sr_dn/1e6)
echo ""
echo " 读取方式: sr_up / sr_dn 单位是 V/s, 除以 1e6 就是 V/us"
echo " 手算期望: SR(+) = Iss/Cc = 20u/1.2p = 16.7 V/us"
echo "           SR(-) = I6/(CL+Cc) = 50u/3.2p = 15.6 V/us"
echo " 判据:     SR 明显偏小 -> 加大 Iss 或 I6 或减小 Cc"
echo ""
echo " 建立/振铃: 看下面写出的 tran_step.txt, 过冲大说明 PM 不够"
echo "=================================================================="

let tv    = time
let voutv = v(vout)
let vinv  = v(vinp)
wrdata tran_step.txt tv voutv vinv
echo " >> 已写出 tran_step.txt (时间 / vout / vinp), 运行:"
echo "    python3 plot_tran.py tran_step.txt"
.endc

.end
