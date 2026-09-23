# -*- fix3.tcl  单位：LAMBDA（= internal/2）；internal 见 gen_fix3.py -*-
# 修复 Miller 支路 Rz/Cc：断开 nz<->vout 短路，把 Cc 顶板接到 nz

# 断 nz<->Cc底板：左下簇 m2/m3 之间的 via2 全部擦掉
box 6150 1050 6210 1120
erase via2

# 擦掉误画的 via3：它把 Cc 底板(m3) 与 metal4 顶板引出块焊在一起
box 8715 2535 8765 2585
erase via3

# metal4：x>=12379 压住 Cc 顶板左边框，左端伸到 Cc 外以便落 via3
box 6080 1050 6210 1130
paint metal4

# metal3：完全在 Cc 底板(x>=12300) 与左下簇 m3 环(x>=12292) 之外
box 6010 1060 6118 1112
paint metal3

# via3：metal4 -> metal3
box 6090 1070 6115 1098
paint via3

# metal2：避开 n2 竖柱(<=11980) 60u，右端与左下簇 m2 环重叠并入 nz
box 6020 1060 6260 1112
paint metal2

# via2：metal3 -> metal2
box 6025 1070 6053 1098
paint via2

# via1：metal2 -> metal1(nz 横线 11640..12330)
box 6100 1070 6128 1098
paint via1
