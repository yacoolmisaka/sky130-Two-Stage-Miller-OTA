# =============================================================================
#  gen_devices.tcl  ·  sky130 两级 Miller OTA —— 一次性生成全部器件
# -----------------------------------------------------------------------------
#  原理：Devices1 / Devices2 菜单按钮背后就是 magic::gencell，
#        所以可以绕过对话框直接用脚本生成。
#
#        magic::gencell <library>::<gencell_type> <实例名> -spice <参数...>
#          -spice 表示参数用 SPICE 网表的名字（W / L / nf），magic 会自己转换。
#
#  用法：在 Magic 的 tkcon 控制台里执行
#            source ../gen_devices.tcl        （magic 从 05_layout/mag 启动时）
#
#  生成结果：10 个实例，名字固定为 M1 M2 M3 M4 M5 M6 M7 Mref Rz Cc
#
#  v2 修复（2026-09-16）：
#    1) $::SKYLIB::$dev 会被 Tcl 解析成变量 "::SKYLIB::"（尾部 :: 被吞进变量名）
#       → 改成 ${::SKYLIB}::$dev
#    2) cellname list property 对不存在的 property 会直接抛错
#       "Property name "library" is not defined" → 全部包 catch
# =============================================================================

# -----------------------------------------------------------------------------
# 0. 安全读 cell property（property 不存在时 magic 会直接抛错，必须 catch）
# -----------------------------------------------------------------------------
proc cprop {cell p} {
    set v ""
    catch {set v [cellname list property $cell $p]}
    return $v
}

# -----------------------------------------------------------------------------
# 1. 自动探测 PDK 生成器所在的命名空间（library）
# -----------------------------------------------------------------------------
proc find_lib {} {
    # (a) 从已经生成过的器件 cell 里读（cell 上记着 library property）
    foreach c [cellname list children] {
        set l [cprop $c library]
        if {$l ne "" && $l ne "toolkit"} { return $l }
    }
    # (b) 退路：扫命名空间，找带 nfet_01v8 生成器的那个
    foreach ns [namespace children ::] {
        set n [string trimleft $ns :]
        if {[namespace eval $ns info commands *nfet_01v8_convert] ne ""} { return $n }
    }
    return ""
}

set ::SKYLIB [find_lib]
if {$::SKYLIB eq ""} {
    puts stderr "==================================================="
    puts stderr "找不到 PDK 生成器命名空间。"
    puts stderr "请在 tkcon 里执行   namespace children ::   把结果发我。"
    puts stderr "==================================================="
    error "no PDK gencell library found"
}
puts "== 使用 library: $::SKYLIB =="

# -----------------------------------------------------------------------------
# 2. 生成辅助
# -----------------------------------------------------------------------------
set ::CELLMAP [dict create]

proc gen {inst dev a} {
    puts ".. 生成 $inst  ($dev)"
    if {[catch {magic::gencell ${::SKYLIB}::$dev $inst -spice {*}$a} err]} {
        puts stderr "!! $inst 生成失败: $err"
        puts stderr "   （若报 No import routine → library 命名空间不对，跑 namespace children :: 把结果发我；"
        puts stderr "     若报其它错 → 把完整报错发我）"
        return
    }
    dict set ::CELLMAP $inst [instance list celldef $inst]
    puts "     -> cell = [dict get $::CELLMAP $inst]"
}

# 复用已生成的同尺寸 cell（避免对同名 cell 重复 create）
proc dup {inst src} {
    if {![dict exists $::CELLMAP $src]} {
        puts stderr "!! $inst 无法复制：$src 不存在"
        return
    }
    set cd [dict get $::CELLMAP $src]
    puts ".. 生成 $inst  = 复用 $src 的 cell ($cd)"
    select top cell
    box 0 0 1 1
    getcell $cd
    catch {identify $inst}
    dict set ::CELLMAP $inst [instance list celldef $inst]
}

# -----------------------------------------------------------------------------
# 3. 按网表 03_sch/ota2_miller.spice 的尺寸生成
#    （W = 总宽，不是单指宽；单指宽 = W/nf）
# -----------------------------------------------------------------------------
select top cell

# --- 第一级 + 偏置 ---
gen M1   sky130_fd_pr__nfet_01v8 {W 4    L 1 nf 2}     ;# 差分输入对
dup M2   M1                                            ;# 同尺寸
gen M5   sky130_fd_pr__nfet_01v8 {W 24   L 1 nf 12}    ;# 尾电流源
gen M7   sky130_fd_pr__nfet_01v8 {W 62.5 L 1 nf 25}    ;# 第二级电流源负载
gen Mref sky130_fd_pr__nfet_01v8 {W 12.5 L 1 nf 5}     ;# 偏置基准

# --- PMOS ---
gen M3   sky130_fd_pr__pfet_01v8 {W 4    L 1 nf 2}     ;# 镜像负载（二极管）
dup M4   M3                                            ;# 同尺寸
gen M6   sky130_fd_pr__pfet_01v8 {W 56   L 1 nf 28}    ;# 第二级增益管

# --- 无源器件 ---
gen Rz   sky130_fd_pr__res_xhigh_po_0p69 {L 1.035}     ;# ≈3 kΩ（W 固定 0.69）
gen Cc   sky130_fd_pr__cap_mim_m3_1 {W 24.3 L 24.3}    ;# ≈1.2 pF

# -----------------------------------------------------------------------------
# 4. 收尾
# -----------------------------------------------------------------------------
select top cell
puts "==================================================="
puts "完成。实例清单："
foreach i {M1 M2 M3 M4 M5 M6 M7 Mref Rz Cc} {
    set cd [instance list celldef $i]
    if {$cd ne ""} { puts "  $i -> $cd" }
}
puts "---------------------------------------------------"
puts "下一步：摆位。用  select cell M5  按名字选中某颗，"
puts "        再把光标框移到目标位置按 m。"
puts "        ⚠️ 别忘了 save + writeall（未命名的话先 save ota2_miller）"
puts "==================================================="
