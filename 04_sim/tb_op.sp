* ============================================================================
*  TB1: 直流工作点 (.op)
*  目的: 1) 确认所有管子都在饱和区   2) 拿到真实 gm / Id / Vov / ro
*        3) 与 02_sizing 手算值对比, 决定要不要调尺寸
*  接法: 单位增益缓冲 (vout 直接连回 vinm), 这样 DC 工作点自动稳定在 vout=vinp
*
*  重要: sky130 器件是 subckt 包装 (.subckt sky130_fd_pr__nfet_01v8 ...) ,
*        里面才是真正的 MOSFET (实例名 msky130_fd_pr__nfet_01v8)。
*        所以查参数的路径是三层: @m.<上层subckt>.<X实例>.msky130_fd_pr__<管型>[参数]
*        例: @m.xota.xm1.msky130_fd_pr__nfet_01v8[region]
*  管型映射: M1,M2,M5,M7,Mref = nfet ; M3,M4,M6 = pfet
* ============================================================================

.include "models.inc"
.include "../03_sch/ota2_miller.sp"

.param VDDV = 1.8
.param VCMV = 0.9

VDD   vdd   0     dc {VDDV}
VINP  vinp  0     dc {VCMV}

* 单位增益缓冲: 端口1(vinm) 与 端口3(vout) 接同一节点
XOTA  vout vinp vout vdd 0 vbias  ota2_miller
XBIAS vbias vdd 0  bias_gen

CL    vout 0  2p

.control
op

echo ""
echo "=================================================================="
echo " 1) 饱和判据 Vds - (|Vgs|-|Vth|)  (V)   >= 0 才算饱和, 负值=线性区"
echo "    注: sky130 subckt 不暴露 region 参数, 用 Vds-Vov 判断等效"
echo "    顺序:      M1     M2     M3     M4     M5     M6     M7    Mref"
echo "------------------------------------------------------------------"
print (abs(@m.xota.xm1.msky130_fd_pr__nfet_01v8[vds])-(abs(@m.xota.xm1.msky130_fd_pr__nfet_01v8[vgs])-abs(@m.xota.xm1.msky130_fd_pr__nfet_01v8[vth]))) (abs(@m.xota.xm2.msky130_fd_pr__nfet_01v8[vds])-(abs(@m.xota.xm2.msky130_fd_pr__nfet_01v8[vgs])-abs(@m.xota.xm2.msky130_fd_pr__nfet_01v8[vth]))) (abs(@m.xota.xm3.msky130_fd_pr__pfet_01v8[vds])-(abs(@m.xota.xm3.msky130_fd_pr__pfet_01v8[vgs])-abs(@m.xota.xm3.msky130_fd_pr__pfet_01v8[vth]))) (abs(@m.xota.xm4.msky130_fd_pr__pfet_01v8[vds])-(abs(@m.xota.xm4.msky130_fd_pr__pfet_01v8[vgs])-abs(@m.xota.xm4.msky130_fd_pr__pfet_01v8[vth]))) (abs(@m.xota.xm5.msky130_fd_pr__nfet_01v8[vds])-(abs(@m.xota.xm5.msky130_fd_pr__nfet_01v8[vgs])-abs(@m.xota.xm5.msky130_fd_pr__nfet_01v8[vth]))) (abs(@m.xota.xm6.msky130_fd_pr__pfet_01v8[vds])-(abs(@m.xota.xm6.msky130_fd_pr__pfet_01v8[vgs])-abs(@m.xota.xm6.msky130_fd_pr__pfet_01v8[vth]))) (abs(@m.xota.xm7.msky130_fd_pr__nfet_01v8[vds])-(abs(@m.xota.xm7.msky130_fd_pr__nfet_01v8[vgs])-abs(@m.xota.xm7.msky130_fd_pr__nfet_01v8[vth]))) (abs(@m.xbias.xmref.msky130_fd_pr__nfet_01v8[vds])-(abs(@m.xbias.xmref.msky130_fd_pr__nfet_01v8[vgs])-abs(@m.xbias.xmref.msky130_fd_pr__nfet_01v8[vth])))

