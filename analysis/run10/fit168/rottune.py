import sys, numpy as np, rotan
grid = {}
for a in sys.argv[1:]: k, v = a.split('='); grid[k] = [float(x) for x in v.split(',')]
U = None; cache = {}
def feats_all(env):
    global U
    acc_u, acc_o = [], []
    for run, clip, lat in rotan.CLIPS:
        if U is None: acc_u.append(rotan.feats(*rotan.load(run, clip, lat)))
        acc_o.append(rotan.feats(*rotan.load(run, clip, lat, './T', env=env)))
    if U is None: U = [np.mean([a[i] for a in acc_u], 0) for i in range(4)]
    return [np.mean([a[i] for a in acc_o], 0) for i in range(4)]
def cost(p):
    key = tuple(sorted(p.items()))
    if key in cache: return cache[key]
    O = feats_all({'T_ALG': '39', **{k: str(v) for k, v in p.items()}})
    c = np.mean(np.abs(U[0] - O[0])[1:]) + 2 * np.mean(np.abs(U[1] - O[1])) + 0.5 * np.mean(np.abs(U[3] - O[3]))
    cache[key] = c; return c
cur = {k: v[0] for k, v in grid.items()}; best = cost(cur)
for it in range(3):
    moved = False
    for k in grid:
        for v in grid[k]:
            p = dict(cur, **{k: v}); c = cost(p)
            if c < best - 1e-6: best, cur, moved = c, p, True
    print('pass %d cost %.3f %s' % (it, best, cur), flush=True)
    if not moved: break
