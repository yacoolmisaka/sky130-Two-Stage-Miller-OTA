* ============================================================================
*  exp_w.sp —— 判别 sky130 subckt 的 W 语义 (只留 A1 / A3 两条有效路径)
*
*  之前 A2(w=10) 与 A4(w=56) 都触发了 BSIM4 运行时参数校验 fatal:
*    Fatal: Pclm = -0.14  is not positive.
*    Fatal: Drout = -0.56  is negative.
*    Warning: Eta0 = -0.21 is negative.
*  这些都是 w>=10 时 bin 5 的"at current temperature"运行时负值,
*  sed 翻正也来不及(参数是算出来的不是写死的). 结论: w 直写路线排除.
*
*  现在只剩 A1 (w=2, 基准) vs A3 (w=2, m=5 倍增), 用同一 w 单纯验证 m= 倍增
*  能否让 Id 等比放大 5 倍. 若 A3/A1 ≈ 5 -> m= 路线可用, OP 网表改用 m= 即可.
* ============================================================================

.include "models.inc"

.param VGV = 1.2

VG   g   0   dc {VGV}
VDA  da  0   dc 1.0
VDC  dcx 0   dc 1.0

XA1  da  g 0 0  sky130_fd_pr__nfet_01v8  l=1 w=2   nf=5
XA3  dcx g 0 0  sky130_fd_pr__nfet_01v8  l=1 w=2   nf=5  m=5

.control
op
echo ""
echo "=================================================================="
echo " Vgs=1.2V, Vds=1.0V (饱和), L=1um, 全 nfet_01v8"
echo "   A1: w=2  nf=5        (基准, 应该 5.27uA 左右)"
echo "   A3: w=2  nf=5  m=5   (m= 倍增, 若 Id~5xA1 -> m= 路线可用)"
echo "------------------------------------------------------------------"
print (i(VDA)*1e6) (i(VDC)*1e6)
echo "---- A1 / A3 的 Id 比值 (期望 5) ----"
let ratio = i(VDC)/i(VDA)
print ratio
echo "---- 各管 Vov (V) ----"
print (abs(@m.xa1.msky130_fd_pr__nfet_01v8[vgs])-abs(@m.xa1.msky130_fd_pr__nfet_01v8[vth])) (abs(@m.xa3.msky130_fd_pr__nfet_01v8[vgs])-abs(@m.xa3.msky130_fd_pr__nfet_01v8[vth]))
.endc

.end
