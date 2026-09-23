* ============================================================================
*  TB4: 输入共模范围 ICMR (.dc 扫描)
*  接法: 单位增益缓冲, 输入共模从 0V 扫到 1.8V
*  判据: |vout - vinp| < 5mV 且尾管 M5 仍饱和 (Vds5 = v(ntail) > Vov5 ~0.15V)
*        的区间就是 ICMR
*  手算期望: 0.78V ~ 1.45V
* ============================================================================

.include "models.inc"
.include "../03_sch/ota2_miller.sp"

.param VDDV = 1.8

VDD   vdd  0  dc {VDDV}
VCM   vinp 0  dc 0.9

XOTA  vout vinp vout vdd 0 vbias  ota2_miller
XBIAS vbias vdd 0  bias_gen

CL    vout 0  2p

.dc VCM 0 1.8 0.005

.control
run

echo ""
echo "=================================================================="
echo " ICMR 扫描已完成, 数据写入 icmr.txt"
echo " 列:  vcm    vout    ntail(Vds5)    n1    n2"
echo "------------------------------------------------------------------"
echo " 判读:"
echo "   - vout 紧跟 vcm 的直线段 = 可用共模区间"
echo "   - v(ntail) 掉到 < 0.2V 说明尾管 M5 进入线性区 -> 共模下限到此为止"
echo "   - v(n1)/v(n2) 突然变化说明电流镜负载退出饱和 -> 共模上限到此为止"
echo "=================================================================="

let vcmv   = v(vinp)
let voutv  = v(vout)
let ntailv = v(xota.ntail)
let n1v    = v(xota.n1)
let n2v    = v(xota.n2)
wrdata icmr.txt vcmv voutv ntailv n1v n2v
echo " >> 运行 python3 icmr_report.py icmr.txt 自动给出上下限"
.endc

.end
