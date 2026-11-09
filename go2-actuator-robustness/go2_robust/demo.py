"""Interactive engineering demo using the unmodified official play implementation."""
import argparse
import importlib.util
import os
from pathlib import Path
import sys
from .upstream import setup
from .tasks import make_cfg, configure_delay, OFFICIAL
from mjlab.tasks.registry import load_rl_cfg, load_runner_cls, register_mjlab_task
from mjlab.managers.event_manager import EventTermCfg
from mjlab.envs.mdp.dr.actuator import pd_gains

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--variant",choices=["baseline","dr","history","balanced"],required=True)
    p.add_argument("--checkpoint",type=Path,required=True)
    p.add_argument("--delay-ms",type=int,choices=[0,20,40],default=0)
    p.add_argument("--kp-scale",type=float,default=1.)
    p.add_argument("--kd-scale",type=float,default=1.)
    a=p.parse_args()
    if not a.checkpoint.is_file():p.error("Checkpoint missing")
    if a.kp_scale<=0 or a.kd_scale<=0:p.error("PD scales must be positive")
    upstream=setup();cfg=make_cfg(a.variant,play=True)
    cfg.scene.num_envs=1
    dt=cfg.decimation*cfg.sim.mujoco.timestep
    steps=round(a.delay_ms/1000/dt)
    if abs(steps*dt*1000-a.delay_ms)>1e-6:p.error("Delay is not an integer control tick")
    configure_delay(cfg,steps,steps)
    cfg.events={k:v for k,v in cfg.events.items() if k in ("reset_base","reset_robot_joints")}
    cfg.events["demo_pd"]=EventTermCfg(func=pd_gains,mode="startup",params={
        "kp_range":(a.kp_scale,)*2,"kd_range":(a.kd_scale,)*2,"operation":"scale"})
    task="Go2-Actuator-Demo"
    register_mjlab_task(task,cfg,cfg,load_rl_cfg(OFFICIAL),load_runner_cls(OFFICIAL))
    spec=importlib.util.spec_from_file_location("unitree_official_play",upstream/"scripts/play.py")
    module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module;spec.loader.exec_module(module)
    os.environ["WANDB_MODE"]="disabled"
    module.run_play(task,module.PlayConfig(checkpoint_file=str(a.checkpoint.resolve()),
                                          num_envs=1,viewer="viser",video=False))
if __name__=="__main__":main()
