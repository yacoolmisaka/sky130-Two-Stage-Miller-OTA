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

---

## 4. 手算 sizing

### 4.1 设计顺序（每个管子只有一个自由度）

```
Cc  →  Iss  →  M1/M2  →  M3/M4  →  M5  →  M6  →  M7
(PM)  (SR)    (GBW)     (ICMR+)   (ICMR-)  (PM)   (镜像)
```

| 器件 | 由什么定 | 公式 |
|---|---|---|
| **Cc** | 相位裕度 | `Cc ≥ 0.22·CL` |
| **Iss** | 压摆率（正向） | `SR = Iss / Cc` |
| **M1/M2** | 单位增益带宽 | `gm1 = 2π·GBW·Cc`，`(W/L)1 = gm1²/(2·Kn'·Id1)` |
| **M3/M4** | ICMR 上限 | `Vicm(max) = VDD − \|Vthp\| − \|Vov3\| + Vthn` |
| **M5** | ICMR 下限 | `Vicm(min) = Vov5 + Vthn + Vov1` |
| **M6** | 相位裕度 | `gm6 ≥ 2.2·(CL/Cc)·gm1`，或按 `PM = 90 − atan(GBW/p2) − atan(GBW/z1)` 迭代 |
| **M7** | 镜像自基准 | `(W/L)7 = (I6/Iref)·(W/L)ref` |

手算脚本：`02_sizing/sizing.py`（参数化，改指标可重算），输出存档 `02_sizing/sizing_result.txt`

```bash
python3 02_sizing/sizing.py                                  # 默认
python3 02_sizing/sizing.py --gbw 10e6 --cl 3p --cc 1.5p     # 换设计点
python3 02_sizing/sizing.py --pm 65                          # 提高 PM 目标
```

### 4.2 最终尺寸（仿真网表 `03_sch/ota2_miller.sp` 里的写法）

| 器件 | 类型 | 写法 | 等效总宽 | L |
|---|---|---|---|---|
| M1, M2 | NMOS | `w=2 nf=1 m=2` | 4 µm | 1 µm |
| M3, M4 | PMOS | `w=2 nf=1 m=2` | 4 µm | 1 µm |
| M5 | NMOS | `w=2 nf=1 m=12` | 24 µm | 1 µm |
| M6 | PMOS | `w=2 nf=1 m=28` | 56 µm | 1 µm |
| M7 | NMOS | `w=2.5 nf=1 m=25` | 62.5 µm | 1 µm |
| Mref | NMOS | `w=2.5 nf=1 m=5` | 12.5 µm | 1 µm |
| Cc | — | 1.2 pF | | |
| Rz | — | 3 kΩ | | |

**两个关键设计点**：

1. **为什么接 vbias 的三个 NMOS 要一起放大**
   M5/M7/Mref 栅极同接 `vbias` → Vgs 相同 → Vov 相同 → **电流比 = (w×m) 之比，不是 m 之比**。
   为让 M5 退出线性区（其 Vds 只有约 0.12V），三者需同比加宽压低 Vov；**改一个必须同步改另外两个**，否则镜像比错、电流跑偏。

2. **为什么必须串调零电阻 Rz**
   无 Rz 时 RHP 零点 `z1 = gm6/(2π·Cc)` 吃相位，实测 PM 只有 50.3°。
   串入 `Rz ≈ 1.2/gm6 = 3kΩ` 后零点移到左半平面反补相位，**PM 提到 63.28°，而 GBW / SR / 功耗零损失**。

---

## 5. 电路结构

两级 Miller 补偿 OTA，8 管 + 补偿网络：

- **第一级**：M1/M2 NMOS 差分输入对 + M3/M4 PMOS 电流镜负载（M3 二极管连接），M5 尾电流源
- **第二级**：M6 PMOS 共源放大 + M7 NMOS 电流沉
- **频率补偿**：`n2 ─[Rz 3k]─ nz ─[Cc 1.2p]─ vout`（Rz 与 Cc 串联跨接第一级输出与输出）
- **偏置**：外部 10µA 基准电流经二极管连接 Mref 产生 vbias，M5/M7 按比例镜像
- **极性**：`vinp` 同相、`vinm` 反相

