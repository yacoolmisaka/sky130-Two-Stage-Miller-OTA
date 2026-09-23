# =============================================================================
#  fix_top.tcl  ·  修复 ota2_miller 顶层（子 cell 不显示 / 垃圾实例 / Cc 缺失）
# -----------------------------------------------------------------------------
#  诊断结论（2026-09-17，直接读了 mag/ 下的 .mag 文件确认）：
#    · 8 个器件 cell 文件完好：几何 + gencell/library/parameters 属性齐全
#    · cap_mim_m3_1_PMLRN3.mag（Cc）也在，但顶层**没有实例化它**（孤儿文件）
#    · 顶层尾部有 4 条垃圾 use 记录（timestamp 0，指向不存在的 4VMFW9/4X5J3S/7UBMCX）
#      —— 就是那些 ✕ 框的来源
#    · 器件只显示成"带名字的空方框" = 子 cell 处于 **unexpanded（未展开）** 状态
#      → 解法就是 magic 的 `expand all`（官方 commandref 原文：expands all subcells
#        in the layout window）。快捷键：`x`=expand overlap，`Ctrl+X`=toggle。
#      ⚠️ 不是文件问题、也不是"没读进来" —— 之前那个判断是错的。
#
#  本脚本做五件事：
#    1) 逐个显式 load 8 个器件 cell
#    2) 回到顶层
#    3) 删掉 4 条垃圾实例
#    4) 把 Cc 补回来（放在 M6 右侧）
#    5) expand all —— 展开所有子 cell，让几何显示出来
#
#  用法：tkcon 里   source ../fix_top.tcl
#        跑完按 v 看全图，然后  save  +  writeall force
# =============================================================================

# ---------- 1. 显式读入 8 个器件 cell ----------
set devcells {
    sky130_fd_pr__pfet_01v8_8MY6K8
    sky130_fd_pr__pfet_01v8_8FHKLD
    sky130_fd_pr__nfet_01v8_7KZ2AN
    sky130_fd_pr__nfet_01v8_SND6KL
    sky130_fd_pr__nfet_01v8_9A3M24
    sky130_fd_pr__nfet_01v8_RNGHDB
    sky130_fd_pr__res_xhigh_po_0p69_96AYDP
}
puts "== 1) 显式读入器件 cell =="
foreach c $devcells {
    if {[catch {load $c} err]} {
        puts stderr "  !! load $c 失败: $err"
    } else {
        puts "  .. $c 已读入"
    }
}

# ---------- 2. 回到顶层 ----------
puts "== 2) 回到 ota2_miller =="
if {[catch {load ota2_miller} err]} {
    puts stderr "  !! $err"
} else {
    puts "  .. 顶层已加载"
}

# ---------- 3. 删掉 4 条垃圾实例 ----------
#   实例名直接取自 ota2_miller.mag 的 use 记录
puts "== 3) 清理垃圾实例 =="
foreach bad {
    sky130_fd_pr__nfet_01v8_4VMFW9_0
    sky130_fd_pr__nfet_01v8_4X5J3S_0
    sky130_fd_pr__nfet_01v8_7UBMCX_0
    sky130_fd_pr__nfet_01v8_7UBMCX_1
} {
    # 先确认实例真的存在，避免 select 落到顶层把版图删了
    if {[instance list celldef $bad] eq ""} {
        puts "  .. $bad 不存在，跳过"
        continue
    }
    if {[catch {select cell $bad} err]} {
        puts stderr "  !! $bad 选不中: $err"
        continue
    }
    if {[catch {delete} err]} {
        puts stderr "  !! $bad 删除失败: $err"
    } else {
        puts "  .. $bad 已删除"
    }
}

# ---------- 4. 补回 Cc ----------
#   M6 在 x≈6659（internal），半宽 3779 → 右边缘 ≈10438
#   放到 x=13000，竖直居中在 y≈0（Cc 自身半高 2470）
puts "== 4) 补回 Cc =="
select top cell
if {[instance list celldef Cc] ne ""} {
    puts "  .. Cc 已存在，跳过"
} else {
    box 13000 -2470 13100 -2370
    if {[catch {getcell sky130_fd_pr__cap_mim_m3_1_PMLRN3} err]} {
        puts stderr "  !! Cc 例化失败: $err"
    } else {
        catch {identify Cc}
        puts "  .. Cc 已补回（放在 M6 右侧）"
    }
}

# ---------- 5. 展开所有子 cell（关键！否则只显示外框不显示几何）----------
puts "== 5) expand all =="
if {[catch {expand all} err]} {
    puts stderr "  !! expand all 失败: $err"
} else {
    puts "  .. 已展开全部子 cell"
}

# ---------- 收尾 ----------
select top cell
puts "==================================================="
puts "完成。当前顶层实例清单："
foreach i {M1 M2 M3 M4 M5 M6 M7 Mref Rz Cc} {
    set cd [instance list celldef $i]
    if {$cd ne ""} { puts "  $i -> $cd" } else { puts "  $i -> !! 缺失" }
}
puts "---------------------------------------------------"
puts "接着做："
puts "  1) 按 v 看全图，确认器件里有几何（条纹），不是空框"
puts "     （还是空框就再敲一次 expand all）"
puts "  2) save"
puts "  3) writeall force"
puts "==================================================="
