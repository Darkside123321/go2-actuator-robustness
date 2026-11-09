"""One engineering workflow; successful matching artifacts are reused, never overwritten."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from .upstream import ROOT

def launch(*args):
    subprocess.run([sys.executable,"-m",*map(str,args)],cwd=ROOT,check=True)

def ensure_eval(variant, checkpoint, output):
    manifest=output/"manifest.json"
    if output.exists():
        if not manifest.is_file():
            raise RuntimeError(f"Incomplete output: {output}; inspect before retrying")
        m=json.loads(manifest.read_text())
        expected=json.loads((ROOT/"configs/evaluation.json").read_text())
        digest=hashlib.sha256(checkpoint.read_bytes()).hexdigest()
        if not (m["success"] and m["variant"]==variant and m["spec"]==expected
                and m["checkpoint_sha256"]==digest and (output/"episodes.csv").is_file()):
            raise RuntimeError(f"Existing evaluation does not match: {output}")
        print("REUSE evaluation",variant,flush=True)
    else:
        launch("go2_robust.evaluate","--variant",variant,"--checkpoint",checkpoint,"--output",output)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--baseline-checkpoint",required=True,type=Path)
    p.add_argument("--iterations",type=int,default=1500)
    p.add_argument("--num-envs",type=int,default=256)
    p.add_argument("--seed",type=int,default=42)
    a=p.parse_args()
    base=a.baseline_checkpoint.resolve()
    if not base.is_file():p.error("Baseline checkpoint missing")
    ensure_eval("baseline",base,ROOT/"results/baseline_v1")
    for variant in ("dr","history"):
        status=ROOT/"runs"/f"{variant}_s{a.seed}_status.json"
        if status.exists():
            s=json.loads(status.read_text())
            if not (s["success"] and s["iterations"]==a.iterations and
                    s["num_envs"]==a.num_envs and s["seed"]==a.seed):
                raise RuntimeError(f"Existing training budget/status mismatch: {status}")
            print("REUSE training",variant,flush=True)
        else:
            launch("go2_robust.train","--variant",variant,"--iterations",a.iterations,
                   "--num-envs",a.num_envs,"--seed",a.seed)
            s=json.loads(status.read_text())
            if not s["success"]:raise RuntimeError("Training failed")
        checkpoint=Path(s["run_dirs"][0])/f"model_{a.iterations-1}.pt"
        ensure_eval(variant,checkpoint,ROOT/f"results/{variant}_s{a.seed}")
    launch("go2_robust.report", "--result", "baseline="+str(ROOT/"results/baseline_v1"),
           "--result", "dr="+str(ROOT/f"results/dr_s{a.seed}"),
           "--result", "history="+str(ROOT/f"results/history_s{a.seed}"))

if __name__=="__main__":main()