---

## 6. 前仿怎么跑

```bash
cd "/mnt/d/WorkBuddy/workspace/sky130 Two-Stage Miller OTA/04_sim"
bash run.sh            # 跑全部
bash run.sh op         # 只跑工作点
bash run.sh ac         # 增益/GBW/PM（手写网表）
bash run.sh acsch      # 增益/GBW/PM（原理图导出网表 → 交叉验证，见 §1.5）
bash run.sh tran       # 压摆率/阶跃
bash run.sh icmr       # 输入共模范围
bash run.sh exp        # W/nf/m 参数语义判别实验（排障用）
```

`run.sh` 自动处理三件事：① 从 `models.inc` 解析模型绝对路径 ② 生成绝对路径版测试台
③ `cd` 到模型库目录启动 ngspice（wrapper 里全是相对路径 include）。

### 四个测试台看什么

| 文件 | 看什么 | 合格标准 |
|---|---|---|
| `tb_op.sp` | 工作点：饱和判据 / Id / gm / Vov / ro / 功耗 | 8 个饱和判据 ≥ 0 |
| `tb_ac.sp` | 开环增益 / GBW / PM | Av ≥ 60dB，GBW 10~20MHz，PM ≥ 60° |
| `tb_tran.sp` | 压摆率 / 过冲 | SR ≥ 10 V/µs，过冲小 |
| `tb_icmr.sp` | 输入共模范围 | 覆盖 spec |

### 后处理与独立验算

```bash
python3 plot_bode.py ac_bode.txt     # → bode.svg  波特图（自动标 GBW/PM）
python3 plot_tran.py tran_step.txt   # → tran.svg  阶跃响应（自动算过冲）
python3 icmr_report.py icmr.txt      # → 自动给出 ICMR 上下限
python3 verify_pm.py ac_bode.txt     # → 从原始数据独立复算 GBW/PM（交叉验证）
```

### 开环 AC 测试台的原理

开环增益 4000+ 倍，直接加 DC 输入会让输出饱和，必须用「DC 反馈 + AC 开路」的 L/C 技巧：

```
        Lfb = 1e9 H
   vout ────[电感]────┐
                      │        DC：电感短路 → vout = vinm，单位增益负反馈，工作点自动建立
   vinm ◄─────────────┘        AC：jwL 极大 → 反馈断开，真正开环
      │
      └──[Cin = 1F]── vin_ac   DC：电容开路，不影响工作点
                                AC：电容短路，把 ±1V 差分激励注入
```

**相位口径（重要）**：本测试台 AC 激励加在**反相端** `vinm`（`vinp` 是 AC 地），
所以 `vout` 已含一次 180° 反相，**0dB 穿越点处 `vp(vout)` 直接就是 PM**，不要再加 180°。

---

## 7. 微调规则表

| 症状 | 根因 | 改法 | 副作用 |
|---|---|---|---|
| **PM < 55°** | RHP 零点吃相位 / gm6 不够 | ① **串调零电阻 Rz**（首选，见 §4.2） ② 加宽 M6 ③ 加大 Cc | ①多一个器件 ②面积↑ ③GBW↓ |
| PM > 75° | M6 过设计 | 收窄 M6 或减小 Rz | 省面积 |
| **GBW 不够** | gm1 不够 | 加大 `(W/L)1` 或 Iss | 功耗↑ |
| **增益 < 55 dB** | ro 不够 | 把 M1/M3/M6/M7 的 L 从 1 µm 提到 2 µm | 面积↑、GBW 略降 |
| **SR 不够** | Iss（正向）或 I6（负向）不够 | 加大对应电流 | 功耗↑ |
| **ICMR 下限太高** | Vov5 太大 | 加大 M5 的 (w×m)，**同步放大 Mref** 保镜像比 | 面积↑ |
| **ICMR 上限太低** | \|Vov3\| 太大 | 加大 M3/M4 的 (w×m) | 面积↑ |
| 某管进线性区（Vds−Vov < 0） | 该管 Vds 不够 | 降该管 Vov（加宽）或查偏置 | 面积↑ |
| Vov < 0.06V | 逼近亚阈，匹配/噪声变差 | 减小该管 (w×m) | — |

