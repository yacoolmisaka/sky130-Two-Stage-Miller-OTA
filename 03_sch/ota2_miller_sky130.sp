* ============================================================================
*  SKY130 两级 Miller 补偿 OTA  —— 真 sky130 模型版 (下载完模型后用这个)
*
*  使用方法:
*    1) volare/ciel 下载完整 sky130A 后找到模型文件, 例如
*         ~/.volare/sky130/versions/<hash>/sky130A/libs.tech/combined/continuous/sky130.lib.spice
*    2) 把 04_sim/models.inc 改成一行:
*         .lib "<上面那个绝对路径>" tt
*    3) 把本文件复制为 ota2_miller.sp (覆盖 BSIM1 应急版)
*       或者把 04_sim/tb_*.sp 里的 .include "../03_sch/ota2_miller.sp"
*       改成 .include "../03_sch/ota2_miller_sky130.sp"
*
*  注意: sky130 官方示例里 l/w 用**微米数值** (l=1 表示 1um, 不是 1u),
*        nf 是 finger 数 (BSIM4 参数, 真模型支持, 与版图一一对应).
*
*  结构: M1/M2 差分对 + M3/M4 PMOS 电流镜负载 + M5 尾电流源
*        M6 PMOS 共源放大 + M7 NMOS 电流沉
*        Cc 跨接在 M6 栅(n2) 与 漏(vout) 之间 (米勒补偿)
*  极性: vinp 同相, vinm 反相
*  端口: .subckt ota2_miller vinm vinp vout vdd vss vbias
* ============================================================================

* ---------------- 器件尺寸 (调参只改这一段) ----------------
.param WF1  = 2       $ M1/M2 单指宽 (um)
.param NF1  = 2       $ M1/M2 finger -> 总宽 4um
.param L1   = 1

.param WF3  = 2       $ M3/M4 单指宽
.param NF3  = 2       $ -> 总宽 4um
.param L3   = 1

.param WF5  = 5       $ M5 单指宽
.param NF5  = 2       $ -> 总宽 10um
.param L5   = 1

.param WF6  = 4       $ M6 单指宽
.param NF6  = 14      $ -> 总宽 56um  (手算48um, 取56留PM余量)
.param L6   = 1

.param WF7  = 5       $ M7 单指宽
.param NF7  = 5       $ -> 总宽 25um
.param L7   = 1

.param WFREF = 5      $ 偏置基准管 Mref
.param LREF  = 1

.param CCV   = 1.2p   $ 米勒补偿电容 (前仿理想 C; 版图阶段换 MiM)
.param IREFV = 10u    $ 基准电流

* ---------------- 核心 OTA 子电路 ----------------
.subckt ota2_miller vinm vinp vout vdd vss vbias

* --- 第一级 ---
XM1  n1    vinm  ntail vss  sky130_fd_pr__nfet_01v8  l={L1} w={WF1} nf={NF1}
XM2  n2    vinp  ntail vss  sky130_fd_pr__nfet_01v8  l={L1} w={WF1} nf={NF1}
XM3  n1    n1    vdd   vdd  sky130_fd_pr__pfet_01v8  l={L3} w={WF3} nf={NF3}
XM4  n2    n1    vdd   vdd  sky130_fd_pr__pfet_01v8  l={L3} w={WF3} nf={NF3}
XM5  ntail vbias vss   vss  sky130_fd_pr__nfet_01v8  l={L5} w={WF5} nf={NF5}

* --- 第二级 ---
XM6  vout  n2    vdd   vdd  sky130_fd_pr__pfet_01v8  l={L6} w={WF6} nf={NF6}
XM7  vout  vbias vss   vss  sky130_fd_pr__nfet_01v8  l={L7} w={WF7} nf={NF7}

* --- 米勒补偿电容 ---
CC   n2    vout  {CCV}

.ends ota2_miller


* ============================================================================
*  偏置支路: Iref 灌进二极管连接的 Mref 产生 vbias
* ============================================================================
.subckt bias_gen vbias vdd vss
IREF  vdd  vbias  dc {IREFV}
XMREF vbias vbias vss vss sky130_fd_pr__nfet_01v8 l={LREF} w={WFREF} nf=1
.ends bias_gen
