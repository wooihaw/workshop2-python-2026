"""Generate sensors.csv and readings.csv for Workshop 2 (stdlib only)."""
import csv, math, random
from datetime import datetime, timedelta
from pathlib import Path

random.seed(20260302)
OUT = Path(__file__).resolve().parent.parent / "data"; OUT.mkdir(parents=True, exist_ok=True)

NODES = ["node-a", "node-b", "node-c", "node-d", "node-e", "node-f"]
START = datetime(2026, 3, 2, 6, 0, 0)
N_TS = 240                       # 240 x 15 min = 60 h = 3 calendar dates
STEP = timedelta(minutes=15)

# ---------------------------------------------------------------- raw signal
grid = []                        # (ts, node, raw_value, hum_raw)
node_off = {n: o for n, o in zip(NODES, [-1.6, -0.9, -0.2, 0.4, 1.1, 1.9])}
for k in range(N_TS):
    ts = START + k * STEP
    hod = ts.hour + ts.minute / 60.0
    diurnal = math.sin((hod - 9.0) / 24.0 * 2 * math.pi)
    for n in NODES:
        raw = 3.2 * diurnal + node_off[n] + random.gauss(0, 0.85)
        hum = 62 - 11 * diurnal - 3.0 * node_off[n] + random.gauss(0, 6.5)
        grid.append([ts, n, raw, max(28.0, min(97.0, hum))])

M = len(grid)                                       # 1440
idx = list(range(M))

# 48 rows lose temp_c (missing-data demo); 48 other rows get duplicated
blank_temp = set(random.sample(idx, 48))
dup_rows = random.sample([i for i in idx if i not in blank_temp], 48)
blank_hum = set(random.sample([i for i in idx if i not in blank_temp], 70))

# the 1440 values that survive as non-null temp_c
kept = [i for i in idx if i not in blank_temp]
multiset = [grid[i][2] for i in kept] + [grid[i][2] for i in dup_rows]

# --------------------------------------------- shape to the slide's statistics
LO, HI, MEAN_C = 16.22, 26.55, 21.3333           # -> 61.2 F, 79.8 F, 70.4 F
rmin, rmax = min(multiset), max(multiset)
norm = [(v - rmin) / (rmax - rmin) for v in multiset]
target = (MEAN_C - LO) / (HI - LO)
g_lo, g_hi = 0.4, 2.5                            # gamma so the mean lands on target
for _ in range(80):
    g = (g_lo + g_hi) / 2
    m = sum(x ** g for x in norm) / len(norm)
    if m > target: g_lo = g
    else: g_hi = g
gamma = (g_lo + g_hi) / 2

def to_c(v):
    x = (v - rmin) / (rmax - rmin)
    return round(LO + (x ** gamma) * (HI - LO), 2)

temp_c = {i: to_c(grid[i][2]) for i in idx}

# nudge for the rounding drift so mean(temp_f) still displays as 70.4
vals = [temp_c[i] for i in kept] + [temp_c[i] for i in dup_rows]
drift = MEAN_C - sum(vals) / len(vals)
movable = [i for i in kept if 18.0 < temp_c[i] < 25.0]
need = int(round(abs(drift) * len(vals) / 0.01))
for i in random.sample(movable, min(need, len(movable))):
    temp_c[i] = round(temp_c[i] + (0.01 if drift > 0 else -0.01), 2)

# --------------------------------------------------- daily t_max / t_min per node
day_vals = {}
for i in idx:
    ts, n = grid[i][0], grid[i][1]
    day_vals.setdefault((n, ts.date()), []).append(temp_c[i])
band = {k: (round(min(v) - 0.30, 2), round(max(v) + 0.30, 2)) for k, v in day_vals.items()}

# ------------------------------------------------------------------- assemble
def messy(node, i):
    """Untidy a few node labels for the .str.strip().str.lower() demo."""
    r = (i * 7919) % 100
    if r < 4:  return " " + node.upper() + " "
    if r < 7:  return node.upper()
    if r < 10: return node + " "
    return node

def fault_of(i):
    t, h = temp_c[i], grid[i][3]
    score = 0.55 * (t - 21.3) - 0.055 * (h - 62) + node_off[grid[i][1]] * 0.35
    return 1 if score + random.gauss(0, 0.85) > 1.55 else 0

rows = []
for i in idx:
    ts, node, _, hum = grid[i]
    lo, hi = band[(node, ts.date())]
    rows.append({
        "ts": ts.strftime("%Y-%m-%d %H:%M:%S"),
        "node": messy(node, i),
        "temp_c": "" if i in blank_temp else f"{temp_c[i]:.2f}",
        "hum": "" if i in blank_hum else f"{hum:.1f}",
        "t_max": f"{hi:.2f}",
        "t_min": f"{lo:.2f}",
        "fault": fault_of(i),
    })

out = rows[:]
for i in dup_rows:                       # exact duplicates for drop_duplicates()
    out.append(dict(rows[i]))
out.sort(key=lambda r: (r["ts"], r["node"].strip().lower()))

FIELDS = ["ts", "node", "temp_c", "hum", "t_max", "t_min", "fault"]
with open(OUT / "sensors.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=FIELDS); w.writeheader(); w.writerows(out)

# ------------------------------------------------------------- readings.csv
BAD = ["", "n/a", "N/A", "--", "ERROR", "21,5", "   ", "null", "23.4C"]
r_rows, start = [], datetime(2026, 3, 5, 8, 0, 0)
bad_at = sorted(random.sample(range(60), 9))
bp = 0
for k in range(60):
    ts = start + k * timedelta(minutes=20)
    node = NODES[k % 3]
    hod = ts.hour + ts.minute / 60.0
    t = 21.3 + 3.0 * math.sin((hod - 9.0) / 24.0 * 2 * math.pi) + random.gauss(0, 0.7)
    h = 62 - 10 * math.sin((hod - 9.0) / 24.0 * 2 * math.pi) + random.gauss(0, 5)
    if k in bad_at:
        value = BAD[bp]; bp += 1
    else:
        value = f"{t:.2f}"
    r_rows.append({"ts": ts.strftime("%Y-%m-%d %H:%M:%S"), "node": node,
                   "temp_c": value, "hum": f"{h:.1f}"})
with open(OUT / "readings.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["ts", "node", "temp_c", "hum"])
    w.writeheader(); w.writerows(r_rows)

# ------------------------------------------------------------------ verify
vals = [float(r["temp_c"]) for r in out if r["temp_c"] != ""]
tf = [v * 9 / 5 + 32 for v in vals]
print(f"sensors.csv  rows={len(out)}  non-null temp_c={len(vals)}")
print(f"  temp_f  count {len(tf)}  mean {sum(tf)/len(tf):.4f}  "
      f"min {min(tf):.4f}  max {max(tf):.4f}")
print(f"  blank temp_c={sum(1 for r in out if r['temp_c']=='')}  "
      f"blank hum={sum(1 for r in out if r['hum']=='')}")
seen, dups = set(), 0
for r in out:
    key = tuple(r[c] for c in FIELDS)
    if key in seen: dups += 1
    seen.add(key)
print(f"  duplicate rows={dups}  "
      f"raw node labels={len({r['node'] for r in out})}  "
      f"clean nodes={len({r['node'].strip().lower() for r in out})}")
print(f"  fault rate={sum(int(r['fault']) for r in out)/len(out):.3f}  "
      f"dates={sorted({r['ts'][:10] for r in out})}")
bad = sum(1 for r in r_rows if not r["temp_c"].strip().replace('.','',1).replace('-','',1).isdigit())
print(f"readings.csv rows={len(r_rows)}  bad temp_c={bad}")
