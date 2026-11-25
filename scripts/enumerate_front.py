#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Enumerate all 648 paths of the case-study DAG and extract the exact Pareto front."""
import os
TIERS=[512,640,768,1024,1280,1536]
CONC_NODES={1:7,5:8,10:9,11:10,20:11,55:12}
OBJ_NODES={5:13,11:14,55:15}
COORD={13:16,14:17,15:18}
RED_NODES={512:19,640:20,768:21,1024:22,1280:23,1536:24}
SINK=25
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
