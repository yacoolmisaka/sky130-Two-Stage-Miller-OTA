* ============================================================================
*  models.inc —— 真 sky130 ngspice 模型 (volare 装的 c6d73a3... 版本)
*
*  用的是同一 PDK 版本 (c6d73a3...) 的**传统 ngspice 入口**:
*      .../sky130A/libs.tech/ngspice/sky130.lib.spice
*
*  为什么不用 combined/continuous:
*    那个库是给 Monte Carlo / 连续 corner 扫描用的, 参数里大量统计分布
*    表达式 (依赖 MC 开关). 在普通 tt 仿真下 MC 开关没置位, 会把 Dsub
*    算成负数 -> ngspice 报 "Fatal: Dsub is negative" 直接退出.
*    传统 ngspice 入口是确定性 corner 模型, 与 ngspice 兼容性最成熟.
*
*  corner 可选: tt / ff / ss / fs / sf / mc
*
*  ngspice 必须从 wrapper 所在目录运行 (里面全是相对路径 include),
*  run.sh 会自动 cd 进去.
* ============================================================================
.lib "/home/yacool/sky130_volare_pdk/volare/sky130/versions/c6d73a35f524070e85faff4a6a9eef49553ebc2b/sky130A/libs.tech/ngspice/sky130.lib.spice" tt

* ---- MC / mismatch 开关 (防御性) ----
* sky130 的统计模型里 mc_mm_switch / mm_switch 控制 Monte Carlo 与失配
* 分布。某些库版本在普通 tt 仿真下这两个量没被赋值, 会报
* "Undefined parameter"。显式置 0 = 关掉统计, 走确定性 tt。
* 注意: 必须写在 .lib 之后, ngspice 是后定义覆盖先定义。
.param mc_mm_switch=0
.param mm_switch=0

* ---- 备选 (做完 MC/多 corner 分析时再启用这行, 并注释上面那行) ----
* .lib "/home/yacool/sky130_volare_pdk/volare/sky130/versions/c6d73a35f524070e85faff4a6a9eef49553ebc2b/sky130A/libs.tech/combined/continuous/sky130.lib.spice" tt