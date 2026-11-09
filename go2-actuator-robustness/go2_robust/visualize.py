"""Unified figures from saved measurements only; no simulation or training."""
import csv
import json
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from .upstream import ROOT
from .figures import configure_style, STYLE, draw_comparison

plt.rcParams.update({"svg.fonttype":"none", "pdf.fonttype":42})

def save(fig, prefix):
    fig.savefig(str(prefix)+".svg",facecolor="white")
    fig.savefig(str(prefix)+".pdf",facecolor="white")
    fig.savefig(str(prefix)+".png",dpi=300,facecolor="white")
    fig.savefig(str(prefix)+".tiff",dpi=600,facecolor="white",pil_kwargs={"compression":"tiff_lzw"})
    plt.close(fig)

OUTPUT = ROOT/"reports/visualization"
SERIES = ("baseline","dr","balanced")
LABELS = {"baseline":"Official baseline","dr":"Actuator DR","history":"DR + history",
          "balanced":"Balanced DR (+500 iter)"}
LINES = {"baseline":"-","dr":"-","history":"-","balanced":"-"}
METRICS = ["vx","vy","wz","height_m","tilt_deg","torque_rms_Nm",
           "mechanical_power_W","joint_gap_rms_rad"]

def panel(ax, label):
    ax.text(-.09,1.06,label,transform=ax.transAxes,fontsize=17,fontweight="bold")
    ax.grid(False)
    ax.set_axisbelow(True)

def handles(policies=SERIES, extra=None):
    h=[Line2D([],[],color=STYLE["series_colors"][p],lw=3.2,ls=LINES[p],label=LABELS[p])
       for p in policies]
    if extra=="command":h.append(Line2D([],[],color="#20242A",lw=2.4,ls="-",label="Command"))
    if extra=="band":h.append(Patch(facecolor="#AEB6C0",alpha=.25,label="P10–P90 initial states"))
    return h

def legend(fig, policies=SERIES, extra=None):
    fig.legend(handles=handles(policies,extra),loc="upper center",
               bbox_to_anchor=(.52,.995),ncol=2 if extra else 3,
               frameon=False,prop={"family":"Arial","weight":"bold","size":12})

def load_nominal():
    files={
        "baseline":ROOT/"results/nominal_diagnostic_v1/baseline_samples.csv",
        "dr":ROOT/"results/nominal_diagnostic_v1/dr_samples.csv",
        "balanced":ROOT/"results/balanced_s42/samples.csv"}
    arrays={};counts={}
    common=None
    with (OUTPUT/"source_data/nominal_samples.csv").open("w",newline="") as out:
        writer=None
        for policy,path in files.items():
            with path.open() as f:all_rows=list(csv.DictReader(f))
            rows=[r for r in all_rows if r.get("scenario","nominal")=="nominal"]
            rows.sort(key=lambda r:(int(r["step"]),int(r["env_id"])))
            ids=sorted({int(r["env_id"]) for r in rows})
            steps=sorted({int(r["step"]) for r in rows})
            assert len(ids)==16 and len(steps)==600 and len(rows)==9600
            assert len({(r["step"],r["env_id"]) for r in rows})==9600
            fields=[k for k in rows[0] if k!="scenario"]
            if common is None:
                common=fields;writer=csv.DictWriter(out,fieldnames=["policy",*fields]);writer.writeheader()
            assert fields==common
            for row in rows:writer.writerow({"policy":policy,**{k:row[k] for k in common}})
            values={k:np.array([float(r[k]) for r in rows]).reshape(600,16) for k in common}
            assert all(np.isfinite(x).all() for x in values.values())
            arrays[policy]=values
            counts[policy]={"input_rows":len(all_rows),"nominal_rows":len(rows),
                            "other_conditions_not_used_in_nominal_panels":len(all_rows)-len(rows)}
    return arrays,counts

def aggregate(arrays):
    records=[]
    for p,a in arrays.items():
        for i in range(600):
            r={"policy":p,"step":i,"t_start_s":a["t_start_s"][i,0],"t_end_s":a["t_end_s"][i,0]}
            for k in ["cmd_vx","cmd_vy","cmd_wz"]:r[k]=a[k][i,0]
            for k in METRICS:
                r[k+"_mean"]=a[k][i].mean()
                r[k+"_p10"]=np.percentile(a[k][i],10)
                r[k+"_p90"]=np.percentile(a[k][i],90)
            records.append(r)
    with (OUTPUT/"source_data/nominal_aggregates.csv").open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(records[0]));w.writeheader();w.writerows(records)

