import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
OUT=r'D:/BackLab/D/Lab/Cloud/修改稿/els-cas-templates/figs/validation_bars'
labels=['512/5','512/1','1280/5','1280/1','1536/5','1536/1']
pred_t=[23.12,23.22,11.99,12.09,11.36,11.46]; meas_t=[23.69,23.26,11.97,12.13,10.83,11.20]; acc_t=[97.6,99.8,99.8,99.7,95.1,97.7]
pred_c=[33.90,33.88,34.38,34.36,37.83,37.81]; meas_c=[35.10,35.31,37.73,36.47,34.08,35.56]; acc_c=[96.6,96.0,91.1,94.2,89.0,93.7]
plt.rcParams.update({'font.family':'serif','font.serif':['Times New Roman','DejaVu Serif'],
                     'mathtext.fontset':'stix','ps.fonttype':42,'pdf.fonttype':42,'font.size':9})
fig,axes=plt.subplots(1,2,figsize=(8.6,3.0))
colors=['#4C72B0','#DD8452']; x=np.arange(len(labels)); w=0.36
for ax,pv,mv,acc,ylab,ylim,tag in [
    (axes[0],pred_t,meas_t,acc_t,'Execution time (s)',27,'(a)'),
    (axes[1],pred_c,meas_c,acc_c,r'Cost ($10^{-3}$ CNY)',42,'(b)')]:
    ax.bar(x-w/2,pv,w,color=colors[0],edgecolor='black',linewidth=0.5,label='Model-solved',zorder=3)
    ax.bar(x+w/2,mv,w,color=colors[1],edgecolor='black',linewidth=0.5,label='Measured (mean of 3 runs)',zorder=3)
    for xi,p_,m_,a_ in zip(x,pv,mv,acc):
        ax.text(xi,max(p_,m_)+ylim*0.035,f'{a_:.1f}%',ha='center',va='bottom',fontsize=6.2,fontweight='bold',color='#333333')
    ax.set_xticks(x); ax.set_xticklabels(labels,fontsize=7.5)
    ax.set_xlabel('Mapper memory (MB) / reduce tasks'); ax.set_ylabel(ylab); ax.set_ylim(0,ylim)
    ax.grid(True,axis='y',linestyle='--',linewidth=0.4,alpha=0.5,zorder=0)
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
    ax.text(0.02,0.96,tag,transform=ax.transAxes,fontsize=10,fontweight='bold',va='top')
axes[0].legend(loc='upper right',fontsize=6.4,frameon=False)
fig.tight_layout(w_pad=1.2)
fig.savefig(OUT+'.eps',format='eps',bbox_inches='tight'); fig.savefig(OUT+'.png',format='png',dpi=300,bbox_inches='tight')
print('saved')
