# Compare two replay score files (replay/scores-<tag>.json): which targeted tests a build moved, and by how much.
import json, sys, numpy as np
A, B = (json.load(open(f)) for f in sys.argv[1:3])
for run in sorted(set(A) & set(B)):
    keys = sorted(set(A[run]) & set(B[run]))
    dl = [(abs(B[run][k][0]) - abs(A[run][k][0]), k) for k in keys]; ds = [(B[run][k][1] - A[run][k][1], k) for k in keys]
    better = sum(1 for d, _ in dl if d < -0.3) + sum(1 for d, _ in ds if d < -0.3); worse = sum(1 for d, _ in dl if d > 0.3) + sum(1 for d, _ in ds if d > 0.3)
    print('%s: %d tests, median |level| %.2f -> %.2f dB, median tone %.2f -> %.2f dB; %d measures better, %d worse (> 0.3 dB)' % (
        run, len(keys), np.median([abs(A[run][k][0]) for k in keys]), np.median([abs(B[run][k][0]) for k in keys]),
        np.median([A[run][k][1] for k in keys]), np.median([B[run][k][1] for k in keys]), better, worse))
    for d, k in sorted(dl + ds, reverse=True)[:5]:
        if d > 0.3: print('   worse: %-28s %+.1f dB' % (k, d))