---

## 8. 踩过的坑（本项目最有价值的部分）

### 8.1 PDK 环境层（模型库）

| 坑 | 现象 | 解法 |
|---|---|---|
| 模型卡缺失 | `Could not find include file ...libs.ref/sky130_fd_pr/spice/...` | 手动解压时只解了 `mag/`，需补解 `spice/` 这一支（639 个文件） |
| 特殊器件缺失 | `special_pfet_latch.pm3.spice` 找不到 | 该器件包未下载；**别一个个删 include**（会破坏 `.param` 链），正确做法是 **tar 还原原厂文件 + 缺失文件建空占位** |
| 硬编码负参数 | `Fatal: Dsub = -1.61 is negative` | 全库 3500+ 处负 `Dsub`：`sed` 批量翻正 |
| 运行时算出负参数 | `Fatal: u0 at current temperature is not positive` | 关键词 **"at current temperature"** = 运行时计算值，改文件没用，只能让 W/L 落回 bin 内 |
| bin 外推 | 报 `__model.23` 这类边界 bin，`Pclm / Drout / Eta0` 为负 | **w 只能写 2~2.5µm**；w ≥ 10 必然触发 |
| wrapper 相对路径 | `Could not find include file` 且路径看着没错 | wrapper 里全是相对 include，ngspice **必须从 wrapper 所在目录启动** |

### 8.2 器件参数语义层（实测判定）

| 结论 | 证据 |
|---|---|
| **`nf` 不倍增电流** | Mref(w=2.5,nf=2,10µA,Vov=0.209V) 反推 KP=183µA/V²，与手算 173 吻合 7%；若按 w×nf=5µm 反推则 KP=91.5，差一倍 |
| **`m=` 是纯电流倍增** | 实验：`w=2 nf=5 m=5` / `w=2 nf=5` = **5.0**（精确） |
| 所以仿真写法 | `w=2 nf=1 m=N`（躲 bin + 拿电流）；原理图/版图用标准 `w=2 nf=N`，两者电学等价 |

### 8.3 工具/脚本层