echo ""
echo "=================================================================="
echo " 2) 漏极电流 Id (uA)   期望: M1=M2=10  M3=M4=10  M5=20  M6=M7=50  Mref=10"
echo "    顺序:      M1     M2     M3     M4     M5     M6     M7    Mref"
echo "------------------------------------------------------------------"
print (@m.xota.xm1.msky130_fd_pr__nfet_01v8[id]*1e6) (@m.xota.xm2.msky130_fd_pr__nfet_01v8[id]*1e6) (@m.xota.xm3.msky130_fd_pr__pfet_01v8[id]*1e6) (@m.xota.xm4.msky130_fd_pr__pfet_01v8[id]*1e6) (@m.xota.xm5.msky130_fd_pr__nfet_01v8[id]*1e6) (@m.xota.xm6.msky130_fd_pr__pfet_01v8[id]*1e6) (@m.xota.xm7.msky130_fd_pr__nfet_01v8[id]*1e6) (@m.xbias.xmref.msky130_fd_pr__nfet_01v8[id]*1e6)

echo ""
echo "=================================================================="
echo " 3) 跨导 gm (uS)   手算期望: gm1~118  gm6~590  (M6 取56um时)"
echo "    顺序:      M1     M3     M6     M7"
echo "------------------------------------------------------------------"
print (@m.xota.xm1.msky130_fd_pr__nfet_01v8[gm]*1e6) (@m.xota.xm3.msky130_fd_pr__pfet_01v8[gm]*1e6) (@m.xota.xm6.msky130_fd_pr__pfet_01v8[gm]*1e6) (@m.xota.xm7.msky130_fd_pr__nfet_01v8[gm]*1e6)

echo ""
echo "=================================================================="
echo " 4) 过驱动电压 |Vgs|-|Vth| (V)   一般希望 >= 0.12V, 太小进亚阈"
echo "    顺序:      M1     M3     M5     M6     M7    Mref"
echo "------------------------------------------------------------------"
print (abs(@m.xota.xm1.msky130_fd_pr__nfet_01v8[vgs])-abs(@m.xota.xm1.msky130_fd_pr__nfet_01v8[vth])) (abs(@m.xota.xm3.msky130_fd_pr__pfet_01v8[vgs])-abs(@m.xota.xm3.msky130_fd_pr__pfet_01v8[vth])) (abs(@m.xota.xm5.msky130_fd_pr__nfet_01v8[vgs])-abs(@m.xota.xm5.msky130_fd_pr__nfet_01v8[vth])) (abs(@m.xota.xm6.msky130_fd_pr__pfet_01v8[vgs])-abs(@m.xota.xm6.msky130_fd_pr__pfet_01v8[vth])) (abs(@m.xota.xm7.msky130_fd_pr__nfet_01v8[vgs])-abs(@m.xota.xm7.msky130_fd_pr__nfet_01v8[vth])) (abs(@m.xbias.xmref.msky130_fd_pr__nfet_01v8[vgs])-abs(@m.xbias.xmref.msky130_fd_pr__nfet_01v8[vth]))

echo ""
echo "=================================================================="
echo " 5) 输出电阻 ro = 1/gds (MOhm) 与 本征增益 gm*ro"
echo "    顺序: ro_M2  ro_M4  ro_M6  ro_M7   |   gm*ro: M1  M6"
echo "------------------------------------------------------------------"
print (1/@m.xota.xm2.msky130_fd_pr__nfet_01v8[gds]/1e6) (1/@m.xota.xm4.msky130_fd_pr__pfet_01v8[gds]/1e6) (1/@m.xota.xm6.msky130_fd_pr__pfet_01v8[gds]/1e6) (1/@m.xota.xm7.msky130_fd_pr__nfet_01v8[gds]/1e6)
echo "----"
print (@m.xota.xm1.msky130_fd_pr__nfet_01v8[gm]/@m.xota.xm1.msky130_fd_pr__nfet_01v8[gds]) (@m.xota.xm6.msky130_fd_pr__pfet_01v8[gm]/@m.xota.xm6.msky130_fd_pr__pfet_01v8[gds])

echo ""
echo "=================================================================="
echo " 6) 关键节点电压 (V)"
echo "    vout   n1(M3漏)  n2(第一级输出/M6栅)  ntail(M5漏)  vbias"
echo "------------------------------------------------------------------"
print v(vout) v(xota.n1) v(xota.n2) v(xota.ntail) v(vbias)

echo ""
echo " 7) 总静态电流 (uA) 与 功耗 (uW)"
echo "------------------------------------------------------------------"
print ((@m.xota.xm5.msky130_fd_pr__nfet_01v8[id] + @m.xota.xm6.msky130_fd_pr__pfet_01v8[id] + @m.xbias.xmref.msky130_fd_pr__nfet_01v8[id]) * 1e6)
print ((@m.xota.xm5.msky130_fd_pr__nfet_01v8[id] + @m.xota.xm6.msky130_fd_pr__pfet_01v8[id] + @m.xbias.xmref.msky130_fd_pr__nfet_01v8[id]) * 1.8 * 1e6)

.endc

.end
