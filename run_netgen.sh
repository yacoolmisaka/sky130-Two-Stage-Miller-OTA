#!/usr/bin/env bash
# ==============================================================================
#  run_netgen.sh  ——  在 WSL 终端执行：bash run_netgen.sh
# ------------------------------------------------------------------------------
#  作用：把 magic 导出的版图网表与 xschem 导出的原理图网表做 LVS。
#
#  前置：先在 magic 的 tkcon 里 source run_lvs.tcl（生成 mag/ota2_miller.spice）
#
#  产物：项目根下 lvs_report.log
#  判读：报告里出现 "Circuits match uniquely." 即 LVS 通过。
# ==============================================================================
set -uo pipefail

PROJ="/mnt/d/WorkBuddy/workspace/sky130 Two-Stage Miller OTA"
LAYOUT="05_layout/mag/ota2_miller.spice"
SCHEM="03_sch/ota2_miller.spice"
REPORT="lvs_report.log"

cd "$PROJ" || { echo "!! 目录不存在: $PROJ"; exit 1; }

# --- 1. 输入文件存在性检查 ----------------------------------------------------
for f in "$LAYOUT" "$SCHEM"; do
    if [ ! -f "$f" ]; then
        echo "!! 缺少输入网表: $PROJ/$f"
        case "$f" in
            *layout*) echo "   -> 请在 magic tkcon 里先 source 05_layout/run_lvs.tcl" ;;
        esac
        exit 1
    fi
done
echo "layout 网表: $LAYOUT  ($(stat -c%s "$LAYOUT") bytes, $(stat -c%y "$LAYOUT" | cut -d. -f1))"
echo "schem  网表: $SCHEM  ($(stat -c%s "$SCHEM") bytes, $(stat -c%y "$SCHEM" | cut -d. -f1))"

# --- 2. 定位 PDK 的 netgen setup ---------------------------------------------
#     PDK_ROOT 环境变量优先；未设则回退到 magicrc 里写的 volare 构建目录。
if [ -z "${PDK_ROOT:-}" ]; then
    for c in "$HOME"/work/open_pdks/open_pdks/root/volare/sky130/build/*/; do
        if [ -d "${c}sky130A" ]; then PDK_ROOT="${c%/}"; break; fi
    done
fi
SETUP="${PDK_ROOT:-}/sky130A/libs.tech/netgen/sky130A_setup.tcl"
if [ ! -f "$SETUP" ]; then
    echo "!! 找不到 netgen setup 文件: $SETUP"
    echo "   PDK_ROOT 当前值: '${PDK_ROOT:-<未设置>}'"
    echo "   请执行 export PDK_ROOT=/你的/pdk/路径  后重跑"
    exit 1
fi
echo "PDK_ROOT    : $PDK_ROOT"

# --- 3. netgen 是否可用 ------------------------------------------------------
command -v netgen >/dev/null 2>&1 || {
    echo "!! 找不到 netgen，请先安装：sudo apt install netgen"; exit 1; }

# --- 4. 跑 LVS ---------------------------------------------------------------
echo
echo "=================== netgen LVS ==================="
netgen -batch lvs "$LAYOUT ota2_miller" "$SCHEM ota2_miller" "$SETUP" "$REPORT"
rc=$?

# --- 5. 判读 -----------------------------------------------------------------
echo
echo "=================== 结果摘要 ==================="
if [ -f "$REPORT" ]; then
    grep -nE "Circuits match|do not match|match uniquely|Property errors|Netlists (do not )?match" "$REPORT" | head -20
    echo
    echo "完整报告: $PROJ/$REPORT"
else
    echo "!! 未生成 $REPORT"
fi
exit $rc
