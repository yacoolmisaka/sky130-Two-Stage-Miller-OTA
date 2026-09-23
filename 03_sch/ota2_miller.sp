* ============================================================================
*  SKY130 两级 Miller 补偿 OTA  —— 核心电路网表 (真 sky130 模型版)
*
*  模型来源: 04_sim/models.inc → volare 装的 c6d73a3... 版本的
*            combined/continuous/sky130.lib.spice
*  注意: l/w 用微米数值 (l=1 表示 1um), nf 是 finger 数 (BSIM4 标准).
*
*  结构: M1/M2 差分对 + M3/M4 PMOS 电流镜负载 + M5 尾电流源
*        M6 PMOS 共源放大 + M7 NMOS 电流沉
*        Cc 跨接在 M6 栅(n2) 与 漏(vout) 之间 (米勒补偿)
*  极性: vinp 同相, vinm 反相
*  端口: .subckt ota2_miller vinm vinp vout vdd vss vbias
* ============================================================================

* ---------------- 器件尺寸 (调参只改这一段) ----------------
* 两条 sky130 模型卡铁律 (踩过坑, 别改回去):
*  1) w 只能写 2~2.5um。写 >=10 会落进 bin5, 运行时算出
*     Pclm/Drout/Eta0 负值 -> BSIM4 校验 fatal (sed 翻正救不了,
*     因为那些值是算出来的不是写死的)。
*  2) nf 在本 PDK 的 subckt 里**不倍增电流**(实测 W_eff 只认 w)。
*     要放大电流只能用 m= 倍增 (实测 m=5 -> Id 精确 x5.0)。
* 所以: w 固定小值躲 bin, 总宽/电流靠 m= 拉, nf=1 仅作占位。
.param WF1  = 2       $ M1/M2 单指宽 (um)
.param NF1  = 1
.param M1V  = 2       $ -> 等效总宽 4um
.param L1   = 1

.param WF3  = 2       $ M3/M4 单指宽
.param NF3  = 1
.param M3V  = 2       $ -> 等效总宽 4um
.param L3   = 1

.param WF5  = 2       $ M5 单指宽
.param NF5  = 1
.param M5V  = 12      $ -> 等效总宽 24um
.param L5   = 1

.param WF6  = 2       $ M6 单指宽
.param NF6  = 1
.param M6V  = 28      $ -> 等效总宽 56um
.param L6   = 1

.param WF7  = 2.5     $ M7 单指宽
.param NF7  = 1
.param M7V  = 25      $ -> 等效总宽 62.5um
.param L7   = 1

.param WFREF = 2.5    $ 偏置基准管 Mref
.param NFREF = 1
.param MREFV = 5      $ -> 等效总宽 12.5um
.param LREF  = 1

* ---- 镜像比铁律 (踩过坑, 改任一个都要同步改其它两个) ----
*  接 vbias 的三个 NMOS (M5/M7/Mref) 的 Vgs 相同 -> Vov 相同,
*  所以电流比 = (w*m) 之比, 不是 m 之比:
*      I5 / Iref = (WF5*M5V) / (WFREF*MREFV) = (2*12)/(2.5*5)   = 1.92 ~ 2 -> 20uA
*      I7 / Iref = (WF7*M7V) / (WFREF*MREFV) = (2.5*25)/(2.5*5) = 5       -> 50uA
*
*  这组 m 值是两个约束的折中:
*    (a) M5 要饱和: Vds5 = V(ntail) ~ 0.12V, 需要 Vov5 < 0.12V
*    (b) Vov 别太小: < 0.06V 就逼近亚阈, 匹配/噪声变差, 一般留 0.10V 左右
*  实测标定: m5=4/mref=1  -> Vov=0.206V (太大, M5 进线性区, Vds-Vov=-0.097)
*            m5=20/mref=8 -> Vov=0.040V (太小, 逼近亚阈)
*            m5=12/mref=5 -> 取中, 预期 Vov ~ 0.09~0.11V, M5 保持饱和

.param CCV   = 1.2p   $ 米勒补偿电容 (前仿理想 C; 版图阶段换 MiM)
.param RZV   = 3k     $ 调零电阻 ~1.2/gm6 (gm6=387uS -> 1/gm6=2.58k, 取整 3k)
.param IREFV = 10u    $ 基准电流

* ---------------- 核心 OTA 子电路 ----------------
.subckt ota2_miller vinm vinp vout vdd vss vbias

* --- 第一级 ---
XM1  n1    vinm  ntail vss  sky130_fd_pr__nfet_01v8  l={L1} w={WF1} nf={NF1} m={M1V}
XM2  n2    vinp  ntail vss  sky130_fd_pr__nfet_01v8  l={L1} w={WF1} nf={NF1} m={M1V}
XM3  n1    n1    vdd   vdd  sky130_fd_pr__pfet_01v8  l={L3} w={WF3} nf={NF3} m={M3V}
XM4  n2    n1    vdd   vdd  sky130_fd_pr__pfet_01v8  l={L3} w={WF3} nf={NF3} m={M3V}
XM5  ntail vbias vss   vss  sky130_fd_pr__nfet_01v8  l={L5} w={WF5} nf={NF5} m={M5V}

* --- 第二级 ---
XM6  vout  n2    vdd   vdd  sky130_fd_pr__pfet_01v8  l={L6} w={WF6} nf={NF6} m={M6V}
XM7  vout  vbias vss   vss  sky130_fd_pr__nfet_01v8  l={L7} w={WF7} nf={NF7} m={M7V}

* --- 米勒补偿电容 + 调零电阻 ---
* RHP 零点 z1 = gm6/(2π·Cc) 会吃相位, 串 Rz 后 z1 = (1/Cc)·(1/gm6 - Rz):
*   Rz = 1/gm6 -> z1 消失;  Rz > 1/gm6 -> z1 变左半平面, 反而补相位。
* 版图阶段: 理想电阻换成 PDK 的 poly 电阻 sky130_fd_pr__res_xhigh_po_0p69
*           (W=0.69 固定, L=1.035 -> 1.5 方块 x 2000 = 3k), 与 xschem 原理图/导出网表一致。
RZ   n2    nz    {RZV}
CC   nz    vout  {CCV}

.ends ota2_miller


* ============================================================================
*  偏置支路: Iref 灌进二极管连接的 Mref 产生 vbias
* ============================================================================
.subckt bias_gen vbias vdd vss
IREF  vdd  vbias  dc {IREFV}
XMREF vbias vbias vss vss sky130_fd_pr__nfet_01v8 l={LREF} w={WFREF} nf={NFREF} m={MREFV}
.ends bias_gen
