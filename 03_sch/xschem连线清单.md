# STEP 5 · 在 xschem 里画原理图

> 目的：得到一份**标准原理图**，用于和版图做 LVS。
> 前仿用的 `ota2_miller.sp` 是手写网表，能跑仿真但 netgen LVS 需要**从原理图导出的网表**，
> 所以这步必须做。画完用 xschem 的 `Netlist` 按钮导出 `.spice` 交给 netgen。

> 🔤 **命名约定（全文统一）**：地网络叫 **`GND`**，电源叫 **`VDD`**。
> 原理图端口、器件 `body=` 参数、版图 tap 全部用这两个名字，不要混用别名。
> （手写仿真网表 `ota2_miller.sp` 里的 `vss` 是同一个网，只是仿真文件的写法，改图时不用管。）

---

## 0. 参数版本说明（重要，别用旧参数）

xschem 里用**标准 finger 写法**：**`W` = 总宽，`nf` = 指数**，单指宽 = `W / nf`。
而 `ota2_miller.sp` 里的 `m=` 是**绕过 PDK 缺陷的仿真写法**。

> ## ⚠️ 最关键的一条：sky130 里 `w` 是「总宽」，不是「单指宽」
>
> 三条证据都指向同一结论：
> 1. PDK 教程里 `w=3 nf=3` → 每指 1 µm，原文写明 "Width is counted as total width"；
> 2. 前仿时实测过：**`nf` 不倍增电流**（W_eff 只认 `w`）—— 如果 `w` 是单指宽，
>    `nf` 就必须倍增电流，两者直接矛盾；
> 3. Magic 的 sky130 器件生成器里 `w` 也是总宽，按 `nf` 折成手指。
>
> **所以原理图里 `W` 要填总宽：M5 填 24、M6 填 56、M7 填 62.5**，不是 2 / 2.5。
> 填成单指宽的话，实际器件会小 12~28 倍；而且单指宽会变成 0.07~0.1 µm，
> 低于 poly 最小线宽 → 版图直接 DRC 报错。
>
> **那为什么仿真网表要用 `m=`？** 因为本 PDK 的模型对 `w ≥ 10` 会落进 bin 边界外，
> 运行时算出负的 Pclm/Drout/Eta0 直接 fatal。所以仿真时要把「总宽」拆成
> 「单指宽 × m=」：`W=24 nf=12` → 仿真写 `w=2 nf=1 m=12`。两者电学等价。
> （后仿提取的网表可能遇到同样问题，到 STEP 7 处理。）

| 器件 | 仿真网表写法（`ota2_miller.sp`） | **xschem 原理图写法** | 等效总宽 | 单指宽 |
|---|---|---|---|---|
| M1, M2 | w=2 nf=1 m=2 | **W=4u nf=2 L=1u** | 4 µm | 2 µm |
| M3, M4 | w=2 nf=1 m=2 | **W=4u nf=2 L=1u** | 4 µm | 2 µm |
| M5 | w=2 nf=1 m=12 | **W=24u nf=12 L=1u** | 24 µm | 2 µm |
| M6 | w=2 nf=1 m=28 | **W=56u nf=28 L=1u** | 56 µm | 2 µm |
| M7 | w=2.5 nf=1 m=25 | **W=62.5u nf=25 L=1u** | 62.5 µm | 2.5 µm |
| Mref | w=2.5 nf=1 m=5 | **W=12.5u nf=5 L=1u** | 12.5 µm | 2.5 µm |
| Cc | 1.2 pF | **1.2 pF** | — | — |
| **Rz** | 3 kΩ（新增） | **3 kΩ**（新增） | — | — |

---

## 1. 启动

```bash
cd "/mnt/d/WorkBuddy/workspace/sky130 Two-Stage Miller OTA/03_sch"
xschem &
```

