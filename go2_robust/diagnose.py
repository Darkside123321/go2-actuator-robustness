"""Targeted nominal-condition diagnosis; records every environment and control tick."""
import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path
from .upstream import ROOT
from .evaluate import evaluate_condition
from mjlab.utils.torch import configure_torch_backends

def summarize(path):
    bins={}
    with path.open() as f:
        for r in csv.DictReader(f):
            if "scenario" in r and r["scenario"]!="nominal":continue
            if int(r["scored"]) != 1:continue
            t=float(r["t_start_s"])
            phase,start=("forward",2.) if t<6 else (("lateral",6.) if t<9 else ("turn",9.))
            period="transition" if t<start+1. else "steady"
            key=phase+"/"+period
            b=bins.setdefault(key,dict(samples=0,xy_sse=0.,yaw_sse=0.,vx_bias=0.,vy_bias=0.,yaw_bias=0.,torque_sum=0.,joint_gap_sum=0.))
            dx=float(r["vx"])-float(r["cmd_vx"]);dy=float(r["vy"])-float(r["cmd_vy"])
            dz=float(r["wz"])-float(r["cmd_wz"])
            b["samples"]+=1;b["xy_sse"]+=dx*dx+dy*dy;b["yaw_sse"]+=dz*dz
            b["vx_bias"]+=dx;b["vy_bias"]+=dy;b["yaw_bias"]+=dz
            b["torque_sum"]+=float(r["torque_rms_Nm"])
            b["joint_gap_sum"]+=float(r["joint_gap_rms_rad"])
    total=sum(b["samples"] for b in bins.values())
    for b in bins.values():
        n=b["samples"]
        b.update(xy_rmse_mps=math.sqrt(b["xy_sse"]/n),yaw_rmse_radps=math.sqrt(b["yaw_sse"]/n),
                 vx_bias_mps=b["vx_bias"]/n,vy_bias_mps=b["vy_bias"]/n,yaw_bias_radps=b["yaw_bias"]/n,
                 mean_torque_rms_Nm=b["torque_sum"]/n,mean_joint_gap_rms_rad=b["joint_gap_sum"]/n,
                 mse_contribution=b["xy_sse"]/total)
    return bins

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--baseline-checkpoint",required=True,type=Path)
    parser.add_argument("--output",type=Path,default=ROOT/"results/nominal_diagnostic_v1")
    args=parser.parse_args()
    output=args.output
    if not args.baseline_checkpoint.is_file():parser.error("Baseline checkpoint missing")
    if output.exists():raise RuntimeError("Diagnostic output already exists")
    output.mkdir(parents=True)
    spec=json.loads((ROOT/"configs/evaluation.json").read_text())
    condition=next(x for x in spec["scenarios"] if x["name"]=="nominal")
    paths={"baseline":args.baseline_checkpoint.resolve(),
           "dr":Path(json.loads((ROOT/"runs/dr_s42_status.json").read_text())["run_dirs"][0])/"model_1499.pt"}
    configure_torch_backends()
    results={}
    columns=["step","t_start_s","t_end_s","env_id","cmd_vx","cmd_vy","cmd_wz","vx","vy","wz",
             "height_m","tilt_deg","torque_rms_Nm","mechanical_power_W","joint_gap_rms_rad","scored"]
    old=json.loads((ROOT/"reports/receipts.json").read_text())
    for variant,checkpoint in paths.items():
        with (output/f"{variant}_samples.csv").open("w",newline="") as f:
            writer=csv.writer(f);writer.writerow(columns)
            score,_=evaluate_condition(variant,checkpoint,spec,condition,csv.writer(io.StringIO()),writer)
        original=next(x for x in old[variant]["summary"] if x["name"]=="nominal")
        results[variant]={"checkpoint_sha256":hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
                          "overall":score,"original_xy_rmse_mps":original["xy_rmse_mps"],
                          "replay_rmse_delta":score["xy_rmse_mps"]-original["xy_rmse_mps"],
                          "segments":summarize(output/f"{variant}_samples.csv")}
        print("DIAGNOSTIC",variant,json.dumps(results[variant]),flush=True)
    gap={k:results["dr"]["segments"][k]["mse_contribution"]-results["baseline"]["segments"][k]["mse_contribution"]
         for k in results["baseline"]["segments"]}
    results["mse_gap_by_segment"]=gap
    (output/"diagnosis.json").write_text(json.dumps(results,indent=2))
    print("MSE_GAP",json.dumps(gap),flush=True)
if __name__=="__main__":main()
