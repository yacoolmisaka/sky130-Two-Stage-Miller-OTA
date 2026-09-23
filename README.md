# SKY130 两级 Miller 补偿 OTA

> 在开源 SKY130（130nm）工艺上，完整走一遍 **规格定义 → 手算 sizing → 原理图 → 前仿 → 版图 → 签核（DRC/LVS）→ 含寄生后仿** 的模拟 IC 全流程。
>
> **当前状态：全流程闭环，收官于 2026-09-22。**
> 前仿 8 项指标全达标 → Magic 版图 10 器件 / 88 µm → netgen LVS `Circuits match uniquely.` → KLayout 官方 DRC **0 违规** → 含寄生后仿 GBW 仅掉 4.5%。
>
> 工具链全开源：ngspice / xschem / Magic / netgen / KLayout。

---

## 0. 进度总览

| 步 | 内容 | 状态 | 收官 |
|---|---|---|---|
| 0 | 环境 & PDK 模型库（含修复攻坚） | ✅ | 09-07 |
| 1 | 定指标 spec | ✅ | 09-09 |
| 2 | 手算 sizing | ✅ | 09-09 |
| 3 | 网表 + 四测试台 + 一键仿真 | ✅ | 09-09 |
| 4 | 前仿迭代调尺寸 | ✅ **8 项全达标** | 09-10 |
| 5 | xschem 原理图 + 网表交叉验证 | ✅ **Av 偏差 0.001 dB** | 09-16 |
| 6 | Magic 版图（10 器件 / 88 µm / 四层金属） | ✅ | 09-18 |
| 7 | Magic DRC 收敛 + 参数提取 | ✅ **132 → 68** | 09-19 |
| 8 | netgen LVS | ✅ **Circuits match uniquely.** | 09-21 |
| 9 | KLayout 官方 runset 签核 DRC | ✅ **0 违规** | 09-22 |
| 10 | 寄生提取 + 含寄生后仿 | ✅ **GBW −4.5%** | 09-22 |

---

## 0.5 最终成绩单

### 电路指标

| 指标 | 目标 | 前仿实测 | 后仿实测（含寄生） |
|---|---|---|---|
| 开环增益 Av | ≥ 60 dB | **72.65 dB** | **72.65 dB** |
| 单位增益带宽 GBW | 10 ~ 20 MHz | **10.39 MHz** | **9.92 MHz**（−4.5 %） |
| 相位裕度 PM | ≥ 60° | **63.28°** | **64.56°** |
| 压摆率 SR | ≥ 10 V/µs | **+14.1 / −12.3 V/µs** | — |
| 静态功耗 | ≤ 150 µW | **139.7 µW** | — |
| 输入共模范围 | 0.78 ~ 1.45 V | **0.21 ~ 1.80 V** | — |
| 阶跃过冲 | 小 | **0.0 %** | — |
| 管子工作区 | 全部饱和 | **8/8 饱和** | — |

### 签核

| 项 | 工具 | 结果 |
|---|---|---|
| **LVS** | netgen + 官方 `sky130A_setup.tcl` | **Circuits match uniquely.**（10 器件 / 10 网） |
| **DRC（签核）** | KLayout + 官方 `sky130A_mr.drc` | **0 违规** |
| **DRC（过程）** | Magic | 132 → 68 项（余项为 PDK 器件生成器固有几何） |
| **GDS** | Magic `gds write` | 9 cell / 14 层号 / 约 7300 shape |

> **为什么两份 DRC？** Magic DRC 是画版图时实时用的；KLayout 跑官方 runset 才是交付晶圆厂前的签核口径。
> 两者不是一回事，本项目都做了。GDS 层号已实测核对（64=nwell / 67=li1 / 68~71=met1~4 / 235=DIEAREA），
> 与官方 `sky130A.map` 吻合 —— 排除"层映射错 → 空版图 → 假 0 违规"的可能。

---

## 1. 前仿成绩单（2026-09-10 收官）

| 指标 | 目标 | 实测 | 判定 |
|---|---|---|---|
| 开环增益 Av | ≥ 60 dB | **72.65 dB** | ✅ |
| 单位增益带宽 GBW | 10 ~ 20 MHz | **10.39 MHz** | ✅ |
| 相位裕度 PM | ≥ 60° | **63.28°** | ✅ |
| 压摆率 SR | ≥ 10 V/µs | **+14.1 / −12.3 V/µs** | ✅ |
| 静态功耗 | ≤ 150 µW | **139.7 µW** | ✅ |
| 输入共模范围 ICMR | 0.78 ~ 1.45 V | **0.21 ~ 1.80 V** | ✅ 更宽 |
| 阶跃过冲 | 小 | **0.0 %** | ✅ |
| 管子工作区 | 全部饱和 | **8/8 饱和** | ✅ |

