# =============================================================================
#  li_bundle.tcl · 多指管源漏/栅极 li 捆扎重布线  (v2 · lambda 单位修正版)
# -----------------------------------------------------------------------------
#  v1 教训：
#    1. puts 里写了 [1/5] -> Tcl 当成命令替换，中断
#    2. box 命令坐标单位是 lambda (1 lambda = 0.01um = 2 internal units)
#       v1 误用 internal units，坐标放大了 2 倍
#
#  本版：全部坐标 = lambda（0.5 的整数倍，box 接受 .5 浮点）
#
#  原理（坐标经实测 + DRC 规则核算）：
#   - 扩散(ndiff)是连续整片；li 压扩散自动成 ndc 接触 -> 新 li 即可连岛
#   - li 横穿栅极 poly 上方不接触（不同层无间距规则）
#   - D 岛(偶位)竖条向上引、S 岛(奇位)向下引，各一条横线并联全部源/漏
#   - 栅极每指竖线(li+mcon+m1)引到顶部 m1 走廊并联，右伸引出
#   - D/S/栅 各留一根 m1 引出线（右侧），供顶层连接
#
#  间距自查（li 宽/间距 17；m1 宽 14/间距 14；mcon 17；单位 lambda）：
#    D横线(18..85) vs S横线(-85..-18)：36  ✔
#    D竖条(0..ye) vs S横线(顶-18)：    18  ✔
#    D/S横线 vs 栅pc环li(pc0)：        >=34 ✔
#    栅竖线顶(pc1+17) vs 保护环顶li：  34  ✔（卡线，同 gencell 原布局）
#    m1栅走廊(pc1+19) vs pc环m1顶：    16  ✔ (>=14)
#    m1 引出线 D(40..63)/S(-63..-40)/G(pc1+19..) 互不重叠 ✔
#
#  备份：mag/bak_li_bundle/（原始文件，可随时回滚）
#
#  用法（magic tkcon）：  source ../li_bundle.tcl
# =============================================================================

set DEVICES {
    {sky130_fd_pr__nfet_01v8_SND6KL  13 129 -774   102 119 136  831}
    {sky130_fd_pr__pfet_01v8_8MY6K8  29 129 -1806  102 123.5 140.5 1863}
    {sky130_fd_pr__nfet_01v8_9A3M24  26 129 -1612.5 127 144 161 1669.5}
    {sky130_fd_pr__nfet_01v8_RNGHDB   6 129 -322.5 127 144 161  379.5}
}
# 列: cellname  n_islands  pitch  x0(最左岛中心,lambda)  yext  pc0  pc1  bbox右沿

foreach d $DEVICES {
    set cell [lindex $d 0]
    set n    [lindex $d 1]
    set pit  [lindex $d 2]
    set x0   [lindex $d 3]
    set ye   [lindex $d 4]
    set pc0  [lindex $d 5]
    set pc1  [lindex $d 6]
    set bbR  [lindex $d 7]
    set nf   [expr {$n - 1}]
    set xout [expr {$bbR + 50}]

    puts "==================================================================="
    puts "  $cell : n=$n nf=$nf ye=$ye pc=$pc0..$pc1 xout=$xout"
    puts "==================================================================="

    load $cell

    # ---- 1) 擦掉原岛区 li / mcon / m1（栅环 pc0 以上不受影响）------------
    for {set k 0} {$k < $n} {incr k} {
        set xc [expr {$x0 + $k*$pit}]
        box [expr {$xc-12}] [expr {-$ye-2}] [expr {$xc+12}] [expr {$ye+2}]
        erase locali
        erase mcon
        erase metal1
    }
    puts "  Step1 原岛区已擦除 ($n 个)"

    # ---- 2) 重画竖条：偶数岛(D)向上、奇数岛(S)向下 -----------------------
    for {set k 0} {$k < $n} {incr k} {
        set xc [expr {$x0 + $k*$pit}]
        if {$k % 2 == 0} {
            box [expr {$xc-8.5}] 0 [expr {$xc+8.5}] $ye
        } else {
            box [expr {$xc-8.5}] [expr {-$ye}] [expr {$xc+8.5}] 0
        }
        paint locali
    }
    puts "  Step2 D/S 竖条已重画"

    # ---- 3) 两条横向捆扎线 -----------------------------------------------
    set xl [expr {$x0 - 8.5}]
    set xr [expr {$x0 + ($n-1)*$pit + 8.5}]
    box $xl 18 $xr 85
    paint locali
    box $xl -85 $xr -18
    paint locali
    puts "  Step3 D/S 横向捆扎线已画"

    # ---- 4) D/S 的 mcon + m1 引出线（右伸）--------------------------------
    set kd [expr {($n-1) % 2 == 0 ? $n-1 : $n-2}]
    set ks [expr {($n-1) % 2 == 1 ? $n-1 : $n-2}]
    set xd [expr {$x0 + $kd*$pit}]
    set xs [expr {$x0 + $ks*$pit}]

    box [expr {$xd-8.5}] 43 [expr {$xd+8.5}] 60
    paint mcon
    box [expr {$xs-8.5}] -60 [expr {$xs+8.5}] -43
    paint mcon
    box [expr {$xd-11.5}] 40 $xout 63
    paint metal1
    box [expr {$xs-11.5}] -63 $xout -40
    paint metal1
    puts "  Step4 D/S 孔+引出完成 (D@$xd S@$xs)"

    # ---- 5) 栅极：每指竖线 + 孔 + m1，顶部走廊并联 + 引出 ------------------
    for {set k 0} {$k < $nf} {incr k} {
        set xp [expr {$x0 + 64.5 + $k*$pit}]
        box [expr {$xp-8.5}] $pc0 [expr {$xp+8.5}] [expr {$pc1+17}]
        paint locali
        box [expr {$xp-8.5}] $pc1 [expr {$xp+8.5}] [expr {$pc1+17}]
        paint mcon
        box [expr {$xp-11.5}] $pc1 [expr {$xp+11.5}] [expr {$pc1+42}]
        paint metal1
    }
    set xpl [expr {$x0 + 64.5 + ($nf-1)*$pit}]
    box [expr {$xpl-11.5}] [expr {$pc1+19}] $xout [expr {$pc1+42}]
    paint metal1
    puts "  Step5 栅极 $nf 根竖线 + 走廊 + 引出完成"

    save
    puts "  >>>>> $cell 已保存"
    puts ""
}

puts "==================================================================="
puts "  全部完成！4 个 cell 已重布线并保存。"
puts "  下一步: load ota2_miller 切回主版图"
puts "==================================================================="
