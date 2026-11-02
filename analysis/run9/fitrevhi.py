exec(open('run9pr/fitshelf.py').read().split("m=(cent")[0])
hr=resp(111,False)
for lo_hz,hi_hz in ((600,4000),(600,6400),(1000,3200)):
    m=(cent>=lo_hz)&(cent<=hi_hz)
    for n,g in ((103,-12),(104,-6),(105,6),(106,12)):
        d=(resp(n,False)-hr).mean(0)
        best=min(np.arange(0.1,1.21,0.05), key=lambda s: np.sum((hi2(cent[m],3842,g*s,0.49)-d[m])**2))
        print(lo_hz,hi_hz,n,g,'scale %.2f'%best, 'resid %.2f'%np.sqrt(np.mean((hi2(cent[m],3842,g*best,0.49)-d[m])**2)))
