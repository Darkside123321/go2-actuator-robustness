"""Compose upstream task configs without editing upstream code or PPO."""
from dataclasses import fields
from .upstream import setup
setup()
import mjlab.tasks
import src.tasks
from mjlab.tasks.registry import load_env_cfg, load_rl_cfg, load_runner_cls, register_mjlab_task
from mjlab.managers.event_manager import EventTermCfg
from mjlab.envs.mdp.dr.actuator import pd_gains
from .actions import DelayedJointPositionActionCfg

OFFICIAL = "Unitree-Go2-Flat"
TASKS = {"dr": "Go2-Actuator-DR", "history": "Go2-Actuator-History", "balanced": "Go2-Actuator-Balanced"}

def configure_delay(cfg, minimum, maximum):
    old = cfg.actions["joint_pos"]
    kwargs = {f.name: getattr(old, f.name) for f in fields(old)
              if f.init and f.name not in ("min_delay_steps", "max_delay_steps")}
    cfg.actions["joint_pos"] = DelayedJointPositionActionCfg(
        **kwargs, min_delay_steps=minimum, max_delay_steps=maximum)

def make_cfg(variant="baseline", play=False):
    cfg = load_env_cfg(OFFICIAL, play=play)
    if variant == "history":
        cfg.observations["actor"].history_length = 4
    if variant != "baseline" and not play:
        configure_delay(cfg, 0, 2)
        cfg.events["actuator_pd"] = EventTermCfg(
            func=pd_gains, mode="reset",
            params={"kp_range": (0.75, 1.25), "kd_range": (0.75, 1.25), "operation": "scale"})
    if variant == "balanced" and not play:
        from .events import balanced_pd_gains
        cfg.events["actuator_pd"] = EventTermCfg(func=balanced_pd_gains, mode="reset", params={"nominal_fraction":0.5})
        cfg.actions["joint_pos"].use_nominal_mask = True
    return cfg

def register():
    for variant, task in TASKS.items():
        agent = load_rl_cfg(OFFICIAL)
        agent.experiment_name = "go2_actuator_" + variant
        register_mjlab_task(task, make_cfg(variant), make_cfg(variant, play=True),
                           agent, load_runner_cls(OFFICIAL))
