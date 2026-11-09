"""Nature-inspired engineering figures with the project's explicit user style."""
import argparse
import json
import os
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.font_manager import FontProperties
from .upstream import ROOT

STYLE = json.loads((ROOT/"configs/figure_style.json").read_text())

def configure_style():
    candidates = [os.environ.get("GO2_ARIAL_BOLD_FONT",""),
                  "/mnt/c/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/arialbd.ttf"]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            font_manager.fontManager.addfont(candidate)
            break
    font = font_manager.findfont(FontProperties(family="Arial", weight="bold"),
                                 fallback_to_default=False)
    if FontProperties(fname=font).get_name() != "Arial":
        raise RuntimeError("Arial Bold required; set GO2_ARIAL_BOLD_FONT")
    plt.rcParams.update({
        "font.family":"Arial", "font.weight":"bold", "font.size":13,
        "axes.labelweight":"bold", "axes.titleweight":"bold",
        "axes.labelsize":14, "axes.titlesize":15, "xtick.labelsize":12,
        "ytick.labelsize":12, "legend.fontsize":12,
        "axes.spines.top":True, "axes.spines.right":True,
        "axes.linewidth":1.5, "xtick.major.width":1.5,"ytick.major.width":1.5,
        "xtick.major.size":5,"ytick.major.size":5,
        "xtick.direction":"in","ytick.direction":"in","xtick.top":True,"ytick.right":True,
        "lines.linewidth":3.2, "lines.linestyle":"-", "axes.grid":False, "legend.frameon":False,
        "svg.fonttype":"none", "pdf.fonttype":42,
        "figure.facecolor":"white", "axes.facecolor":"white"})
    return font

def save(fig, prefix):
    fig.savefig(str(prefix)+".svg", facecolor="white")
    fig.savefig(str(prefix)+".pdf", facecolor="white")
    fig.savefig(str(prefix)+".png", dpi=300, facecolor="white")
    fig.savefig(str(prefix)+".tiff", dpi=600, facecolor="white",
                pil_kwargs={"compression":"tiff_lzw"})
    plt.close(fig)

def draw_comparison(receipts, output):
    font=configure_style()
    labels=list(receipts)
    conditions=[r["name"] for r in next(iter(receipts.values()))["summary"]]
    if any([r["name"] for r in receipts[k]["summary"]]!=conditions for k in labels):
        raise ValueError("Condition ordering differs across policies")
    fig,axes=plt.subplots(1,2,figsize=(12.8,5.5))
    fig.subplots_adjust(left=.075,right=.985,bottom=.25,top=.79,wspace=.30)
    width=.76/len(labels)
    handles=[]
    for j,label in enumerate(labels):
        values=receipts[label]["summary"]
        x=[i-.38+(j+.5)*width for i in range(len(conditions))]
        color=STYLE["series_colors"][label]
        bars=axes[0].bar(x,[100*r["completion_rate"] for r in values],width,
                         color=color,edgecolor="white",linewidth=.6)
        handles.append(bars[0])
        axes[1].bar(x,[r["xy_rmse_mps"] if r["xy_rmse_mps"] is not None else float("nan")
                       for r in values],width,color=color,edgecolor="white",linewidth=.6)
    axes[0].set_ylabel("Completion (%)");axes[0].set_ylim(0,110)
    axes[0].set_yticks([0,25,50,75,100])
    axes[1].set_ylabel("XY tracking RMSE (m/s)\nBefore first failure")
    axes[1].set_ylim(bottom=0)
    for i,ax in enumerate(axes):
        ax.set_xticks(range(len(conditions)),
                      [STYLE["condition_labels"][k] for k in conditions])
        ax.tick_params(axis="x",labelrotation=24)
        for tick in ax.get_xticklabels(): tick.set_ha("right")
        ax.grid(False)
        ax.set_axisbelow(True)
        ax.text(-.12,1.10,chr(97+i),transform=ax.transAxes,fontsize=17,fontweight="bold")
    fig.legend(handles,[STYLE["series_labels"][k] for k in labels],
               loc="upper center",bbox_to_anchor=(.51,.995),ncol=min(2,len(labels)),
               handlelength=1.5,columnspacing=2.0,prop=FontProperties(family="Arial",weight="bold",size=12))
    save(fig,output/"comparison")
    return font

def draw_training(csv_path, output):
    import csv
    configure_style()
    data={}
    with Path(csv_path).open() as f:
        for r in csv.DictReader(f):
            data.setdefault(r["policy"],[]).append((int(r["iteration"]),float(r["mean_reward"])))
    fig,ax=plt.subplots(figsize=(10.2,5.6))
    fig.subplots_adjust(left=.10,right=.98,bottom=.19,top=.79)
    styles={"baseline":"-","dr":"-","history":"-"}
    for label,points in data.items():
        points=sorted(points);x=[v[0] for v in points];y=[v[1] for v in points]
        smooth=[sum(y[max(0,i-24):i+1])/len(y[max(0,i-24):i+1]) for i in range(len(y))]
        color=STYLE["series_colors"][label]
        ax.plot(x,y,color=color,lw=.8,alpha=.20,zorder=1)
        ax.plot(x,smooth,color=color,lw=3.2,ls=styles[label],
                label=STYLE["series_labels"][label],zorder=2)
    ax.set_xlabel("PPO iteration");ax.set_ylabel("Mean training reward")
    ax.set_xlim(0,1499);ax.grid(False)
    ax.legend(loc="lower center",bbox_to_anchor=(.5,1.05),ncol=3,
              prop=FontProperties(family="Arial",weight="bold",size=12))
    save(fig,output/"training_curves")

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,default=ROOT/"reports")
    a=p.parse_args();a.output.mkdir(exist_ok=True,parents=True)
    receipts=json.loads((a.output/"receipts.json").read_text())
    font=draw_comparison(receipts,a.output)
    if (a.output/"training_rewards.csv").exists():
        draw_training(a.output/"training_rewards.csv",a.output)
    print("Font verified:",Path(font).name)
if __name__=="__main__":main()
