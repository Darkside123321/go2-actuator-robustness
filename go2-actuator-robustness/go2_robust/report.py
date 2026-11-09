"""Export small, trackable engineering receipts; raw logs/checkpoints stay ignored."""
import argparse
import csv
import json
from pathlib import Path
from .upstream import ROOT

def gate(rows, limits):
    r={x["name"]:x for x in rows}
    checks={
        "nominal_completion":r["nominal"]["completion_rate"]>=limits["nominal_min_completion_rate"],
        "nominal_tracking":r["nominal"]["xy_rmse_mps"] is not None and r["nominal"]["xy_rmse_mps"]<=limits["nominal_max_xy_rmse_mps"],
        "delay40_completion":r["delay40"]["completion_rate"]>=limits["delay40_min_completion_rate"],
        "soft_delay40_completion":r["soft_delay40"]["completion_rate"]>=limits["soft_delay40_min_completion_rate"]}
    return {"passed":all(checks.values()),"checks":checks}

def fmt(value):
    return "n/a" if value is None else f"{value:.3f}"

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,default=ROOT/"reports")
    p.add_argument("--result",action="append",help="label=directory; may repeat")
    a=p.parse_args()
    inputs=a.result or ["baseline="+str(ROOT/"results/baseline_v1"),
                       "dr="+str(ROOT/"results/dr_s42"),
                       "history="+str(ROOT/"results/history_s42")]
    limits=json.loads((ROOT/"configs/acceptance.json").read_text())
    rows=[];receipts={};verdicts={}
    for item in inputs:
        label,path=item.split("=",1);directory=Path(path)
        manifest=json.loads((directory/"manifest.json").read_text())
        if not manifest["success"]:raise ValueError("Incomplete run: "+label)
        data=json.loads((directory/"summary.json").read_text())
        receipts[label]={"checkpoint_sha256":manifest["checkpoint_sha256"],
                         "evaluation_spec":manifest["spec"],
                         "extension_commit":manifest.get("extension_commit","baseline evaluation before provenance field"),
                         "summary":data}
        verdicts[label]=gate(data,limits)
        rows.extend(dict(policy=label,**r) for r in data)
    a.output.mkdir(parents=True,exist_ok=True)
    with (a.output/"comparison.csv").open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    (a.output/"receipts.json").write_text(json.dumps(receipts,indent=2))
    (a.output/"acceptance.json").write_text(json.dumps({"targets":limits,"verdicts":verdicts},indent=2))
    lines=["# Engineering comparison","","Single training seed; fixed evaluation initial-state seed. No hardware or statistical generalization claim.","",
           "|Policy|Condition|Completed|XY RMSE (m/s)|Yaw RMSE (rad/s)|Coverage|",
           "|---|---|---:|---:|---:|---:|"]
    for r in rows:
        lines.append(f"|{r['policy']}|{r['name']}|{r['completed']}/{r['episodes']}|{fmt(r['xy_rmse_mps'])}|{fmt(r['yaw_rmse_radps'])}|{r['sample_coverage']:.1%}|")
    lines+=["","## Predefined engineering gate",""]
    for label,v in verdicts.items():
        lines.append(f"- {label}: {'PASS' if v['passed'] else 'NOT MET'}; {v['checks']}")
    lines+=["","RMSE includes samples until first failure, including the failure tick, after a 2-second warmup. Read it together with completion and coverage. Work/power proxies are control-rate samples of generalized actuation forces and velocities, not electrical consumption."]
    (a.output/"COMPARISON.md").write_text("\n".join(lines)+"\n")
    # Rendering is centralized in go2_robust.visualize; this command exports metrics only.
    print(json.dumps(verdicts))

if __name__=="__main__":main()
