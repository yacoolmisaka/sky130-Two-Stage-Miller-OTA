# =============================================================================
#  exp_geom.tcl  ·  参数扫描实验：让源漏岛焊盘 m1 宽度 >= 0.31um
# -----------------------------------------------------------------------------
#  背景（详见 M5-M7多指管LVS阻塞根因终局报告.md）：
#    gencell 生成的器件，源漏接触的 m1 只包了 0.03um，
#    岛焊盘总宽仅 0.23um < via1 所需的 0.31um
#    -> 顶层打不下过孔、也铺不开 metal1 走线 -> 各指源漏无法并联 -> LVS 卡死。
#
#  本实验利用 sky130.tcl 的传参机制（已从源码验证）：
#
#     sky130::sky130_fd_pr__nfet_01v8_draw {parameters}
#         set drawdict [dict merge $sky130::ruleset $newdict $parameters]
#                                                            ^^^^^^^^^^^
#                                                      优先级最高，可覆盖一切
#
#     sky130::mos_convert {parameters}
#         default { dict set pdkparams $key $value }   # 未识别参数原样透传
#
#  所以 gate_to_diffcont / diff_extension / contact_size 都能传进去并生效。
#
#  这些参数在 ruleset 里的默认值（sky130.tcl 第 60~67 行）：
#     diff_surround      0.06    ;# 扩散包围接触
#     gate_to_diffcont   0.145   ;# 栅极到源漏接触【中心】的距离
#     gate_to_polycont   0.275   ;# 栅极到 poly 接触中心距离
#     diff_extension     0.29    ;# 扩散超出栅极
#     contact_size       0.17    ;# 接触最小尺寸
#     metal_surround     0.08    ;# (ruleset 值，器件里实际用 0.03)
#
#  参考：varactor 用的是 gate_to_diffcont 0.34 / diff_extension 0.485，
#        证明这些参数确实可以在 draw 层面覆盖。
#
#  用法（magic 的 tkcon 里，工作目录 = 05_layout/mag）：
#      source ../exp_geom.tcl
#      save exp_geom
#
#  然后用 Windows 侧脚本量几何：
#      python 05_layout/_probe_geom.py --exp
# =============================================================================

# ---- 0. 工具：安全读 cell property ------------------------------------------
proc cprop {cell p} {
    set v ""
    catch {set v [cellname list property $cell $p]}
    return $v
}

# ---- 1. 找 PDK gencell 命名空间（与 gen_devices.tcl 同一套逻辑）-------------
proc find_lib {} {
    foreach c [cellname list children] {
        set l [cprop $c library]
        if {$l ne "" && $l ne "toolkit"} { return $l }
    }
    foreach ns [namespace children ::] {
        set n [string trimleft $ns :]
        if {[namespace eval $ns info commands *nfet_01v8_convert] ne ""} { return $n }
    }
    return ""
}

set ::SKYLIB [find_lib]
if {$::SKYLIB eq ""} {
    puts stderr "==========================================================="
    puts stderr "  找不到 PDK 生成器命名空间。"
    puts stderr "  请在 tkcon 里执行:  namespace children ::"
    puts stderr "  把结果发我。"
    puts stderr "==========================================================="
    error "no PDK gencell library found"
}
puts "== 使用 library: $::SKYLIB =="

# ---- 2. 清理旧实验 cell，避免 'already exists' ------------------------------
foreach n {expE0 expE1 expE2 expE3 expE4 expE5 expE6} {
    catch {cellname delete $n}
}
puts "== 已清理旧实验 cell =="

# ---- 3. 生成单个实验管 -------------------------------------------------------
# 全部用 nf=2（2 指 3 岛），几何最简单、对比最直观。
# W 固定 4um，单指宽 = 2.0um，与 M1/M5/M6 的单指宽一致。
set ::RESULTS [list]

proc try_gen {name paramlist} {
    puts ""
    puts "  -----------------------------------------------------------"
    puts "  实验 $name"
    puts "     参数: $paramlist"
    puts "  -----------------------------------------------------------"

    if {[catch {magic::gencell ${::SKYLIB}::sky130_fd_pr__nfet_01v8 \
                    $name -spice {*}$paramlist} err]} {
        puts stderr "     !! 生成失败: $err"
        lappend ::RESULTS [list $name "FAILED" $err]
        return ""
    }
    set cd [instance list celldef $name]
    puts "     -> cell = $cd"
    puts "     (接下来请 save，然后回 Windows 用脚本量几何)"
    lappend ::RESULTS [list $name "OK" $cd]
    return $cd
}

puts ""
puts "==============================================================="
puts "  开始参数扫描（每个 cell 用 nf=2）"
puts "==============================================================="

# E0 · 基准组（完全照原配置，等价于 M1/M2）
try_gen expE0 {W 4 L 1 nf 2}

# E1 · 只加大「栅极到源漏接触距离」—— 核心假设
try_gen expE1 {W 4 L 1 nf 2 gate_to_diffcont 0.30}

# E2 · 栅极距离 + 扩散延伸一起加大
try_gen expE2 {W 4 L 1 nf 2 gate_to_diffcont 0.30 diff_extension 0.45}

# E3 · 再加大一档
try_gen expE3 {W 4 L 1 nf 2 gate_to_diffcont 0.45 diff_extension 0.60}

# E4 · 只加大接触尺寸（看 gencell 是否接受 contact_size 覆盖）
try_gen expE4 {W 4 L 1 nf 2 contact_size 0.31}

# E5 · 组合拳
try_gen expE5 {W 4 L 1 nf 2 gate_to_diffcont 0.40 diff_extension 0.55 contact_size 0.31}

# E6 · 试 conn_gates 1（看能否顺便解决栅极断连）
try_gen expE6 {W 4 L 1 nf 2 conn_gates 1}

# ---- 4. 汇总 ----------------------------------------------------------------
puts ""
puts "==============================================================="
puts "  实验完成 — 结果汇总"
puts "==============================================================="
foreach r $::RESULTS {
    set name [lindex $r 0]
    set st   [lindex $r 1]
    set cd   [lindex $r 2]
    if {$st eq "OK"} {
        puts [format "  %-8s   ✔  %s" $name $cd]
    } else {
        puts [format "  %-8s   ✗  %s" $name $cd]
    }
}
puts "---------------------------------------------------------------"
puts "  下一步："
puts "    1) 在 tkcon 执行:   save exp_geom"
puts "       （若报 name already exists，用  save exp_geom2）"
puts "    2) 告诉我跑完了，我用量几何脚本对比 7 个 cell 的"
puts "       【源漏岛 m1 宽度】，找出 >= 0.31um 的参数组合。"
puts "==============================================================="
