# =============================================================================
#  floorplan_v1.tcl  ·  骨架排布（把 10 颗器件按信号流排成三行）
# -----------------------------------------------------------------------------
#  目标结构（从上到下）：
#
#     ══════════════ VDD 轨（met1 宽条，后面画）══════════════
#        [M3][M4]        [M6]            ← PMOS 区（源/体接 VDD）
#        [Rz]   [Cc]                     ← 无源区（n2 → vout 补偿通路）
#     [Mref][M5][M1][M2]   [M7]          ← NMOS 区（源/体接 GND）
#     ══════════════ GND 轨（met1 宽条，后面画）══════════════
#
#  排布理由：
#   · M3/M4 相邻     → 电流镜匹配 + 栅极总线 n1 最短
#   · M6 靠右        → 与 M7 上下相对，vout 短路相连
#   · M1/M2 相邻     → 差分对匹配（第一版先不做共质心拆分）
#   · M5 在 M1/M2 左 → 尾电流注入 ntail 短
#   · Mref 在最左    → 与 M5/M7 共享 vbias 总线
#   · Cc/Rz 在中间   → n2（M2/M4 漏 → M6 栅）高阻走线最短
#
#  用法：tkcon 里   source ../floorplan_v1.tcl
# =============================================================================

select top cell

# 把一行器件从 x 起点依次往右排；返回本行排完后的 x
# y / gap / 返回值都是 magic 内部单位（1 µm = 200 internal）
proc layout_row {y insts gap} {
    set x 2000
    foreach inst $insts {
        if {[catch {select cell $inst} err]} {
            puts "!! $inst 选不中（$err），跳过"
            continue
        }
        # 读实例包围盒，拿真实宽度
        set w 4000
        catch {
            set b [instance list abutment]
            if {[llength $b] == 4} {
                set w [expr {[lindex $b 2] - [lindex $b 0]}]
            }
        }
        if {$w <= 0} { set w 4000 }
        # 把选中实例的左下角搬到 (x, y)
        box $x $y [expr {$x + 100}] [expr {$y + 100}]
        move
        puts [format "  %-5s x=%-7d 宽=%-6d (≈%.1f µm)" $inst $x $w [expr {$w / 200.0}]]
        set x [expr {$x + $w + $gap}]
    }
    return $x
}

puts "== Row 1 · PMOS 区（靠 VDD）=="
layout_row 16000 {M3 M4 M6} 1000

puts "== Row 2 · 无源区 =="
layout_row  8000 {Rz Cc} 2000

puts "== Row 3 · NMOS 区（靠 GND）=="
layout_row     0 {Mref M5 M1 M2 M7} 1000

select top cell
puts "==================================================="
puts "骨架完成。按 v 看全图。"
puts "下一步：画 VDD / GND 电源轨（met1 宽条）→ 连线 → label"
puts "⚠️ 存盘：save + writeall"
puts "==================================================="