新建 `ota2_miller.sch`。器件从库里取，符号在
`$PDK_ROOT/sky130A/libs.tech/xschem/sky130_fd_pr/` 下（`nfet_01v8.sym` / `pfet_01v8.sym`）。

---

## 1.5 器件符号对照表（Rz / Cc / Iref 到底叫什么、在哪）

PDK 符号库根目录（本项目实测路径）：

```
~/sky130_volare_pdk/volare/sky130/versions/c6d73a35f524070e85faff4a6a9eef49553ebc2b/sky130A/libs.tech/xschem/sky130_fd_pr/
```

| 器件 | 符号文件名 | 所在库 | 说明 |
|---|---|---|---|
| **Rz** 3 kΩ | **`res_xhigh_po_0p69.sym`** | sky130_fd_pr | P- 多晶，**2000 Ω/□**；**本设计实际采用**：W=0.69 µm、L=1.035 µm |
| Rz（早期备选，**已弃用**） | `res_high_po_0p69.sym`（或 `_1p41`） | sky130_fd_pr | P+ 多晶精密电阻，**320 Ω/□**，固定宽度 0.69 / 1.41 µm；曾推荐，最终未采用 |
| **Cc** 1.2 pF | `cap_mim_m3_1.sym` | sky130_fd_pr | MIM 电容 **2 fF/µm²**，需 ≈ 600 µm²（约 25 × 24 µm） |
| Cc（备选） | `cap_mim_m3_2.sym` | sky130_fd_pr | 同为 2 fF/µm²，走 M4 / Via4 版本 |
| **Iref** 10 µA | `isource.sym` | **xschem 自带库**（`…/xschem/xschem_library/devices/`） | 理想电流源，**只在测试台用，不进 LVS** |
| VDD / GND | `vdd.sym` / `gnd.sym` | 自带库 devices | — |
| 端口 | `ipin.sym` / `opin.sym` / `iopin.sym` | 自带库 devices | vinm/vinp 用 ipin，vout 用 opin，电源用 iopin |

**尺寸估算**（画版图时会用到）：

- Rz = 3 kΩ 用 **`res_xhigh_po`**（2000 Ω/□）：方块数 = 3000 / 2000 = **1.5** → 长度 **L = 1.035 µm**（W 固定 0.69 µm）✅ 本设计采用
  （另一种 `res_high_po`，320 Ω/□，需 ≈ 6.5 µm —— 早期推荐，**已弃用**，见下方 ⚠️ 说明）
- Cc = 1.2 pF 用 MIM：2 fF/µm² → **面积 ≈ 600 µm²**，约 **25 µm × 24 µm**

**怎么改阻值**：这些符号**宽度是固定的，只有 `L` 一个可调参数**（实例属性里改 `L`，`mult` 保持 1）。

```
R = RSH × ( mult × L / W )        方块数 = mult × L / W
```

xschem 在符号下方自动显示这两行 —— 上面一行是方块电阻 RSH，下面一行就是方块数：

| 符号 | RSH | 3 kΩ 需要的方块数 | W=0.69 µm 时 L |
|---|---|---|---|
| **`res_xhigh_po_0p69`** | 2000 | **1.5** | **1.035 µm ✅ 本设计实际采用**（1.035 / 0.69 = 1.5 方块 × 2000 = 3 kΩ） |
| `res_high_po_0p69` | 320 | 9.4 | 6.5 µm（早期推荐，**已弃用**） |
| `res_high_po_1p41` | 320 | 9.4 | 13.2 µm（宽版，匹配更好、面积大） |
| `res_xhigh_po_5p73` | 2000 | 1.5 | 8.6 µm（要留 xhigh 家族时的折中） |

