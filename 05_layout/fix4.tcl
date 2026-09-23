# -*- fix4.tcl  单位：LAMBDA（= internal/2）；internal 见 gen_fix4.py -*-
# 补体接触：nfet 体环 -> GND，pfet nwell 连片 -> VDD

# li 扩展：包住 M5 体环下横条右段(3245..3341, 583..617)，上下各撑开 13/13
box 1623 285 1670 315
paint locali

# mcon：x 左右各留 31，y 上下各留 14（sky130 只要求两对边有包围）
box 1638 292 1655 309
paint viali

# metal1：盖住 mcon 并向左引出到 GND 柱上方（实测该走廊 metal1 为空）
box 1450 292 1670 320
paint metal1

# via1：落进 GND 柱 metal2 (2920..2970, 300..640) —— 实测该柱确实是 GND
box 1463 294 1479 320
paint via1

# nwell 桥1：M3 nwell(<=797) <-> M4 nwell(>=1197)，缝 400 全填上并各压 17
box 390 2174 605 2292
paint nwell

# nwell 桥2：M4 nwell(<=2047) <-> M6 nwell(>=3361)，两端各压 7 / 9
box 1020 2174 1685 2292
paint nwell

# li 扩展：包住 M6 左下角 nsubdiff+nsubdiffcont，向左下撑开放 mcon
box 1681 2185 1746 2215
paint locali

# mcon：完全落在新画的 li 内（上下各留 14，左右各留 14/78）
box 1690 2192 1707 2209
paint viali

# metal1：盖住 mcon；y 上沿 4440 与 M6 下栅跳线(4479) 留 39 间距
box 1681 2185 1746 2220
paint metal1

# metal1 竖直上引 x3420..3462：y4746 接上既有 VDD metal1 竖条(3420..3462,4746..6000)
box 1710 2220 1731 2373
paint metal1
