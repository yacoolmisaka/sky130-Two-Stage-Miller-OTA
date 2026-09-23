#!/usr/bin/env bash
# ==============================================================================
#  run_drc.sh  ——  在 WSL 终端执行：bash run_drc.sh
# ------------------------------------------------------------------------------
#  用官方 KLayout DRC 脚本 sky130A_mr.drc 对版图 GDS 做 signoff 检查。
#
#  前置：先在 magic tkcon 里 source 05_layout/run_gds.tcl 生成 GDS
#
#  DRC 脚本用法（来自 sky130A_mr.drc 第 24 行的官方注释）：
#     klayout -b -rd input=my_layout.gds -rd report=sky130_drc.txt -r drc.drc
#  top_cell 与 thr（线程数）是可选变量。
#
#  产物：项目根下 drc_klayout.txt（KLayout 文本报告，扩展名非 .xml 即文本）
# ==============================================================================
set -uo pipefail

PROJ="/mnt/d/WorkBuddy/workspace/sky130 Two-Stage Miller OTA"
GDS="05_layout/mag/ota2_miller.gds"
REPORT="drc_klayout.txt"

cd "$PROJ" || { echo "!! 目录不存在: $PROJ"; exit 1; }

# --- 1. PDK_ROOT 与 DRC 脚本 -------------------------------------------------
if [ -z "${PDK_ROOT:-}" ]; then
    for c in "$HOME"/work/open_pdks/open_pdks/root/volare/sky130/build/*/; do
        if [ -d "${c}sky130A" ]; then PDK_ROOT="${c%/}"; break; fi
    done
fi
DRC="${PDK_ROOT:-}/sky130A/libs.tech/klayout/drc/sky130A_mr.drc"

# --- 2. 前置检查 --------------------------------------------------------------
if [ ! -f "$GDS" ]; then
    echo "!! 缺少 GDS: $PROJ/$GDS"
    echo "   -> 请先在 magic tkcon 里执行:"
    echo "      source \"/mnt/d/WorkBuddy/workspace/sky130 Two-Stage Miller OTA/05_layout/run_gds.tcl\""
    exit 1
fi
if [ ! -f "$DRC" ]; then
    echo "!! 找不到 DRC 脚本: $DRC"
    echo "   PDK_ROOT 当前值: '${PDK_ROOT:-<未设置>}'"
    exit 1
fi
if ! command -v klayout >/dev/null 2>&1; then
    echo "!! 找不到 klayout，请先安装"; exit 1
fi

echo "GDS    : $GDS ($(stat -c%s "$GDS") bytes)"
echo "DRC    : $DRC"
echo "report : $REPORT"
echo

# --- 3. 跑 DRC ---------------------------------------------------------------
echo "=================== KLayout signoff DRC ==================="
# -b  : batch（无图形界面）
# -rd : 给 ruby 脚本传变量（脚本里用 $input / $top_cell / $report / $thr）
# -r  : 要执行的 DRC runset
klayout -b \
    -rd input="$PROJ/$GDS" \
    -rd top_cell="ota2_miller" \
    -rd thr=8 \
    -rd report="$PROJ/$REPORT" \
    -r "$DRC"

# --- 3b. 回退：若这个 klayout 构建没有 ruby 支持，改用原生格式 ---------------
#     sky130A_mr.drc 是 ruby 脚本（开头 require 'time' / 'logger'），
#     sky130A.lydrc 是 KLayout 0.28+ 原生 DRC 格式，不依赖 ruby。
if [ ! -f "$REPORT" ]; then
    echo
    echo "!! 报告未生成 —— 多半是这个 klayout 构建没有 ruby 支持"
    echo "   改用原生格式 sky130A.lydrc 重试（不依赖 ruby）..."
    DRC2="${PDK_ROOT}/sky130A/libs.tech/klayout/drc/sky130A.lydrc"
    if [ -f "$DRC2" ]; then
        DRC="$DRC2"
        klayout -b \
            -rd input="$PROJ/$GDS" \
            -rd top_cell="ota2_miller" \
            -rd thr=8 \
            -rd report="$PROJ/$REPORT" \
            -r "$DRC"
    else
        echo "!! 备用脚本也不存在: $DRC2"
    fi
fi

# --- 4. 结果摘要 -------------------------------------------------------------
echo
echo "=================== 结果摘要 ==================="
if [ -f "$REPORT" ]; then
    echo "报告: $PROJ/$REPORT  ($(wc -l < "$REPORT") 行)"
    echo
    # KLayout 文本报告里每条规则形如 "  <rule>:  <n> errors"
    # 先把非空且含数字的规则行挑出来
    grep -iE "errors|violations|total|End of DRC" "$REPORT" | head -40
else
    echo "!! 未生成报告 $REPORT"
fi