> ⚠️ **本设计定案：`sky130_fd_pr__res_xhigh_po_0p69`，W = 0.69 µm、L = 1.035 µm。**
> 依据是导出网表里的 `XRz net4 net2 GND sky130_fd_pr__res_xhigh_po_0p69 L=1.035 mult=1`。
> 早期「xhigh 太短、端头 head 电阻占比大、阻值不准」的分析仍然成立，但
> **「推荐换成 `res_high_po_0p69`」这条已作废** —— 图已经这么画了、网表也做过交叉验证，
> **版图必须照 `res_xhigh_po_0p69` 摆**；换成 res_high_po 会让 STEP 8 的 netgen LVS 直接 device mismatch。
> 代价是 README §1.5 记录的那约 1° PM 偏差，属预期内。

> 精度要求宽松（Rz 只是调零电阻，±20% 对 PM 影响很小），所以按上表取整即可。

> ⚠️ **Rz 的 `B` 脚必须接 GND！** `res_*_po` 符号是 **3 端**（两端 + 衬底 `B`）。
> B 悬空的话 xschem 导出网表会报未连接引脚，仿真也跑不起来。接 GND 即可。

**怎么改容值（Cc）**：`cap_mim_m3_1` 有 `w` / `l` 两个可调参数，`MF` 保持 1。

```
C[fF] = 2.0 × (W × L) + 0.38 × (W + L)        (W、L 单位 µm)
```

拿 W = L = 1 验算：2.0 + 0.76 = **2.76 fF** —— 正是符号默认显示的 `C=2.76e-15`。

| W × L (µm) | C |
|---|---|
| 24 × 24 | 1.170 pF |
| **24.3 × 24.3** | **1.200 pF** ✅ |
| 24.5 × 24.5 | 1.219 pF |
| 25 × 25 | 1.269 pF |

> MIM 容值工艺本身就有 ±10% 偏差（CMIMA 1.8~2.2 fF/µm²），别抠小数点 ——
> 改完看符号下面 `C=` 那行读到 1.2e-12 附近就行。
> 另外这 ~590 µm² 是版图里最大的单个器件，版图阶段可以考虑把它盖在放大管上方省面积。

> ⚠️ **LVS 关键**：Rz / Cc 必须用 **PDK 符号**，**不能**用自带库的 `res.sym` / `cap.sym`。
> 版图里 Magic 从 poly/MIM 层提取出来的就是 `sky130_fd_pr__res_xhigh_po_0p69` / `cap_mim_m3_1`
> 这类子电路；原理图若用理想 R/C，netgen 直接报 device mismatch。
> （理想 R/C 只在 §3 的"前仿等价性自检"里临时用。）

---

## 2. 连线清单（照这个连）

内部节点命名（和网表保持一致，方便对照）：

| 节点名 | 是什么 |
|---|---|
| `n1` | M1 漏 / M3 漏 / M3 栅 / M4 栅（电流镜栅极节点） |
| `n2` | M2 漏 / M4 漏 / **Rz 一端**（第一级输出，高阻节点） |
| `nz` | **Rz 另一端 / Cc 一端**（本次新增的中间节点） |
| `ntail` | M1 源 / M2 源 / M5 漏（尾节点） |
| `vout` | M6 漏 / M7 漏 / Cc 另一端 |

### 器件逐个摆（符号端口顺序是 **D G S B**，别接错）

| 器件 | 类型 | D 接 | G 接 | S 接 | B 接 | 参数 |
|---|---|---|---|---|---|---|
| **M1** | nfet_01v8 | `n1` | `vinm` | `ntail` | `GND` | W=4u L=1u nf=2 |
| **M2** | nfet_01v8 | `n2` | `vinp` | `ntail` | `GND` | W=4u L=1u nf=2 |
| **M3** | pfet_01v8 | `n1` | **`n1`**（二极管连接） | `VDD` | `VDD` | W=4u L=1u nf=2 |
| **M4** | pfet_01v8 | `n2` | `n1` | `VDD` | `VDD` | W=4u L=1u nf=2 |
| **M5** | nfet_01v8 | `ntail` | `vbias` | `GND` | `GND` | W=24u L=1u **nf=12** |
| **M6** | pfet_01v8 | `vout` | `n2` | `VDD` | `VDD` | W=56u L=1u **nf=28** |
| **M7** | nfet_01v8 | `vout` | `vbias` | `GND` | `GND` | W=62.5u L=1u **nf=25** |
| **Mref** | nfet_01v8 | `vbias` | **`vbias`**（二极管连接） | `GND` | `GND` | W=12.5u L=1u nf=5 |
| **Rz** | 电阻 | `n2` | — | `nz` | — | **3 kΩ** |
| **Cc** | 电容 | `nz` | — | `vout` | — | 1.2 pF |
| **Iref** | 电流源 | VDD → `vbias`，10 µA | | | | |

