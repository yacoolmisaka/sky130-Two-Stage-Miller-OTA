# =============================================================================
#  lvs_setup_custom.tcl -- 配合 lvs_devices.spice（简化器件定义）的合并规则
# -----------------------------------------------------------------------------
#  器件定义改为单层 MOS（nfet_lvs / pfet_lvs）后：
#    - M 行端口序为 D(1) G(2) S(3) B(4)  → permute 1 3 允许 D/S 互换
#    - 并联合并：l critical + w add
#    - 忽略 magic / xschem 输出中不一致的几何属性
#
#  说明：官方 sky130A_setup.tcl 里对 nfet_01v8 等的规则对 nfet_lvs/pfet_lvs
#  不生效（类名不同），所以这里为简化器件重新定义一套完整的规则。
# =============================================================================

puts ">>> Custom setup: rules for simplified LVS devices (nfet_lvs / pfet_lvs)"

set mosdevs {nfet_lvs pfet_lvs}

foreach dev $mosdevs {
    # D/S 互换（MOS 对称）
    permute "-circuit1 $dev" 1 3
    permute "-circuit2 $dev" 1 3

    # 并联合并：l 相同、w 相加
    property "-circuit1 $dev" parallel enable
    property "-circuit1 $dev" parallel {l critical}
    property "-circuit1 $dev" parallel {w add}
    property "-circuit1 $dev" tolerance {w 0.01} {l 0.01}
    property "-circuit1 $dev" delete as ad ps pd mult sa sb sd nf nrd nrs area perim topography

    property "-circuit2 $dev" parallel enable
    property "-circuit2 $dev" parallel {l critical}
    property "-circuit2 $dev" parallel {w add}
    property "-circuit2 $dev" tolerance {w 0.01} {l 0.01}
    property "-circuit2 $dev" delete as ad ps pd mult sa sb sd nf nrd nrs area perim topography

    puts "    rules enabled: $dev"
}

# 电阻：两端可互换 + 并联合并
foreach dev {sky130_fd_pr__res_xhigh_po_0p69 sky130_fd_pr__res_xhigh_po_0p69_96AYDP} {
    permute "-circuit1 $dev" 1 2
    permute "-circuit2 $dev" 1 2
    property "-circuit1 $dev" parallel enable
    property "-circuit1 $dev" parallel {l critical}
    property "-circuit1 $dev" parallel {w add}
    property "-circuit2 $dev" parallel enable
    property "-circuit2 $dev" parallel {l critical}
    property "-circuit2 $dev" parallel {w add}
}

# 电容：并联合并
foreach dev {sky130_fd_pr__cap_mim_m3_1 sky130_fd_pr__cap_mim_m3_1_PMLRN3} {
    property "-circuit1 $dev" parallel enable
    property "-circuit2 $dev" parallel enable
}

puts ">>> Custom setup done"
