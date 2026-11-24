#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Enumerate all paths of the 3-tier case-study DAG (162 paths) and the exact front."""
import os
TIERS=[512,640,768]
CONC_NODES={1:4,5:5,10:6,11:7,20:8,55:9}
OBJ_NODES={5:10,11:11,55:12}
COORD={10:13,11:14,12:15}
RED_NODES={512:16,640:17,768:18}
SINK=19
def load(path):
    w={}
    for line in open(path, encoding='utf-8'):
        p=line.split()
        if len(p)==4: w[(int(p[0]),int(p[1]))]=(float(p[2]),float(p[3]))
    return w
def dominates(a,b): return (a[0]<=b[0] and a[1]<=b[1]) and (a[0]<b[0] or a[1]<b[1])
def main():
    base=os.path.dirname(os.path.abspath(__file__))
    inst=os.path.join(os.path.dirname(base),'instance','TaobaoTraffic3.6GB_final.txt')
    w=load(inst); paths=[]
    for mi,mem in enumerate(TIERS):
        for conc,cn in CONC_NODES.items():
            for obj,on in OBJ_NODES.items():
                co=COORD[on]
                for red,rn in RED_NODES.items():
                    seq=[0,1+mi,cn,on,co,rn,SINK]
                    t=sum(w[(seq[i],seq[i+1])][0] for i in range(6))
                    c=sum(w[(seq[i],seq[i+1])][1] for i in range(6))
                    paths.append((t,c,mem,conc,obj,red))
    front=[p for p in paths if not any(dominates(q,p) for q in paths if q is not p)]
    front.sort(key=lambda x:x[0])
    print(f'total paths: {len(paths)}'); print(f'Pareto front size: {len(front)}')
    print(f"{'#':>2} {'mapper':>7} {'conc':>5} {'obj':>4} {'reducer':>8} {'time(s)':>8} {'cost(CNY)':>10}")
    for i,(t,c,mem,conc,obj,red) in enumerate(front,1):
        print(f'{i:>2} {mem:>7} {conc:>5} {obj:>4} {red:>8} {t:>8.2f} {c:>10.5f}')
if __name__=='__main__': main()