**补偿支路拓扑（注意别接错）**：
```
n2 ──[Rz 3k]── nz ──[Cc 1.2p]── vout
```
Rz 和 Cc **串联**跨接在第一级输出与输出节点之间，中间多出一个 `nz` 节点。

**极性检查（画完务必确认）**：`vinp` 上升 → M2 电流↑ → `n2` 下降 → M6 的 Vsg↑ → M6 电流↑ → `vout` 上升。
所以 **vinp 是同相端、vinm 是反相端**。反了就把 M1/M2 的栅对调。

> 💡 **3 端符号的衬底走 `body=` 参数，且必须和端口名一致！**
> `nfet3_01v8` / `pfet3_01v8` 没有 B 引脚，衬底由实例属性 **`body=`** 决定（默认 `GND`）。
> 本设计地网络统一叫 **`GND`**（电源叫 `VDD`），所以：
> - **5 个 NMOS（M1/M2/M5/M7/Mref）：`body=GND`** ← 就是符号默认值，不用改
> - **3 个 PMOS（M3/M4/M6）：`body=VDD`**
>
> ⚠️ **`body=` 的值必须是电路里真实存在的网络。** SPICE 里 `.subckt` 内部、又没出现在端口列表上的
> 网络是**局部节点** —— 要是图里既没有叫 `GND` 的 `iopin`、也没有任何 `GND` 连线，
> 那这个 `GND` 只存在于子电路内部，衬底相当于悬空（仿真会出错，LVS 也对不上）。
> 所以图上**必须有一个名字叫 `GND` 的 `iopin.sym`**。
>
> 另外，**`gnd.sym` 不能当端口用**：它只是个图形，不会让网络进子电路的端口列表 ——
> 端口只能由 `ipin` / `opin` / `iopin` 产生。

### 端口（用 xschem 的 `ipin` / `opin` / `iopin`）

| pin | 方向 | 连到 |
|---|---|---|
| `vinm` | in | M1 栅 |
| `vinp` | in | M2 栅 |
| `vout` | out | M6 漏 / M7 漏 |
| `vbias` | in | M5 栅 / M7 栅 / Mref |
| `VDD` | inout | 电源 |
| `GND` | inout | 地 |

> 💡 **VDD / GND 用 `iopin.sym`，别用 `vdd.sym` / `gnd.sym`。**
> `vdd.sym` / `gnd.sym`（自带库 devices 里）是**全局电源标志**，只用在顶层测试台 `tb_ota.sch`
> —— 那里的 GND 正好可以当 ngspice 的 0 节点。
> 本图里 VDD/GND 是**子电路的端口**，用 `vdd/gnd` 标志会让它们变成全局网络、不出现在端口列表里，
> 导出的 `.subckt ota2_miller vinm vinp vout vdd vss vbias` 就少了两个脚 → LVS 直接 mismatch。

> ⚠️ **LVS 关键**：测试台（激励源、CL、Lfb、Cin）**不要**画进这个 `.sch`。
> 单独建 `tb_ota.sch` 放测试台。这样 LVS 时原理图侧只有 8 管 + Rz + Cc + Iref，
> 和版图一一对应，不会 mismatch。
>
> 另：Iref 是片外基准电流，通常也不进版图；LVS 时按需决定保留或删除。