def speed_response(arrays):
    fig,axes=plt.subplots(3,1,figsize=(12.5,9.1),sharex=True)
    fig.subplots_adjust(left=.10,right=.98,bottom=.08,top=.87,hspace=.24)
    for j,(key,cmd,ylabel) in enumerate([
        ("vx","cmd_vx","Forward speed (m/s)"),
        ("vy","cmd_vy","Lateral speed (m/s)"),
        ("wz","cmd_wz","Yaw rate (rad/s)")]):
        ax=axes[j];panel(ax,chr(97+j))
        for p,a in arrays.items():
            t=a["t_end_s"][:,0];v=a[key]
            color=STYLE["series_colors"][p]
            ax.fill_between(t,np.percentile(v,10,axis=1),np.percentile(v,90,axis=1),
                            color=color,alpha=.14,lw=0)
            ax.plot(t,v.mean(1),color=color,lw=3.2,ls=LINES[p])
        a=arrays["baseline"]
        x=np.r_[a["t_start_s"][:,0],12.];y=np.r_[a[cmd][:,0],a[cmd][-1,0]]
        ax.step(x,y,where="post",color="#20242A",lw=2.4,ls="-",zorder=8)
        ax.set_ylabel(ylabel);ax.set_xlim(0,12);ax.set_xticks(range(0,13,2))
    axes[-1].set_xlabel("Time (s)")
    legend(fig,extra="command")
    save(fig,OUTPUT/"02_velocity_response")

def phase_errors():
    with (ROOT/"reports/precision_segments.csv").open() as f:raw=list(csv.DictReader(f))
    lookup={(r["policy"],r["segment"]):r for r in raw}
    phases=["forward/transition","forward/steady","lateral/transition","lateral/steady",
            "turn/transition","turn/steady"]
    names=["Forward\ntransition","Forward\nsteady","Lateral\ntransition","Lateral\nsteady",
           "Turn\ntransition","Turn\nsteady"]
    fig,axes=plt.subplots(1,2,figsize=(13,5.7),gridspec_kw={"width_ratios":[1.55,1]})
    fig.subplots_adjust(left=.075,right=.98,bottom=.22,top=.79,wspace=.30)
    width=.23
    for j,p in enumerate(SERIES):
        c=STYLE["series_colors"][p]
        axes[0].bar(np.arange(6)+(j-1)*width,
                    [float(lookup[p,k]["xy_rmse_mps"]) for k in phases],width,
                    color=c,edgecolor="white",lw=.6)
        observed=[.5+float(lookup[p,"forward/steady"]["vx_bias_mps"]),
                  .3+float(lookup[p,"lateral/steady"]["vy_bias_mps"])]
        axes[1].bar(np.arange(2)+(j-1)*width,observed,width,color=c,edgecolor="white",lw=.6)
    axes[0].set_xticks(range(6),names);axes[0].tick_params(axis="x",labelsize=11,labelrotation=18)
    axes[0].set_ylabel("XY tracking RMSE (m/s)")
    axes[1].scatter(range(2),[.5,.3],marker="D",s=62,color="#20242A",zorder=6)
    axes[1].set_xticks(range(2),["Forward","Lateral"])
    axes[1].set_ylabel("Mean steady speed (m/s)")
    axes[1].set_ylim(0,.57)
    for i,ax in enumerate(axes):panel(ax,chr(97+i));ax.set_ylim(bottom=0)
    h=handles()+[Line2D([],[],marker="D",ls="none",color="#20242A",label="Command")]
    fig.legend(handles=h,loc="upper center",bbox_to_anchor=(.52,.995),ncol=2,
               prop={"family":"Arial","weight":"bold","size":12})
    save(fig,OUTPUT/"03_error_localization")

def smooth(y,window=5):
    return np.array([y[max(0,i-window+1):i+1].mean() for i in range(len(y))])

def state_cost(arrays):
    fig,axes=plt.subplots(3,2,figsize=(12.8,10.2),sharex=True)
    fig.subplots_adjust(left=.09,right=.98,bottom=.065,top=.90,hspace=.28,wspace=.28)
    entries=[("height_m","Base height (m)"),("tilt_deg","Body tilt (deg)"),
             ("joint_gap_rms_rad","Joint target error (rad)"),("torque_rms_Nm","Actuator torque RMS (N m)"),
             ("mechanical_power_W","Absolute mech. power (W)"),("work","Absolute mech. work (J)")]
    for i,((key,ylabel),ax) in enumerate(zip(entries,axes.flat)):
        panel(ax,chr(97+i));ax.set_ylabel(ylabel);ax.set_xlim(0,12);ax.set_xticks(range(0,13,2))
        for p,a in arrays.items():
            v=np.cumsum(a["mechanical_power_W"]*a["scored"]*.02,axis=0) if key=="work" else a[key]
            t=a["t_end_s"][:,0];color=STYLE["series_colors"][p]
            ax.fill_between(t,np.percentile(v,10,axis=1),np.percentile(v,90,axis=1),
                            color=color,alpha=.14,lw=0)
            raw=v.mean(1)
            ax.plot(t,raw,color=color,alpha=.22,lw=.8)
            ax.plot(t,smooth(raw,5) if key!="work" else raw,color=color,lw=3.2,ls=LINES[p])
        ax.set_ylim(bottom=0)
    for ax in axes[-1]:ax.set_xlabel("Time (s)")
    legend(fig,extra="band")
    save(fig,OUTPUT/"04_state_and_control")

