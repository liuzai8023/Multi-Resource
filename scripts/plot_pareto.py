import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
INST=r'D:/BackLab/D/Lab/Cloud/修改稿/Case Study/TaobaoCase/taobao3/instance/TaobaoTraffic3.6GB_final.txt'
OUT=r'D:/BackLab/D/Lab/Cloud/修改稿/els-cas-templates/figs/validation_pareto'
TIERS=[512,640,768]
CONC_NODES={1:4,5:5,10:6,11:7,20:8,55:9}
OBJ_NODES={5:10,11:11,55:12}
COORD={10:13,11:14,12:15}
RED_NODES={512:16,640:17,768:18}
w={}
for line in open(INST, encoding='utf-8'):
    p=line.split()
    if len(p)==4: w[(int(p[0]),int(p[1]))]=(float(p[2]),float(p[3]))
paths=[]
for mi,mem in enumerate(TIERS):
    for conc,cn in CONC_NODES.items():
        for obj,on in OBJ_NODES.items():
            co=COORD[on]
            for red,rn in RED_NODES.items():
                seq=[0,1+mi,cn,on,co,rn,19]
                t=sum(w[(seq[i],seq[i+1])][0] for i in range(6))
                c=sum(w[(seq[i],seq[i+1])][1] for i in range(6))
                paths.append((t,c,mem,obj,red))
def dom(a,b): return a[0]<=b[0] and a[1]<=b[1] and (a[0]<b[0] or a[1]<b[1])
front=[p for p in paths if not any(dom(q,p) for q in paths if q is not p)]
front.sort(key=lambda x:x[0])
plt.rcParams.update({'font.family':'serif','font.serif':['Times New Roman','DejaVu Serif'],
                     'mathtext.fontset':'stix','ps.fonttype':42,'pdf.fonttype':42,'font.size':9})
fig,ax=plt.subplots(figsize=(5.4,3.7))
ax.scatter([p[0] for p in paths],[p[1]*1000 for p in paths],s=12,facecolors='none',
           edgecolors='#9a9a9a',linewidths=0.4,label='Feasible paths',zorder=2)
ax.plot([p[0] for p in front],[p[1]*1000 for p in front],'-o',color='#1f77b4',lw=1.3,ms=3.5,
        label='Pareto front',zorder=3)
val={512:(23.12,0.03390),640:(19.69,0.03461),768:(17.23,0.03485)}
for mem,(t,c) in val.items():
    ax.scatter([t],[c*1000],s=42,marker='s',facecolors='#d62728',edgecolors='k',linewidths=0.5,zorder=5)
offs={512:(-12,-14),640:(6,8),768:(6,8)}
for mem,(t,c) in val.items():
    ax.annotate(f'{mem} MB',(t,c*1000),xytext=offs[mem],textcoords='offset points',
                fontsize=7.5,color='#d62728',fontweight='bold')
ax.scatter([],[],s=42,marker='s',facecolors='#d62728',edgecolors='k',label='Validated configurations',zorder=5)
ax.set_xlabel('Makespan (s)'); ax.set_ylabel(r'Cost ($10^{-3}$ \$)')
ax.set_xlim(14.5,25); ax.set_ylim(33,36)
ax.grid(True,linestyle='--',linewidth=0.4,alpha=0.5)
ax.legend(loc='upper right',fontsize=7,framealpha=0.9)
fig.tight_layout(); fig.savefig(OUT+'.eps',format='eps',bbox_inches='tight')
fig.savefig(OUT+'.png',format='png',dpi=300,bbox_inches='tight')
print('front:',[(round(p[0],2),round(p[1]*1000,2),p[2]) for p in front])