| 坑 | 现象 | 解法 |
|---|---|---|
| **`vp()` 返回弧度** | PM 显示 0.86°（实际是 0.86 rad = 50.3°） | 乘 `180/π`。**排查手法**：低频相位显示 3.1412（=π）就说明是弧度 |
| `meas FIND` 不支持复合表达式 | `no such vector as (180+vp(vout))` | 先 `FIND vp(vout)` 再 `let` 运算 |
| `meas ... PARAM='expr'` 不可靠 | `no such function as 'param=...'` | 拆成两个 `meas` + `let` 算斜率 |
| **`wrdata` 路径不能含空格** | `no such vector Two-Stage`（把目录名当表达式解析） | 建无空格软链接 `/tmp/ota_sim_out` 指向输出目录 |
| sky130 subckt 不暴露 `region` | `no such parameter region` | 改用 `Vds − (|Vgs|−|Vth|) ≥ 0` 判饱和 |
| xschem 用户配置报错 | `invalid command name "font"` | `~/.xschem/xschemrc` 在 Tk 初始化**之前**被 source，不能直接调 Tk 命令；字体设置要用 `after idle {…}` 延后 |
| xschem 启动自动加载不存在的示例 | `Unable to open file: .../sky130_tests/top.sch` | 带文件名参数启动 `xschem xxx.sch`，或补一个空文件 |
| **xschem 网表带 `**` 前缀** | `Error: unknown subckt: ...` —— `**.subckt` / `**.ends` 被 SPICE 当整行注释 → **子电路根本没定义** | 去掉前两个星号；`sch2sim.py` 已内置处理 |
| **导出网表末尾的 `.end`** | 被 `.include` 进来会让 ngspice **提前结束解析**，后面器件全读不到 | 整行删掉 |
| **网表不在项目目录** | 点完 Netlist 满世界找不到 `.spice` 文件 | `netlist_dir` 默认是 `~/.xschem/simulations/` |
| **导出端口顺序 ≠ 手写网表** | 套用手写版的 `XOTA` 行 → 六个脚全接错 | xschem 导出 `GND vinp vinm vout vbias VDD`；手写是 `vinm vinp vout vdd vss vbias` |
| **器件实例坐标带小数** | 引脚与导线端差 0.3~1.2 单位，**画面完全看不出断开**，但 xschem 判定全悬空 → 一堆 `open net` / `undriven node` | 坐标取整。**`m`（移动）是纯平移、不做网格吸附**，所以小数永远拖不掉 —— 要挪位置就**删掉重放** |
| 原理图接线想核验但不想一个个点 | — | `python3 03_sch/check_sch.py` —— 无 GUI 逐引脚核验，1 秒出报告 |
| **`Ctrl+P` 打不开器件参数窗** | 选了器件按 Ctrl+P 没反应 | Magic 是 X11 的 **focus-follows-mouse**：键盘事件只送给**鼠标指针所在**的那个窗口。鼠标停在 tkcon 控制台上按 Ctrl+P 会被 tkcon 吃掉 → **把鼠标指到 layout 窗口的器件上再按**。且必须先用 `i` 真正**选中**（只拖光标框罩上去不算选中） |
| 想核验版图器件尺寸对不对 | — | 不必卡在 `Ctrl+P`：**STEP 8 的 netgen LVS 会逐管比对 W/L/nf**，填错了一定报 parameter mismatch。也可以在 tkcon 敲 `cellname list children` 看生成的子 cell 名 |
| **`save` 只写当前 cell，子 cell 不落盘** | 重开 magic 后版图变空，报 `Cell sky130_fd_pr__nfet_01v8_XXXXXX couldn't be read` + `Timestamp mismatches` | 生成器造的器件是**独立子 cell**，各是各的 `.mag` 文件。存盘必须 **`save` + `writeall`** 两条都跑（`writeall` 把所有改过的子 cell 一起写盘） |
| **`RLIMIT_NOFILE is above 1024` 警告** | magic 8.3 + Tcl 8.6 启动时打这行警告 | 不是废话：Tcl 8.6 的 fd 处理在 ulimit>1024 时会出各种诡异读写问题。**启动 magic 前加 `ulimit -n 1024`** |
| **Tcl 变量名里的 `::` 尾巴** | `can't read "::SKYLIB::": no such variable` | `$` 替代会把 `::` 吞进变量名：`$::SKYLIB::$dev` 解析成变量 `::SKYLIB::` + `$dev`。**含 `::` 的变量名必须加花括号**：`${::SKYLIB}::$dev` |
| **`cellname list property` 对不存在的 property 直接抛错** | `Property name "library" is not defined`（不是返回空串） | 查询前不确定 property 在不在就必须 `catch`，否则脚本中断 |
| **`getcell` 不是 PCell 生成器** | `getcell sky130_fd_pr__nfet_01v8` → `Cell sky130_fd_pr__nfet_01v8 couldn't be read` | 官方定义：*"Import a cell as a subcell of the current edit cell."* —— 它去**搜索路径**找**已存在**的 `<cellname>.mag` 文件。本 PDK 版没有 `libs.ref/sky130_fd_pr/mag/`，必然失败。**器件生成走 layout 窗口菜单栏的 `Devices1` / `Devices2`，或脚本调 `magic::gencell <library>::<type> <实例名> -spice W .. L .. nf ..`（见 `05_layout/gen_devices.tcl`）** |
| **`File → Import SPICE` 也不是版图生成器** | 以为能"网表转版图" | `readspice.tcl` 开头写明：*"This is NOT a schematic-to-layout function!"* 它只给**已有** cell **标注端口顺序**，是 LVS 前置步骤 |
| Magic 字号太小，想永久放大 | — | Magic 的字是 **Tk 字体**（没有 `magic::set_option font` 这个命令）。**控制台**（`tkcon 2.3 Main`）→ `~/.tkconrc`：`set ::tkcon::OPT(font) {{DejaVu Sans Mono} 20}`；**layout1**（菜单栏 / 器件参数窗）→ 必须写进 **magic 真正读的那个 rcfile**。本流程用绝对路径 `-rcfile $PDK_ROOT/.../sky130A.magicrc` 启动，此时 `~/.magicrc` **不会被读**（`utils/main.c` 中只有 `RCFileName[0] != '/'` 时才去拼 `$HOME/<名字>`），所以 font 行要追加到 **PDK 的 magicrc**：`font configure TkDefaultFont/TkTextFont/TkMenuFont/TkFixedFont -size 20` 再 `option add *Font <字体名>`。（PDK 重装会丢，重跑一次即可。详见 `05_layout/docs/版图步骤.md` §0.0） |
| Tk 字体族名带空格 | `expected integer but got "Sans"` | 字体值被拆成 4 个词，Tk 把第 2 个词当字号。**族名带空格要再套一层花括号**：`{{DejaVu Sans Mono} 20}` |
| `.bashrc` 混进 Windows 换行符 | 每次开终端报 `line N: syntax error near unexpected token $'…\r'` | `cp ~/.bashrc ~/.bashrc.bak && sed -i 's/\r$//' ~/.bashrc && bash -n ~/.bashrc` |