def training_progress():
    with (ROOT/"reports/training_rewards.csv").open() as f:rows=list(csv.DictReader(f))
    with (ROOT/"reports/precision_training.csv").open() as f:fine=list(csv.DictReader(f))
    assert len(rows)==4500 and len(fine)==500
    fig,axes=plt.subplots(1,2,figsize=(13,5.3),gridspec_kw={"width_ratios":[1.55,1]})
    fig.subplots_adjust(left=.075,right=.98,bottom=.15,top=.76,wspace=.27)
    for p in ["baseline","dr","history"]:
        data=[r for r in rows if r["policy"]==p]
        x=np.array([int(r["iteration"]) for r in data]);y=np.array([float(r["mean_reward"]) for r in data])
        axes[0].plot(x,y,lw=.8,alpha=.2,color=STYLE["series_colors"][p])
        axes[0].plot(x,smooth(y,25),lw=3.2,ls=LINES[p],color=STYLE["series_colors"][p])
    x=np.array([int(r["additional_iteration"]) for r in fine])
    y=np.array([float(r["mean_reward"]) for r in fine]);color=STYLE["series_colors"]["balanced"]
    axes[1].plot(x,y,color=color,lw=.8,alpha=.2)
    axes[1].plot(x,smooth(y,25),color=color,lw=3.2,ls=LINES["balanced"])
    axes[0].set_xlim(0,1499);axes[1].set_xlim(0,499)
    axes[0].set_xlabel("Initial PPO iteration");axes[1].set_xlabel("Additional PPO iteration")
    axes[0].set_title("Initial training (1500 iterations)",pad=18)
    axes[1].set_title("Precision fine-tuning (+500)",pad=18)
    for i,ax in enumerate(axes):panel(ax,chr(97+i));ax.set_ylabel("Mean training reward")
    legend(fig,policies=("baseline","dr","history","balanced"))
    save(fig,OUTPUT/"05_training_progress")

def main():
    (OUTPUT/"source_data").mkdir(exist_ok=True,parents=True)
    configure_style()
    STYLE["series_labels"].update(LABELS)
    with (ROOT/"reports/precision_evaluation.csv").open() as f:rows=list(csv.DictReader(f))
    receipts={}
    for r in rows:
        q={k:r[k] for k in ["name"]}
        q.update(completion_rate=float(r["completion_rate"]),xy_rmse_mps=float(r["xy_rmse_mps"]))
        receipts.setdefault(r["policy"],{"summary":[]})["summary"].append(q)
    assert len(rows)==24 and all(len(x["summary"])==6 for x in receipts.values())
    draw_comparison(receipts,OUTPUT)
    for ext in ["png","svg","pdf","tiff"]:
        (OUTPUT/f"comparison.{ext}").rename(OUTPUT/f"01_robustness_overview.{ext}")
    arrays,counts=load_nominal();aggregate(arrays)
    speed_response(arrays);phase_errors();state_cost(arrays);training_progress()
    for file in ["precision_evaluation.csv","precision_segments.csv","training_rewards.csv","precision_training.csv"]:
        (OUTPUT/"source_data"/file).write_bytes((ROOT/"reports"/file).read_bytes())
    (OUTPUT/"data_contract.json").write_text(json.dumps({
        "overview_rows":24,"conditions":6,"policies_overview":4,
        "nominal_trace_counts":counts,"nominal_initial_states_per_policy":16,
        "band":"Pointwise P10-P90 across initial states, not training-seed confidence intervals",
        "state_smoothing":"5-tick trailing mean (0.10 s); raw mean also visible",
        "training_points":5000,"training_smoothing":"25-iteration trailing mean; all raw points visible",
        "fine_tuning_budget":"500 additional iterations; separate axis",
        "history_temporal_panel_omission":"No saved per-environment nominal history-policy trace; remains in all-condition overview and training panel",
        "new_simulations":0,"new_training_runs":0},indent=2))
    print("Saved 5 figure bundles; no new training or simulation.")
if __name__=="__main__":main()