**工作点明细**（`bash run.sh op`）：

| 器件 | Id | gm | Vov |
|---|---|---|---|
| M1, M2 | 8.24 / 8.22 µA | 90.1 µS | 0.144 V |
| M3, M4 | 8.24 / 8.22 µA | 41.4 µS | 0.356 V |
| M5 | 16.46 µA | — | 0.068 V |
| M6, M7 | 51.16 µA | 387 / 798 µS | 0.225 / 0.069 V |
| Mref | 10.00 µA | — | 0.069 V |

**成品图**：`04_sim/bode.svg`（波特图）、`04_sim/tran.svg`（阶跃响应）——浏览器直接打开。

---

## 1.5 原理图交叉验证（2026-09-16 完成）

原理图画完只代表"图好看"，必须证明它**电学等价于手写网表**才算过关。

```
xschem 画图 → 点 Netlist 导出 → sch2sim.py 转换 → tb_ac_sch.sp 跑 AC → 对比基线
```

```bash
# 1) xschem 里点 Netlist 按钮
#    网表默认生成在 ~/.xschem/simulations/ota2_miller.spice（不是项目目录！）
# 2) 转换：拆总宽、剥 ** 前缀、删 .end
python3 04_sim/sch2sim.py ~/.xschem/simulations/ota2_miller.spice \
        -o 03_sch/ota2_miller_sim.spice
# 3) 跑交叉验证测试台
cd 04_sim && bash run.sh acsch
```

**结果**：

| 指标 | 手写网表（基线） | 原理图导出网表 | 偏差 | 判定 |
|---|---|---|---|---|
| 开环增益 Av | 72.65 dB | **72.649 dB** | 0.001 dB | ✅ |
| 单位增益带宽 GBW | 10.39 MHz | **10.41 MHz** | +0.2 % | ✅ |
| 相位裕度 PM | 63.28° | **64.37°** | +1.09° | ✅ |

> **PM 那 1.09° 的差异是预期内的，不是接线错误。**
> 手写网表里 `Rz` 是**理想 3 kΩ 电阻**，原理图里是 PDK 的 `res_xhigh_po_0p69` 子电路
> （含端头 head 电阻、实际 W 不精确等于 0.69 µm），实际阻值略偏离 3000 Ω，零点位置随之微移；
> `Cc` 同理（理想 1.200 pF vs MiM 1.199 pF）。这类 1° 量级差异属于**器件模型精度**。

**结论：原理图连接与参数确认无误，可以进版图。**

---

## 1.6 版图实现（STEP 6，2026-09-18）

用 Magic 完成，**全部由 TCL 脚本参数化生成**（坐标可精确复现、便于迭代）。

| 项 | 值 |
|---|---|
| 顶层单元 | `ota2_miller` |
| 器件数 | 10（M1/M2/M3/M4/M5/M6/M7/Mref + MiM Cc + poly Rz） |
| 整体尺寸 | 88 µm |
| 布线层 | metal1 ~ metal4（VDD 走 metal1，GND 走 metal2） |
| 最大器件 | M6 28 指 PMOS（W=56 µm）、M7 25 指 NMOS（W=62.5 µm） |

**版图上的三个关键处理**：

1. **叠放 via（stacked via）** —— 输出节点接 MiM 电容上极板用 **via2+via3 叠放**、补偿节点接下极板用 **via1+via2 叠放**，一次跨两层直达极板，避开 24.3×24.3 µm 电容区绕行。
2. **多指器件的源漏分组** —— N 指器件有 N+1 个扩散岛，**偶数岛一组 / 奇数岛一组**并联。版图提取出的 80 个实例经 netgen 合并回 5 个 nfet + 3 个 pfet。
3. **多指管栅极环跨接** —— 栅极环有断口，用 metal1 覆盖块 + metal2 桥跨漏极线连通（含 0.05 µm 栅环间距避让）。

**最后 220 项几何修正**：`05_layout/fix_all.tcl`（fix1 39 + fix2 163 + fix3 8 + fix4 10 项），
覆盖短路修复、开路补齐、多指捆扎、Miller 补偿支路、体接触五大类。
全部经 `05_layout/_check_all.py` 五组检查验证（SHORT 45 对 / OPEN 10 / BUNDLE 12 / MILLER 4 / BULK 4）→ `ALL CHECKS PASSED`。

---

## 1.7 签核怎么跑（STEP 8 / 9）

