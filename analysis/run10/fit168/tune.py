# Coordinate descent on the shape hooks for one algorithm / wet-only slot. usage: tune.py alg slot 'P=v1,v2,...' ...
import sys, os, itertools, shutil, numpy as np
import fit
alg, slot = sys.argv[1], int(sys.argv[2])
grid = {}
for a in sys.argv[3:]:
    k, v = a.split('='); grid[k] = [float(x) for x in v.split(',')]
cur = {k: v[0] for k, v in grid.items()}
cache = {}
def cost(p):
    key = tuple(sorted(p.items()))
    if key in cache: return cache[key]
    out = 'tune/%s' % abs(hash(key)); env = {'T_ALG': alg, 'T_MOD': '0', **{k: str(v) for k, v in p.items()}}
    fit.render('./T', out, env, [slot]); e, t, d = fit.score(out, slot); shutil.rmtree(out)
    c = e + t + 5 * d; cache[key] = (c, e, t, d); return cache[key]
best = cost(cur)
for it in range(3):
    moved = False
    for k in grid:
        for v in grid[k]:
            p = dict(cur, **{k: v}); c = cost(p)
            if c[0] < best[0] - 1e-6: best, cur, moved = c, p, True
    print('pass %d: cost %.3f (env %.2f tone %.2f decay %.0f%%) %s' % (it, best[0], best[1], best[2], 100 * best[3], cur), flush=True)
    if not moved: break
