import sys, itertools, shutil, fit
alg, slot = sys.argv[1], int(sys.argv[2]); fixed = {'T_ALG': alg}; grid = {}
for a in sys.argv[3:]:
    k, v = a.split('=')
    if ',' in v: grid[k] = v.split(',')
    else: fixed[k] = v
res = []
for combo in itertools.product(*grid.values()):
    env = dict(fixed, **dict(zip(grid, combo))); out = 'g/' + '_'.join(combo)
    fit.render('./T', out, env, [slot]); e, t, d = fit.score(out, slot); shutil.rmtree(out)
    res.append((e + t + 5 * d, e, t, d, combo))
for r in sorted(res)[:6]: print('cost %.3f env %.2f tone %.2f decay %.0f%% %s' % (r[0], r[1], r[2], 100 * r[3], dict(zip(grid, r[4]))))
