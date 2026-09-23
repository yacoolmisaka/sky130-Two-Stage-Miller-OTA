#!/usr/bin/env bash
# ==============================================================================
#  run_postsim.sh  ——  在 WSL 终端执行：bash run_postsim.sh
# ------------------------------------------------------------------------------
#  后仿一键：清洗 magic 导出的网表 -> ngspice 跑开环 AC -> 打印结果摘要
#
#  前置：已在 magic 里 source 05_layout/run_pext.tcl 生成
#        05_layout/mag/ota2_miller_pext.spice
#
#  为什么要"清洗"这一步：
#    magic 会在某些寄生电容行尾写 "**FLOATING" 标记。
#    spice 语法里只有【行首】的 * 才是注释；行尾的 * 会被 ngspice 当成多余参数，
#    直接报 "unknown parameter (*)" 并中断仿真。必须先剥掉。
# ==============================================================================
set -uo pipefail

PROJ="/mnt/d/WorkBuddy/workspace/sky130 Two-Stage Miller OTA"
SIM="$PROJ/04_sim"
PEXT="$PROJ/05_layout/mag/ota2_miller_pext.spice"
CLEAN="$SIM/ota2_pext_clean.spice"

cd "$SIM" || { echo "!! 目录不存在: $SIM"; exit 1; }

if [ ! -f "$PEXT" ]; then
    echo "!! 找不到含寄生网表: $PEXT"
    echo "   -> 请先在【新开的 magic 会话】里执行:"
    echo "      source \"$PROJ/05_layout/run_pext.tcl\""
    exit 1
fi
command -v ngspice >/dev/null 2>&1 || { echo "!! 找不到 ngspice"; exit 1; }

# --- 1. 剥掉行尾的 **FLOATING 标记 -------------------------------------------
n_mark=$(grep -c 'FLOATING' "$PEXT" || true)
sed 's/[[:space:]]*\*\*FLOATING[[:space:]]*$//' "$PEXT" > "$CLEAN"
n_left=$(grep -c 'FLOATING' "$CLEAN" || true)

# --- 1b. 给浮空节点补 DC 通路 -------------------------------------------------
#  magic 会提取出悬空金属岛(只连寄生电容、没接任何器件)并单列成一个节点，
#  这类节点没有 DC 通路 -> "singular matrix" -> gmin/source stepping 全失败，
#  DC 工作点出不来，后面 AC 全是假的(曾出现 av0=-157dB)。
python3 "$SIM/fix_float.py" "$CLEAN"

echo "pext   : $PEXT ($(stat -c%s "$PEXT") bytes)"
echo "clean  : $CLEAN   (剥掉 $n_mark 处 FLOATING，残留 $n_left)"
echo

# --- 2. 跑后仿 AC -------------------------------------------------------------
echo "=================== ngspice 后仿 AC ==================="
ngspice -b tb_ac_post.sp 2>&1 | tee /tmp/postsim.log

# --- 3. 结果摘要 --------------------------------------------------------------
echo
echo "=================== 与前仿基线对比 ==================="
echo "  基线(前仿/原理图): av0=72.65dB   gbw=10.39MHz   pm=63.28deg"
echo "------------------------------------------------------"
grep -E 'av0|gbw|pm_at|=' /tmp/postsim.log | grep -iE 'av0|gbw|pm_at' | head -10
echo
echo "曲线数据: $SIM/ac_bode_post.txt (可用 plot_bode.py 与 ac_bode_sch.txt 叠加)"
