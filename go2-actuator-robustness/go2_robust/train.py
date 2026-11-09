"""Budgeted entry point delegating the complete PPO loop to the official script."""
import argparse
import hashlib
import re
import importlib.util
import json
import os
import resource
import subprocess
import sys
import time
from dataclasses import replace
from pathlib import Path
from .upstream import ROOT, setup

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--variant", choices=["dr", "history", "balanced"], required=True)
    p.add_argument("--iterations", type=int, default=1500)
    p.add_argument("--num-envs", type=int, default=256)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--resume-from",type=Path)
    a = p.parse_args()
    if a.resume_from and not a.resume_from.is_file():p.error("Resume checkpoint missing")
    if a.iterations <= 0 or a.num_envs <= 0:
        p.error("budgets must be positive")
    existing = ROOT / "runs" / f"{a.variant}_s{a.seed}_status.json"
    if existing.exists():
        p.error("Existing training status; use pipeline to reuse results or archive it explicitly")
    upstream = setup()
    from .tasks import register, TASKS
    register()
    name = "unitree_official_train"
    spec = importlib.util.spec_from_file_location(name, upstream / "scripts/train.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    cfg = module.TrainConfig.from_task(TASKS[a.variant])
    cfg.env.scene.num_envs = a.num_envs
    cfg.agent.max_iterations = a.iterations
    cfg.agent.seed = a.seed
    cfg.agent.save_interval = 500
    cfg.agent.logger = "tensorboard"
    cfg.agent.run_name = a.variant + "_s" + str(a.seed)
    cfg = replace(cfg, gpu_ids=[0], video=False, enable_nan_guard=True)
    os.environ["WANDB_MODE"] = "disabled"
    (ROOT / "runs").mkdir(exist_ok=True)
    os.chdir(ROOT / "runs")
    base = Path("logs/rsl_rl") / cfg.agent.experiment_name
    before = set(base.glob("*"))
    if a.resume_from:
        parent=a.resume_from.resolve()
        base.mkdir(parents=True,exist_ok=True)
        link=base/"resume_parent"
        if link.exists() and link.resolve()!=parent.parent:raise RuntimeError("Resume parent mismatch")
        if not link.exists():link.symlink_to(parent.parent,target_is_directory=True)
        before.add(link)
        cfg.agent.resume=True
        cfg.agent.load_run="^resume_parent$"
        cfg.agent.load_checkpoint="^"+re.escape(parent.name)+"$"
    start = time.monotonic()
    result = dict(variant=a.variant, seed=a.seed, num_envs=a.num_envs,
                  iterations=a.iterations, control_steps=a.iterations*a.num_envs*24,
                  upstream_commit=subprocess.check_output(["git","-C",str(upstream),
                                                           "rev-parse","HEAD"], text=True).strip(),
                  extension_commit=subprocess.check_output(["git","-C",str(ROOT),
                                                            "rev-parse","HEAD"], text=True).strip(),
                  success=False)
    if a.resume_from:
        result.update(parent_checkpoint=str(parent),parent_sha256=hashlib.sha256(parent.read_bytes()).hexdigest(),budget_semantics="iterations and control_steps are additional fine-tuning work")
    try:
        module.launch_training(TASKS[a.variant], cfg)
        result["success"] = True
    finally:
        result.update(wall_seconds=time.monotonic()-start,
                      peak_RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,
                      run_dirs=[str(x.resolve()) for x in set(base.glob("*"))-before])
        out = ROOT / "runs" / (cfg.agent.run_name + "_status.json")
        out.write_text(json.dumps(result, indent=2))
        print("RUN_STATUS", json.dumps(result))

if __name__ == "__main__":
    main()
