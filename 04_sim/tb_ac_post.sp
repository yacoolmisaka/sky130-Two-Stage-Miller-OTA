* ============================================================================
*  TB2c: 开环 AC —— 【版图后仿版】含寄生
*
*  与 tb_ac_sch.sp 的三点区别:
*    1) include 的是 magic 导出的【含寄生】版图网表 —— 它是 flat 形式,
*       器件直接铺在顶层(80 个实例 + 29 个寄生电容), 没有 .subckt 包装,
*       所以【没有 XOTA 可调】, 激励直接接到网表的顶层节点名上
*    2) 版图网表里的地叫 "GND" 而不是 0, 用一个 0V 源把它钉到 0
*       (spice 大小写不敏感, 网表里的 VDD 和这里的 vdd 是同一个节点)
*    3) 端口顺序的坑不存在了(不是子电路调用), 但节点名必须逐字对上:
*       VDD GND vout vbias vinm vinp n1 n2 ntail nz
*
*  基线(前仿/原理图网表): av0=72.65dB  gbw=10.39MHz  pm=63.28deg
* ============================================================================

.include "models.inc"
* 注意: include 的是【清洗过】的网表 —— magic 会在行尾写 "**FLOATING" 标记,
*       而 spice 只有【行首】的 * 才是注释, 行尾的 * 会被 ngspice 当成参数报
*       "unknown parameter (*)"，所以必须先用 run_postsim.sh 把它剥掉。
.include "ota2_pext_clean.spice"

.param VDDV = 1.8
.param VCMV = 0.9
.param CLV  = 2p

VDD   vdd   0      dc {VDDV}
* 注意: 这里【不能】再补一个 "VGND GND 0 dc 0"。
*   ngspice 会把网表里的 GND 节点自动归一化成 0（报错信息里
*   "c20 nz 0" 而源文件写的是 "C20 nz GND" 就是证据），
*   再补一个 0V 源就等于把它接在 0 和 0 之间 -> 
*   "Fatal error: instance vgnd is a shorted VSRC"，整个仿真直接中止。
VCM   vinp  0      dc {VCMV}         $ 同相端: DC 偏置 + AC 地

VAC   vin_ac 0     dc 0    ac 1      $ AC 激励源
CIN   vin_ac vinm  1                  $ 1F, AC 短路 / DC 开路

IREF  vdd   vbias  dc 10u             $ 基准电流 (Mref 已在版图内部)

LFB   vout vinm  1e9                  $ DC 反馈 / AC 开路
CL    vout 0     {CLV}

.ac dec 20 1 1e9

.control
run

echo ""
echo "=================================================================="
echo "  版图后仿 开环 AC 结果 (含寄生)"
echo "  基线(前仿/原理图): av0=72.65dB  gbw=10.39MHz  pm=63.28deg"
echo "------------------------------------------------------------------"
meas ac av0  FIND vdb(vout) AT=10               $ 10Hz 处低频增益 (dB)
meas ac gbw  WHEN vdb(vout)=0                   $ 单位增益带宽 (Hz)
meas ac pm_at FIND vp(vout) WHEN vdb(vout)=0
meas ac pm_atgbw FIND vp(vout) AT=gbw
echo ""
echo " >>> 相位裕度 PM (deg)   [两种测法 x 180/PI, 应接近]"
print (pm_at*180/PI) (pm_atgbw*180/PI)
echo ""
echo " 判读: 后仿相对前仿的偏移主要来自连线寄生电容(米勒电容被抬高等),"
echo "       通常 gbw 下降 10~20% / pm 略降 —— 属正常;"
echo "       若增益或 PM 掉得离谱, 优先查 C14/C18/C25 这几个大电容连到哪了"
echo "=================================================================="

let freqv     = frequency
let gain_db   = vdb(vout)
let phase_deg = vp(vout)
wrdata ac_bode_post.txt freqv gain_db phase_deg
echo " >> 已写出 ac_bode_post.txt (可与 ac_bode_sch.txt 叠加对比)"
.endc

.end
