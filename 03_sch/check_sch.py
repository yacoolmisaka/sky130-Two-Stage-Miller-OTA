import re, sys

UNC = '//wsl$/Ubuntu-2604'
SCH = 'D:/WorkBuddy/workspace/sky130 Two-Stage Miller OTA/03_sch/ota2_miller.sch'
LIB = UNC + '/home/yacool/tools/share/xschem/xschem_library/'

src = open(SCH, encoding='utf-8', errors='replace').read()

wires = []
for m in re.finditer(r'^N ([-\d.]+) ([-\d.]+) ([-\d.]+) ([-\d.]+)\s*(?:\{([^\}]*)\})?',
                     src, re.M):
    x1, y1, x2, y2 = (float(m.group(i)) for i in range(1, 5))
    attr = m.group(5) or ''
    lm = re.search(r'lab=(\S+)', attr)
    wires.append((x1, y1, x2, y2, lm.group(1) if lm else ''))

comps = []
for m in re.finditer(r'C \{([^\}]+)\} ([-\d.]+) ([-\d.]+) (\d+) (\d+) \{([^\}]*)\}', src):
    sym, x, y, attr = m.group(1), float(m.group(2)), float(m.group(3)), m.group(6)
    nm = re.search(r'name=(\S+)', attr)
    lb = re.search(r'lab=(\S+)', attr)
    comps.append((sym, x, y, nm.group(1) if nm else '?', lb.group(1) if lb else ''))

_pincache = {}
def pins(sym):
    if sym in _pincache:
        return _pincache[sym]
    p = LIB + sym if sym.startswith('devices/') else UNC + sym
    out = []
    try:
        for ln in open(p, encoding='utf-8', errors='replace'):
            m = re.match(r'^B \d+ ([-\d.]+) ([-\d.]+) ([-\d.]+) ([-\d.]+)\s*\{name=(\S+)', ln)
            if m:
                a, b, c, d = (float(m.group(i)) for i in range(1, 5))
                out.append(((a + c) / 2, (b + d) / 2, m.group(5)))
    except Exception as e:
        print('  !! cannot read symbol:', sym, e)
    _pincache[sym] = out
    return out

def on_wire(px, py):
    for (x1, y1, x2, y2, _) in wires:
        if x1 == x2 and px == x1 and min(y1, y2) - 1e-6 <= py <= max(y1, y2) + 1e-6:
            return True
        if y1 == y2 and py == y1 and min(x1, x2) - 1e-6 <= px <= max(x1, x2) + 1e-6:
            return True
    return False

print('wires: %d   components: %d\n' % (len(wires), len(comps)))

bad = 0
for (sym, x, y, name, lab) in comps:
    if 'xschem.tcl' in sym:
        print('  [?] stray tcl block  %s' % name)
        continue
    ps = pins(sym)
    if not ps:
        print('  [?] no pin info for %s (%s)' % (name, sym.split('/')[-1]))
        continue
    for (dx, dy, pname) in ps:
        px, py = x + dx, y + dy
        if not on_wire(px, py):
            bad += 1
            print('  [X] %-6s pin %-4s at (%.4g, %.4g)  NOT CONNECTED' % (name, pname, px, py))
    if lab:
        px, py = x, y
        if not on_wire(px, py):
            bad += 1
            print('  [X] %-6s PORT %-6s at (%.4g, %.4g)  NOT CONNECTED' % (name, lab, px, py))

# dangling wire ends (endpoint touched by nothing)
pts = []
for (x1, y1, x2, y2, _) in wires:
    pts.append((x1, y1))
    pts.append((x2, y2))

def touched(px, py):
    hits = 0
    for (x1, y1, x2, y2, _) in wires:
        if (px, py) in ((x1, y1), (x2, y2)):
            hits += 1
        elif x1 == x2 and px == x1 and min(y1, y2) < py < max(y1, y2):
            hits += 1
        elif y1 == y2 and py == y1 and min(x1, x2) < px < max(x1, x2):
            hits += 1
    for (sym, x, y, name, lab) in comps:
        for (dx, dy, pn) in pins(sym) if 'xschem.tcl' not in sym else []:
            if abs(x + dx - px) < 1e-6 and abs(y + dy - py) < 1e-6:
                hits += 1
    return hits

print()
for (x, y) in sorted(set(pts)):
    if touched(x, y) < 2:
        print('  [!] dangling wire end at (%.4g, %.4g)' % (x, y))

print('\nunconnected pins: %d' % bad)
