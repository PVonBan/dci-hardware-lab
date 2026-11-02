exec(open('run9pr/eqcurves.py').read().split("print('== reverb")[0])
hr,pr=resp(111,False),resp(111,True)
print('band  '+' '.join('%6.0f'%c for c in cent))
print('flat U abs L '+' '.join('%6.1f'%v for v in hr[0]))
print('flat ours L  '+' '.join('%6.1f'%v for v in pr[0]))
for n in (109,110):
    h=resp(n,False)-hr; p=resp(n,True)-pr
    for c in (0,1): print('%d U  ch%d '%(n,c)+' '.join('%+6.1f'%v for v in h[c]))
    print('%d ours   '%n+' '.join('%+6.1f'%v for v in p.mean(0)))
