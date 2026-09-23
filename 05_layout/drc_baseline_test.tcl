# =============================================================================
#  drc_baseline_test.tcl  (v2)  --  用 getcell 放裸器件，跑 DRC 基线
# -----------------------------------------------------------------------------
#  v1 的问题：magic::gencell 会去找参数对话框 (.params.title.ient)，在新 cell 里报错
#  v2 改用 getcell 直接复用磁盘上已有的器件 cell（ota2_miller 用的那颗）
#
#  用法：
#     load drc_test                       ← 先切到测试 cell
#     source ../drc_baseline_test.tcl
#     跑完看数字，再  load ota2_miller 回来
# =============================================================================

puts "======================================================"
puts " 对照实验 v2：裸器件 DRC 基线"
puts "======================================================"

# 确认在哪个 cell
if {[catch {set cur [cellname self]}]} { set cur "?" }
puts "  当前编辑 cell = $cur"
puts "  （必须是 drc_test。如果不是，先执行 load drc_test）"

# ---- 清掉可能残留的实例 ----
catch {select top cell}
catch {box 0 0 1000 1000}
catch {erase $}

# ---- 放一个 M5 同参数的裸器件（复用已有的 cell 文件）----
puts "  放置裸器件（复用 SND6KL = M5 同参数 W24/L1/nf12）..."
if {[catch {
    select top cell
    box 0 0 100 100
    getcell sky130_fd_pr__nfet_01v8_SND6KL
} err]} {
    puts "!! getcell 失败: $err"
    return
}
puts "  放置完成"

# ---- 展开 + 跑 DRC ----
catch {select top cell}
if {[catch {expand all} e2]} { puts "expand: $e2" }
catch {drc check}
catch {drc catchup}
catch {drc count}

puts "======================================================"
puts " ★ 记下上面 drc count 的第一个数字（裸器件的错误数）"
puts " ★ 然后回主 cell：  load ota2_miller"
puts "======================================================"
