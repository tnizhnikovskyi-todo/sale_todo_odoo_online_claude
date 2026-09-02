# -*- coding: utf-8 -*-
import json, io, statistics as st
p = json.load(io.open('data/price.json', encoding='utf-8'))
R = p['_ставки']; rate=R['ставка_клієнту_€_год']; cost=R['собівартість_€_год']; res=R['резерв_на_scope']
rows=[]
for g in p['групи']:
    for it in g['items']:
        inc=len(it['inc']); cum=inc
        prev_h=None
        for i,(name,h,sav,sig,add) in enumerate(it['lv']):
            cum += len(add) if i>0 else 0
            price = round(h*rate/50)*50
            cost_res = h*(1-sav/100)*cost*(1+res)
            cost_nores = h*(1-sav/100)*cost
            m_res = price-cost_res; m_nores=price-cost_nores
            dh = None if prev_h is None else h-prev_h
            dn = len(add) if i>0 else None
            rows.append(dict(g=g['g'],id=it['id'],n=it['n'],lvl=i+1,lname=name,h=h,sav=sav,pts=cum,
                             price=price,cost_res=cost_res,cost_nores=cost_nores,m_res=m_res,m_nores=m_nores,
                             mp_res=m_res/price*100, mp_nores=m_nores/price*100, hpp=h/cum, dh=dh, dn=dn,
                             hpadd=(dh/dn if dn else None)))
            prev_h=h
# 1. margin table
print("id lvl h sav pts price cost_res margin_res %res cost_nores margin_nores %nores h/pt dh dn h/added")
for r in rows:
    print(f"{r['id']:5} L{r['lvl']} {r['h']:3d} {r['sav']:3d}% {r['pts']:2d} €{r['price']:5d} €{r['cost_res']:6.1f} €{r['m_res']:7.1f} {r['mp_res']:5.1f}% €{r['cost_nores']:6.1f} €{r['m_nores']:7.1f} {r['mp_nores']:5.1f}% {r['hpp']:4.2f} {str(r['dh']):>4} {str(r['dn']):>4} {('%.1f'%r['hpadd']) if r['hpadd'] else '-':>5}")
print()
# 2. margin % depends only on savings
print("Margin% by savings only (with reserve / without):")
for s in sorted(set(r['sav'] for r in rows)):
    print(f"  sav {s:2d}%: with reserve {100*(1-(1-s/100)*cost*(1+res)/rate):5.1f}%   without {100*(1-(1-s/100)*cost/rate):5.1f}%")
print()
# 3. totals
tot_h=sum(r['h'] for r in rows if r['lvl']==2); print("sum L2 hours all 26:",tot_h)
print("hours per point stats L1:", st.mean([r['hpp'] for r in rows if r['lvl']==1]), min(r['hpp'] for r in rows if r['lvl']==1), max(r['hpp'] for r in rows if r['lvl']==1))
for L in (1,2,3):
    xs=[r['hpp'] for r in rows if r['lvl']==L]
    print(f"L{L} h/pt mean {st.mean(xs):.2f} median {st.median(xs):.2f} min {min(xs):.2f} max {max(xs):.2f}")
print()
# 4. sorted by hours per point, L2 and L3
for L in (2,3):
    print(f"--- L{L} sorted by hours/added point")
    for r in sorted([r for r in rows if r['lvl']==L], key=lambda r:r['hpadd']):
        print(f"  {r['id']:5} {r['n']:28} +{r['dh']:2d}h / +{r['dn']} pts = {r['hpadd']:.1f} h/added; total {r['h']}h {r['pts']}pts {r['hpp']:.2f}h/pt")
print()
# 5. sensitivity: actual hours = k * estimate, price fixed; margin with reserve considered as buffer: cost_actual = k*h*(1-sav)*15 (no extra reserve)
print("Sensitivity: actual hours factor k, margin% (price fixed) — cost=k*h*(1-sav)*15, compare to reserve cost")
for s in (20,25,30,35,40):
    line=f"  sav {s}%: "
    for k in (1.0,1.2,1.5,2.0,2.5):
        mp=100*(1-k*(1-s/100)*cost/rate)
        line+=f"k={k}:{mp:5.1f}%  "
    print(line)
print()
# breakeven factor k where margin=0: k = rate/((1-s)*cost)
for s in (0,20,25,30,35,40):
    print(f"  sav {s}%: margin hits 0 at actual/estimate = {rate/((1-s/100)*cost):.2f}x ; reserve covers up to {1+res:.2f}x")
print()
# 6. avg project mix: 4 positions at L2 (Base L2 + 3 modules) - using concept 'середній проєкт' 80 h
# distribution of prices
import collections
print("Total L1/L2/L3 hours per group:")
for g in p['групи']:
    hs=[[it['lv'][i][1] for it in g['items']] for i in range(3)]
    print(f"  {g['g']:32} L1 {sum(hs[0]):3d}  L2 {sum(hs[1]):3d}  L3 {sum(hs[2]):3d}")
json.dump(rows, io.open('rows.json','w',encoding='utf-8'), ensure_ascii=False, indent=1)