### 8.4 方法论教训

- **两个独立方法互相验证**：ngspice 的 `meas` 和 Python 从原始数据复算，两个都对上才可信。
  （PM 那个坑就是靠这个抓出来的：SR 正常 + 阶跃 0% 过冲 + PM=1° 三个现象自相矛盾 → 先怀疑测量口径）
- **"at current temperature"、"computed" 这类字眼 = 运行时值**，改数据文件无效。
- **改联动参数必须一次改全**：接同一偏置节点的管子，镜像比按 `w×m` 算，改一个动三个。
- **每次只改一个变量**：否则出问题无法归因。

---

## 9. 目录说明

```
sky130 Two-Stage Miller OTA/
├── README.md                       ← 你在这儿
├── 简历项目介绍.md                  ← 一页纸速览（参数 + 成绩单 + 关键操作）
├── docs/
│   ├── 工程全流程复盘.md            ← 全流程复盘 + 技术问答（最值得一读的一份）
│   └── DRC攻坚历程.md              ← DRC 从 132 项收敛到 68 项的过程记录
│
├── 01_spec/                        ← 设计规格
├── 02_sizing/
│   ├── sizing.py                   ← 手算脚本（参数可调）
│   └── sizing_result.txt           ← 输出存档
├── 03_sch/
│   ├── ota2_miller.sp              ← 核心仿真网表（尺寸全在顶部 .param）
│   ├── ota2_miller_sky130.sp       ← 真 sky130 版备份
│   ├── ota2_miller.spice           ← LVS 用的原理图网表
│   ├── xschem连线清单.md            ← STEP 5 画图用（含最终尺寸 + Rz）
│   ├── ota2_miller.sch             ← xschem 原理图（STEP 5 产出）
│   ├── ota2_miller_sim.spice       ← 原理图导出网表（经 sch2sim.py 转换）
│   └── check_sch.py                ← 原理图接线核验（无 GUI，逐引脚）
├── 04_sim/
│   ├── models.inc                  ← 模型库指向（改动只改这里）
│   ├── run.sh                      ← 一键仿真（op/ac/acsch/tran/icmr/exp）
│   ├── tb_op.sp / tb_ac.sp / tb_tran.sp / tb_icmr.sp
│   ├── tb_ac_sch.sp                ← AC 交叉验证（原理图导出网表）
│   ├── tb_ac_post.sp               ← 后仿测试台
│   ├── exp_w.sp                    ← W/nf/m 参数语义判别实验
│   ├── plot_bode.py / plot_tran.py ← 生成 SVG（纯标准库，无需 matplotlib）
│   ├── icmr_report.py / verify_pm.py ← ICMR 判读 / PM 独立复算
│   ├── fix_float.py                ← 悬空节点修补（后仿用）
│   ├── ac_bode.txt / ac_bode_post.txt ← 前仿 / 后仿原始数据
│   └── bode.svg / tran.svg         ← 成品图
├── 05_layout/
│   ├── README.md                   ← 版图目录索引（50 tcl + 40 py 该怎么看）
│   ├── run_lvs.tcl                 ← 【入口】应用修正 → 提取 → 导出 LVS 网表
│   ├── run_gds.tcl                 ← 【入口】导出 GDS
│   ├── run_pext.tcl                ← 【入口】导出含寄生网表
│   ├── fix_all.tcl                 ← 最终 220 项几何修正（fix1~fix4 合并）
│   ├── _check_all.py               ← 五组几何检查（SHORT/OPEN/BUNDLE/MILLER/BULK）
│   ├── <其余 tcl/py>               ← 生成与调试脚本，详见 05_layout/README.md
│   ├── docs/                       ← 版图 / DRC / LVS 过程记录（10 份）
│   ├── mag_bak_v2_20260918/        ← 09-18 版图半成品存档
│   └── mag/
│       ├── ota2_miller.mag         ← 顶层版图源
│       ├── ota2_miller.gds         ← 【交付物】GDSII
│       ├── ota2_miller.spice       ← LVS 版图网表
│       ├── ota2_miller_pext.spice  ← 含寄生后仿网表
│       ├── ota2_miller.ext         ← 提取中间结果
│       ├── sky130_fd_pr__*.mag     ← 8 个器件子 cell
│       └── bak_lvs_pass_20260921/  ← LVS 通过时的完整快照
│
├── run_netgen.sh                   ← LVS 一键脚本
├── run_drc.sh                      ← KLayout 签核 DRC 一键脚本
├── run_postsim.sh                  ← 后仿一键脚本
├── lvs*.log                        ← 13 轮 LVS 迭代日志（最终版 = lvs_report.log）
└── drc_klayout.txt                 ← KLayout 签核 DRC 报告（0 违规）
```

---

## 10. 已完成 / 可继续

### 已完成（全流程闭环）

| 环节 | 产出 | 佐证 |
|---|---|---|
| 规格 & 手算 | `02_sizing/sizing.py` | `sizing_result.txt` |
| 原理图 | `03_sch/ota2_miller.sch` | 网表交叉验证 Av 偏差 0.001 dB |
| 前仿 | `04_sim/ac_bode.txt` | 8 项全达标 |
| 版图 | `05_layout/mag/ota2_miller.mag` | 10 器件 / 88 µm / 四层金属 |
| LVS | `lvs_report.log` | `Circuits match uniquely.` |
| 签核 DRC | `drc_klayout.txt` | 0 违规 |
| 后仿 | `04_sim/ac_bode_post.txt` | GBW −4.5 % |

### 可以继续做的

- 后仿补齐 SR / ICMR / 瞬态建立，与前仿那一套对齐
- 用 `04_sim/plot_bode.py` 把 `ac_bode.txt` 与 `ac_bode_post.txt` 叠一张图
- KLayout LVS 与 netgen 交叉验证（两套独立工具互证）
- 补天线效应（antenna）与金属密度检查，凑齐完整 signoff 清单
- 加 padframe / ESD 结构，向可流片形态再推一步
