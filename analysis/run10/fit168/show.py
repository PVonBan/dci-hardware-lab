import sys, os, fit
alg, slot = sys.argv[1], int(sys.argv[2]); env = {'T_ALG': alg}
for a in sys.argv[3:]: k, v = a.split('='); env[k] = v
fit.render('./T', 'show', env, [slot]); fit.score('show', slot, True)
