import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
OUT=r'D:/BackLab/D/Lab/Cloud/修改稿/els-cas-templates/figs/validation_bars'
labels=['512','640','768','1024','1280','1536']
pred_t=[23.12,19.69,17.23,14.13,11.99,11.36]; meas_t=[23.69,19.60,16.80,13.71,11.97,10.83]; acc_t=[97.6,99.6,97.4,96.9,99.8,95.1]
pred_c=[33.90,34.61,34.85,35.25,34.38,37.83]; meas_c=[35.10,35.62,36.29,35.26,37.73,34.08]; acc_c=[96.6,97.2,96.0,100.0,91.1,89.0]
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
        top=max(p_,m_)
        ax.text(xi,top+ylim*0.035,f'{a_:.1f}%',ha='center',va='bottom',fontsize=6.4,fontweight='bold',color='#333333')
    ax.set_xticks(x); ax.set_xticklabels(labels)
    ax.set_xlabel('Mapper memory (MB)'); ax.set_ylabel(ylab); ax.set_ylim(0,ylim)
    ax.grid(True,axis='y',linestyle='--',linewidth=0.4,alpha=0.5,zorder=0)
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
    ax.text(0.02,0.96,tag,transform=ax.transAxes,fontsize=10,fontweight='bold',va='top')
axes[0].legend(loc='upper right',fontsize=6.6,frameon=False)
fig.tight_layout(w_pad=1.2)
fig.savefig(OUT+'.eps',format='eps',bbox_inches='tight')
fig.savefig(OUT+'.png',format='png',dpi=300,bbox_inches='tight')
print('saved')