```bash
# 1) 版图：magic tkcon 内（生成 mag/ota2_miller.spice）
source 05_layout/run_lvs.tcl

# 2) LVS：netgen 比对版图网表 vs 原理图网表
bash run_netgen.sh          # → lvs_report.log

# 3) GDS：magic tkcon 内
source 05_layout/run_gds.tcl

# 4) 签核 DRC：KLayout 官方 runset
bash run_drc.sh             # → drc_klayout.txt
```

**LVS 对账的关键数字**：

- 版图提取 80 个实例 → netgen 合并为 **10 个器件**（与原理图 1:1）
- 版图原始 14 个网 → **减去 1**（VSUBS 并入 GND）**减去 3**（三片 nwell 合一并入 VDD）= **10 个网**，与原理图一致
- 判定：`Circuits match uniquely.`（器件数和网数**都**对上才算唯一匹配，只对上一个不算）

> **踩坑记录**：13 轮 LVS 迭代日志（`lvs3.log` ~ `lvs11.log`、`lvs_final.log`…）全部保留在仓库根目录，
> 记录从"器件数对了但网数不对"到最终通过的全过程。**最终成功版本是 `lvs_report.log`**。

---

## 1.8 含寄生后仿（STEP 10，2026-09-22）

```bash
# 1) 寄生网表：magic 新开会话（ext2spice lvs 是持久开关，不能在同会话切）
source 05_layout/run_pext.tcl

# 2) 后仿
bash run_postsim.sh         # → 04_sim/ac_bode_post.txt
```

| 指标 | 前仿 | 后仿 | 变化 |
|---|---|---|---|
| Av | 72.65 dB | **72.65 dB** | 持平 |
| GBW | 10.39 MHz | **9.92 MHz** | −4.5 % |
| PM | 63.28° | **64.56°** | +1.28° |

**提取到的寄生**：29 个寄生电容（主要集中在输出节点与补偿节点）。

**三个坑**：

| 坑 | 现象 | 解法 |
|---|---|---|
| `**FLOATING` 标记 | ngspice 报 `unknown parameter (*)` | 它在**行尾**，不是注释（SPICE 只有行首 `*` 才是注释），用 `sed` 剥除 |
| `shorted VSRC` | `Fatal: instance vgnd is a shorted VSRC` | ngspice 已把 `GND` 归一化为节点 `0`，不能再补 `VGND GND 0` |
| `singular matrix` | `check node m1_3660_752#`，av0 算出 −157 dB | 悬空金属岛无 DC 通路，用 `04_sim/fix_float.py` 给每个挂 1 TΩ 到地 |

---

## 2. 环境

- **宿主机**：Windows 11 + WSL2（Ubuntu），项目在 `D:\WorkBuddy\workspace\sky130 Two-Stage Miller OTA\`
  （WSL 侧 `/mnt/d/WorkBuddy/workspace/sky130 Two-Stage Miller OTA/`，**路径含空格**，命令记得加引号）
- **PDK**：volare 安装的 SKY130（版本号 `c6d73a35f524070e85faff4a6a9eef49553ebc2b`）

  | 用途 | 路径（相对 `$PDK_ROOT/sky130A/`） |
  |---|---|
  | 仿真模型库 | `libs.tech/ngspice/sky130.lib.spice` |
  | 模型卡本体 | `libs.ref/sky130_fd_pr/spice/`（639 个文件） |
  | xschem 符号 | `libs.tech/xschem/` |
  | Magic 版图单元 | `libs.ref/sky130_fd_pr/mag/` |

- **工具链**：ngspice（仿真）、xschem（原理图）、Magic（版图）、netgen（LVS）

> ⚠️ **模型库必须用 `libs.tech/ngspice/sky130.lib.spice`**（参数化主库）。
> 不要用 `libs.tech/combined/continuous/sky130.lib.spice` —— 那是给 FastSPICE / Monte Carlo 用的，
> 里面按 W/L 预生成了大量尺寸档位子电路，普通 tt 仿真会算出负参数直接 fatal。

---

## 3. 设计规格（Spec）

| 指标 | 目标 | 说明 |
|---|---|---|
| 电源 | 1.8 V | sky130 核电压 |
| 开环增益 Av | ≥ 60 dB | 两级叠加 |
| GBW | 10 ~ 20 MHz | 设计点 15 MHz，实测收敛在 10.4 MHz |
| 相位裕度 PM | ≥ 60° | |
| 压摆率 SR | ≥ 10 V/µs | |
| 输入共模范围 ICMR | 0.8 ~ 1.45 V | 受 Vthn ≈ 0.62V（实测）限制 |
| 负载 CL | 2 pF | |
| Miller 电容 Cc | 1.2 pF | Cc/CL = 0.6 |
| 静态功耗 | ≤ 150 µW | |

