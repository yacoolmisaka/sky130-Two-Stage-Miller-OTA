#!/bin/bash
# ============================================================================
#  SKY130 OTA 前仿一键运行脚本  (真 sky130 模型版)
#
#  模型: volare 装的 c6d73a3... sky130A
#        .../sky130A/libs.tech/ngspice/sky130.lib.spice  (确定性 corner)
#        具体路径写在 models.inc 里, 本脚本自动从那里解析.
#        注: combined/continuous 那套是 MC/连续 corner 库, 普通 tt 仿真会
#            fatal (Dsub negative), 不要指过去.
#
#  三个必须处理的坑:
#    1) wrapper 里全是相对路径 .include -> ngspice 必须从 wrapper 目录启动
#    2) 但测试台 tb_*.sp 里的 ../03_sch/ 也是相对路径 -> 改成绝对路径
#    3) wrdata 输出会落到 wrapper 目录 -> 也改成绝对路径指回 04_sim
#  本脚本用 sed 自动处理 2) 和 3)
#
#  用法:  cd 04_sim && bash run.sh            # 跑全部
#         cd 04_sim && bash run.sh op         # 只跑工作点
#         cd 04_sim && bash run.sh ac         # 只跑 AC (手写网表)
#         cd 04_sim && bash run.sh acsch      # 只跑 AC (原理图网表交叉验证)
#         cd 04_sim && bash run.sh tran       # 只跑瞬态
#         cd 04_sim && bash run.sh icmr       # 只跑 ICMR
# ============================================================================
set -u
cd "$(dirname "$0")"

SIM_DIR=$(pwd)                 # 04_sim 目录 (结果文件都落这)
SCH_DIR=$(cd "../03_sch" && pwd)

# ngspice 的 wrdata 既不支持含空格路径, 也不支持引号包裹路径。
# 项目目录名 "sky130 Two-Stage Miller OTA" 带空格, 所以建一个无空格软链接,
# 让 wrdata 走软链接 (实际文件仍落在 04_sim/)。
OUT_LINK=/tmp/ota_sim_out
ln -sfn "$SIM_DIR" "$OUT_LINK"

# ---------- 1. 校验 models.inc ----------
echo "[1/3] 检查 models.inc ..."
if [ ! -f "models.inc" ]; then
    echo "!! models.inc 不存在, 请检查路径"
    exit 1
fi
MOD_PATH=$(grep -oE '"[^"]*\.lib\.spice"' models.inc | head -1 | tr -d '"')
if [ -z "$MOD_PATH" ]; then
    echo "!! models.inc 里没找到 .lib \"xxx.lib.spice\" 行"
    exit 1
fi
if [ ! -f "$MOD_PATH" ]; then
    echo "!! 模型文件不存在: $MOD_PATH"
    echo "   请检查 volare 装的路径, 或改 models.inc"
    exit 1
fi
SKY130_DIR=$(dirname "$MOD_PATH")
echo "     模型路径 : $MOD_PATH"
echo "     工作目录 : $SKY130_DIR  (ngspice 必须从这启动)"
echo "     结果目录 : $SIM_DIR"
echo ""

# ---------- 2. 生成绝对路径版测试台 ----------
echo "[2/3] 生成绝对路径版测试台 ..."
prep () {
    local f="$1"
    local base
    base=$(basename "$f" .sp)
    local out="$SIM_DIR/.run_${base}.sp"
    sed -e "s|\.\./03_sch/|${SCH_DIR}/|g" \
        -e "s|\"models.inc\"|\"${SIM_DIR}/models.inc\"|g" \
        -e "s|wrdata \([A-Za-z0-9_]\+\.txt\)|wrdata ${OUT_LINK}/\1|g" \
        "$f" > "$out"
    echo "$out"
}

# ---------- 3. 跑仿真 ----------
echo "[3/3] 运行 ngspice ..."
WHAT="${1:-all}"

run_one () {
    local f="$1"
    local abs
    abs=$(prep "$f")
    echo ""
    echo "################################################################"
    echo "####  $f"
    echo "################################################################"
    (cd "$SKY130_DIR" && ngspice -b "$abs" 2>&1)
}

case "$WHAT" in
    op)   run_one tb_op.sp ;;
    ac)   run_one tb_ac.sp ;;
    acsch) run_one tb_ac_sch.sp ;;
    tran) run_one tb_tran.sp ;;
    icmr) run_one tb_icmr.sp ;;
    exp)  run_one exp_w.sp ;;
    all)
        run_one tb_op.sp
        run_one tb_ac.sp
        run_one tb_tran.sp
        run_one tb_icmr.sp
        ;;
    *)
        echo "未知参数: $WHAT  (可选: op / ac / tran / icmr / exp / all)"
        exit 1 ;;
esac

echo ""
echo "=================================================================="
echo " 全部完成。结果文件 (在 04_sim/ 下):"
echo "   ac_bode.txt    波特图数据  -> python3 plot_bode.py ac_bode.txt"
echo "   tran_step.txt  阶跃数据    -> python3 plot_tran.py tran_step.txt"
echo "   icmr.txt       ICMR 数据   -> python3 icmr_report.py icmr.txt"
echo "=================================================================="