---

## 3. 导出网表

xschem 里：`Netlist` 按钮 → 生成 `ota2_miller.spice`。

### ⚠️ 网表默认生成在哪

`xschemrc` 里 `netlist_dir` 的**默认值是 `~/.xschem/simulations/`**，不是原理图目录。
所以点完 `Netlist` 按钮，要去那里找 `ota2_miller.spice`：

```bash
cat -n ~/.xschem/simulations/ota2_miller.spice
```

（想改成本目录输出，在 `xschemrc` 里设 `set local_netlist_dir 1`。）

### ⚠️ 两个必须处理的坑（不处理仿真直接挂）

导出的内容长这样：

```
** sch_path: /mnt/d/.../03_sch/ota2_miller.sch
**.subckt ota2_miller GND vinp vinm vout vbias VDD
*.iopin GND
...
**.ends
.end
```

| 坑 | 后果 | 处理 |
|---|---|---|
| **`**.subckt` / `**.ends`** —— 开头两个星号是 **xschem 的层次化标记** | SPICE 里 `*` 是注释符，`**` 更是整行注释 → **整个子电路等于没定义**，ngspice 报 `Error: unknown subckt` | 去掉前两个星号，还原成 `.subckt` / `.ends` |
| **末尾的 `.end`** | 被 `.include` 进来会让 ngspice **提前结束解析**，后面的器件全部读不到 | 整行删掉 |

`04_sim/sch2sim.py` 已经内置了这两条处理，所以**导出后必须过一遍它**再用。

### ⚠️ 端口顺序和手写网表不一样！

| | 端口顺序 |
|---|---|
| 手写 `ota2_miller.sp` | `vinm vinp vout vdd vss vbias` |
| **xschem 导出** | **`GND vinp vinm vout vbias VDD`** |

给测试台写 `XOTA` 那一行时，别照抄手写版的顺序，否则六个脚全接错。

### 检查导出内容
- `.subckt` 那行有 6 个端口：`GND vinp vinm vout vbias VDD`
- 器件行形如 `XM1 net1 vinm net3 GND sky130_fd_pr__nfet_01v8 L=1 W=4 nf=2`（**W 是总宽**）
- 补偿支路是 `XRz net4 net2 GND ...` + `XCc net4 vout ...`

**交叉验证（强烈建议做）**：原理图导出网表和手写仿真网表应该电学等价。
但导出的网表里 `w` 是**总宽**（24 / 56 / 62.5，全都 ≥ 10），直接喂 ngspice 会撞 bin 边界 fatal，
所以先用 `04_sim/sch2sim.py` 把「总宽」拆成「单指宽 × m=」：

```bash
python3 "/mnt/d/WorkBuddy/workspace/sky130 Two-Stage Miller OTA/04_sim/sch2sim.py" ota2_miller.spice
# -> ota2_miller_sim.spice     (W=24 nf=12  ->  w=2 nf=1 m=12)
```

再拿它跑一次 AC，结果应该和 `ota2_miller.sp` 几乎一致。
不一致就说明原理图连错了 —— 这是画完原理图最有效的自检。

---

## 4. 常见坑

| 现象 | 原因 |
|---|---|
| 器件参数改了仿真没变 | 改的是 symbol 默认值而非 instance 属性；要在 instance 上填 W/L/nf |
| 网表里 pin 顺序不对 | sky130 符号是 **D G S B**，别按 G D S B 连 |
| `nf` 没导出 | 在器件属性里显式填 `nf=2`（不能只填 W） |
| 管子电流只有设计的 1/N（小十几倍） | 把 `W` 当成「单指宽」填了。sky130 里 **`W` 是总宽**，见 §0 |
| 版图里单指宽只有 0.1 µm、DRC 报错 | 同上，`W` 填成单指宽导致 `W/nf` 过小 |
| 导出的网表带 `m=` 导致 LVS 失败 | LVS 用原始导出版（nf 版），仿真才用 m= 版 |
| 找不到器件符号 | 检查 `xschemrc` 里的 `XSCHEM_LIBRARY_PATH` 是否指向 `$PDK_ROOT/.../libs.tech/xschem` |
| 电阻符号导出成子电路 | **这是正常的**——PDK 电阻本来就是子电路，LVS 就靠它跟版图对上。**别**换成 `devices/res.sym`（见 §1.5 的 LVS 警告） |

