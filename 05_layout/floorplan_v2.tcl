# =============================================================================
#  floorplan_v2.tcl  ·  按「模块」重排（M3/M4 在 M1/M2 头上）
# -----------------------------------------------------------------------------
#  目标骨架（左 → 右）：
#
#      ┌ 模块 A：第一级 ────────┐  ┌ 模块 B：偏置 ──┐  ┌ 模块 C：第二级 ──┐
#      │  [M3]  [M4]   PMOS     │  │                │  │  [M6]   PMOS     │
#      │  [M1]  [M2]   NMOS     │  │ [M5]  [Mref]   │  │  [M7]   NMOS     │
#      └────────────────────────┘  └────────────────┘  └──────────────────┘
#                                                        [Cc]          [Rz]
#
#  为什么这么摆（每一条都能在面试里说）：
#   · M3 压在 M1 上 →  n1 = M1.D+M3.D+M3.G 是**垂直**连线，极短
#   · M4 压在 M2 上 →  n2 = M2.D+M4.D 同理（且 n2 是高阻节点，越短越好）
#   · M1/M2 水平相邻 → 差分对匹配，同取向同环境
#   · M3/M4 水平相邻 → 电流镜匹配
#   · M5 + Mref 一组 → 都在 vbias/ntail 这条偏置链上，放一起便于走偏置总线
#   · M6 压在 M7 上 →  两管漏极 = vout，垂直直连
#   · Cc / Rz 放最右 → 补偿通路（n2 → Cc → vout）在模块 A 与模块 C 之间，走线短
#
#  前提：先在 ota2_miller 顶层，且**已经 save + writeall**（出错可回退）
#  用法：tkcon 里   source ../floorplan_v2.tcl
# =============================================================================

# ---------- 单位换算：本 PDK 1 µm = 200 internal ----------
proc um {v} { return [expr {int(round($v * 200.0))}] }

set Y_NM [um 10]        ;# NMOS 行基线（下）
set Y_PM [um 26]        ;# PMOS 行基线（上）
set GAP  [um 2]         ;# 同模块内器件水平间隙
set BLK  [um 20]        ;# 模块之间间隔
set WMIN [um 8]         ;# 量不到宽度时的保守值

# ---------- 量一个实例的真实宽度（internal 单位）----------
proc iwidth {inst} {
    set w 0
    catch {
        select cell $inst
        set b [instance list abutment]
        if {[llength $b] == 4} {
            set w [expr {[lindex $b 2] - [lindex $b 0]}]
        }
    }
    if {$w < 200} { set w $::WMIN }
    return $w
}

# ---------- 把某个实例搬到 (x, y)：删掉旧例化 → 在新位置重新 getcell ----------
#   用 getcell 而不是 move：getcell「把 cell 左下角放到光标框左下角」的行为
#   已经在本项目里被验证过（10 颗器件当初就是这么精确落到原点的）。
proc place_at {inst x y} {
    set cd [instance list celldef $inst]
    if {$cd eq ""} { puts "!! $inst 不存在，跳过"; return }
    if {[catch {select cell $inst}]} { puts "!! $inst 选不中，跳过"; return }
    delete
    box $x $y [expr {$x + 100}] [expr {$y + 100}]
    getcell $cd
    catch {identify $inst}
    puts [format "  %-5s ->  x=%6.1f µm,  y=%6.1f µm" $inst [expr {$x/200.0}] [expr {$y/200.0}]]
}

# ======================= 开始摆放 =======================
select top cell
puts "== 模块 A：M1/M2（下）+ M3/M4（上）=="

set xa [um 10]
place_at M1 $xa $Y_NM
set xb [expr {$xa + [iwidth M1] + $GAP}]
place_at M2 $xb $Y_NM
place_at M3 $xa $Y_PM
place_at M4 $xb $Y_PM

puts "== 模块 B：M5 + Mref =="
set xc [expr {$xb + [iwidth M2] + $BLK}]
place_at M5 $xc $Y_NM
set xd [expr {$xc + [iwidth M5] + $GAP}]
place_at Mref $xd $Y_NM

puts "== 模块 C：M7（下）+ M6（上）=="
set xe [expr {$xd + [iwidth Mref] + $BLK}]
place_at M7 $xe $Y_NM
place_at M6 $xe $Y_PM

puts "== 无源：Cc + Rz =="
set xf [expr {$xe + [iwidth M6] + $BLK}]
place_at Cc $xf $Y_PM
place_at Rz $xf $Y_NM

# ======================= 收尾 =======================
select top cell
puts "==================================================="
puts "排布完成。按 v 看全图。"
puts "检查三件事："
puts "  1) M3 在 M1 正上方、M4 在 M2 正上方（垂直对齐）"
puts "  2) M6 在 M7 正上方"
puts "  3) 各模块之间没重叠"
puts "⚠️ 存盘： save  +  writeall force"
puts "==================================================="
