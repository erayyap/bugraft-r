#!/usr/bin/env python3
"""Offline comparison with directly transcribed PDF Table III; raw results unchanged."""
import argparse,csv,hashlib,json,pathlib,statistics
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter,MultipleLocator

ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=ROOT/'reports/comparison'
SUCCESS={'unrelated_or_unconfirmed_crash','hang_observed_unconfirmed_target','freeze_reported_unconfirmed'}
SOURCE='https://arxiv.org/pdf/2503.20036'

def build_data():
    cases=[];expected_cost=0
    for name in ('five-case-rerun-01','remaining-81-run'):
        run=ROOT/'reports'/name;progress=json.loads((run/'progress.json').read_text())
        assert progress['state']=='completed' and not progress['active'] and not progress['pending']
        expected_cost+=json.loads((run/'usage-summary.json').read_text())['pi_reported_cost_usd']['total']
        for cid,e in progress['finished'].items():
            d=run/e['attempt'];pi=json.loads((d/'pi-result.json').read_text());usage=json.loads((d/'usage.json').read_text())
            assert pi['tool_inventory_valid']
            cases.append({'case_id':cid,'attempt':str(d.relative_to(ROOT)),'outcome':e['outcome'],'assumed_success':e['outcome'] in SUCCESS,'cost_usd':usage['pi_reported_cost_usd']['total'],'agent_seconds':pi['elapsed_seconds'],'usage_warnings':usage['warnings']})
    assert len(cases)==len({c['case_id'] for c in cases})==86
    total=sum(c['cost_usd'] for c in cases);assert abs(total-expected_cost)<1e-7
    count=sum(c['assumed_success'] for c in cases)
    rows=[
        {'system':'Human expert','success_pct':83.0,'cost_usd':28.20,'time_min':20.0,'source':'PDF Table III; human success is agreement-based'},
        {'system':'BugCraft GPT-4.1','success_pct':34.9,'cost_usd':1.16,'time_min':10.0,'source':'PDF Table III'},
        {'system':'BugCraft GPT-4o','success_pct':30.2,'cost_usd':1.45,'time_min':15.56,'source':'PDF Table III'},
        {'system':'OpenAI CUA','success_pct':25.5,'cost_usd':.65,'time_min':6.37,'source':'PDF Table III'},
        {'system':'UI-TARS-1.5-7B','success_pct':0.0,'cost_usd':.02,'time_min':3.27,'source':'PDF Table III'},
        {'system':'Bugcraft-R','success_pct':100*count/86,'cost_usd':total/86,'time_min':statistics.mean(c['agent_seconds'] for c in cases)/60,'source':'Current86 attempts; user-assumed crash/hang/freeze successes'},
    ]
    assert all(r['cost_usd']>0 and r['time_min']>=0 and 0<=r['success_pct']<=100 for r in rows)
    return {'paper_pdf':SOURCE,'paper_table':'III','paper_pdf_sha256':hashlib.sha256((ROOT/'reports/paper-reference/2503.20036.pdf').read_bytes()).hexdigest(),'attempts':86,'assumed_successes':count,'total_pi_estimated_cost_usd':total,'success_assumption':'Per user instruction, observed crash/hang and reported-freeze candidates count as successful; not independently verified target matches. Four reported freezes were separately user-confirmed.','cost_definition':'Mean Pi-estimated model cost over ALL86 attempts, including provider errors/continuations; not billed cost or host/VM expenses.','time_definition':'Mean agent wall-clock per attempt, including continuation and VM pauses, excluding preparation and post-evaluation diagnostics. Not batch elapsed time or time divided by concurrency4. Paper values are Table III Active Time, not human MTTR.','comparability':'Different harnesses and success adjudication; descriptive comparison, not a controlled superiority claim. Human83% is the paper agreement-based estimate.','rows':rows,'cases':cases}

def plot(data,key,filename,title,xlabel,log=False):
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,'axes.spines.right':False})
    fig,ax=plt.subplots(figsize=(10.8,6.6));fig.subplots_adjust(left=.09,right=.97,top=.86,bottom=.24)
    colors=['#64748b','#7c3aed','#ad6ee5','#d97706','#64748b','#087e8b']
    offsets_cost=[(-12,10),(8,13),(8,-16),(-10,-19),(9,12),(12,-4)]
    offsets_time=[(-12,10),(8,12),(8,-15),(-10,-19),(8,12),(12,-4)]
    for i,r in enumerate(data['rows']):
        ours=i==5;x=r[key];y=r['success_pct'];offset=(offsets_cost if log else offsets_time)[i]
        ax.scatter(x,y,s=210 if ours else 85,marker='*' if ours else '^' if i==0 else 'o',color=colors[i],edgecolors='white',linewidths=.8,zorder=4,clip_on=False)
        value=f'${x:.3f}' if log and ours else f'${x:.2f}' if log else f'{x:.2f} min'
        name=r['system']
        ax.annotate(f"{name}\n{y:.1f}% | {value}",(x,y),xytext=offset,textcoords='offset points',ha='right' if offset[0]<0 else 'left',va='center',fontsize=10,fontweight='bold' if ours else 'normal',color=colors[i])
    if log:
        ax.set_xscale('log');ax.set_xlim(.013,65);ax.set_xticks([.02,.05,.1,.2,.5,1,2,5,10,20,50]);ax.xaxis.set_major_formatter(FuncFormatter(lambda x,pos:f'${x:g}'))
    else:ax.set_xlim(0,24);ax.xaxis.set_major_locator(MultipleLocator(5))
    ax.set_ylim(-5,100);ax.set_yticks(range(0,101,20));ax.set_ylabel('Success rate (%)');ax.set_xlabel(xlabel,labelpad=12)
    ax.grid(which='major',color='#dce2e8',linewidth=.8);ax.set_axisbelow(True)
    fig.suptitle(title,x=.09,ha='left',fontsize=19,fontweight='bold',y=.97)
    fig.text(.09,.90,'BugCraft-Bench · 86 Minecraft bug reports',fontsize=11,color='#526174')
    fig.text(.09,.035,f"Cost = mean estimated model USD/attempt. Time = mean agent wall time; setup/diagnostics excluded.\nPaper: arXiv:2503.20036, Table III. Human success is agreement-based; protocols/adjudication differ.",fontsize=8.5,color='#526174',linespacing=1.65)
    for ext in ('png','svg','pdf'):fig.savefig(OUT/f'{filename}.{ext}',dpi=200,facecolor='white')
    plt.close(fig)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--from-data',action='store_true',help='Render the published curated data without private attempt artifacts');args=parser.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    data=json.loads((OUT/'comparison-data.json').read_text()) if args.from_data else build_data()
    data['rows'][-1]['system']='Bugcraft-R'
    (OUT/'comparison-data.json').write_text(json.dumps(data,indent=2)+'\n')
    with (OUT/'comparison-data.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(data['rows'][0]));w.writeheader();w.writerows(data['rows'])
    plot(data,'cost_usd','cost_success','Cost vs success','Mean cost per attempt (USD, logarithmic)',True)
    plot(data,'time_min','time_success','Time vs success','Active time per attempt (minutes, linear)')
    from PIL import Image
    with Image.open(OUT/'cost_success.png') as left,Image.open(OUT/'time_success.png') as right:
        combined=Image.new('RGB',(left.width+right.width,max(left.height,right.height)),'white');combined.paste(left,(0,0));combined.paste(right,(left.width,0));combined.save(OUT/'cost_time_success.png')
    print(json.dumps(data['rows'][-1],indent=2));print('total_cost',data['total_pi_estimated_cost_usd'])
if __name__=='__main__':main()