---

## 附录 · 本次踩过的坑与走过的弯路（2026-09-13）

> 这一节是**事后总结**。画图时先照 §0~§4 走，卡住了再回来翻这里。
> 下面每一条都是真的撞过一次才记下来的。

| # | 坑 | 当时的错法 | 正确做法 |
|---|---|---|---|
| 1 | **`W` 是总宽还是单指宽** | 把 `W` 当单指宽填（M7 填 `W=2.5 nf=25`） | sky130 里 **`w` 就是总宽**，`nf` 只负责分手指。M7 应填 `W=62.5 nf=25` |
| 2 | **地网络名不统一** | 端口写 `VSS`，衬底参数却是 `body=GND` | 全项目统一叫 **`GND`**（电源 `VDD`），`body=` 跟着一起改 |
| 3 | **用 `gnd.sym` 当端口** | 图里放个地符号就当接地了 | `gnd.sym` 只是图形，**不产生端口**；端口必须用 `iopin.sym`（name 填 GND） |
| 4 | **衬底悬空** | 3 端符号的 `body=GND`，但图上根本没有 GND 这个网络 | SPICE 里子电路内未列进端口的网络 = **局部节点**，等于衬底浮空 |
| 5 | **电阻用了自带库 `res.sym`** | 图省事用理想电阻 | 必须用 PDK 的 `res_xhigh_po_0p69`（本设计定案型号）；版图提取出来是子电路，理想 R 会 device mismatch |
| 6 | **选错 PDK 变体** | 在 `sky130B` 目录下找器件 | 本项目统一 **sky130A**（`models.inc` 指向 A；B 多一层 ReRAM、寄生参数不同） |
| 7 | **3 kΩ 电阻选了 xhigh_po** | 当时判断「`res_xhigh_po`（2000 Ω/□）只要 1 µm 长，太短、head 电阻占比大」，想换成 `res_high_po`（320 Ω/□）取 ≈ 6.5 µm | ⚠️ **结论已推翻**：最终定案仍用 **`res_xhigh_po_0p69`（L=1.035）**，见 §1.5 的定案说明。**版图照 xhigh 摆**，别再换 res_high_po（会 LVS mismatch） |
| 8 | **M3 / M4 / M6 画成了 NMOS** | 三个全用 `nfet_01v8` | 它们是 **PMOS**，要用 `pfet_01v8.sym` |
| 9 | **输入端极性接反** | vinp 接到 M1、vinm 接到 M2 | **vinp → M2**（漏接 n2，同相端），**vinm → M1**；接反闭环变正反馈 |
| 10 | **`vp()` 读出来是弧度** | 以为 PM 只有 0.86°，以为电路要振荡 | ngspice 的 `vp()` 输出**弧度**，×180/π 之后 PM = 50.3°，一直是稳的 |

### 三条方法论

- **判输入极性**：别看图上的 (+)/(−) 标记，看「哪个管子的漏极接到 `n2`（第二级栅）」——那一侧才是同相端。
- **判参数对不对**：改完看符号下面那两行实时读数（阻值 / 容值 / 方块数），别只信自己填的数。
- **判网络是否真连上**：`.subckt` 里既没出现在端口列表、又没被 `ipin`/`opin`/`iopin` 标住的网络 = 局部节点，等于没连。
