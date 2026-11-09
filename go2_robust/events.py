"""Coupled reset modes: exact nominal control or full actuator randomization."""
import torch
from mjlab.envs.mdp.dr.actuator import pd_gains
from mjlab.managers.event_manager import requires_model_fields

@requires_model_fields("actuator_gainprm","actuator_biasprm")
def balanced_pd_gains(env, env_ids, nominal_fraction=0.5):
    ids=torch.arange(env.num_envs,device=env.device) if env_ids is None else env_ids
    if not 0<=nominal_fraction<=1:raise ValueError("nominal_fraction outside [0,1]")
    if not hasattr(env,"nominal_episode_mask"):
        env.nominal_episode_mask=torch.zeros(env.num_envs,dtype=torch.bool,device=env.device)
    mask=torch.rand(len(ids),device=env.device)<nominal_fraction
    env.nominal_episode_mask[ids]=mask
    pd_gains(env,ids,kp_range=(0.75,1.25),kd_range=(0.75,1.25),operation="scale")
    nominal=ids[mask]
    if len(nominal):
        pd_gains(env,nominal,kp_range=(1.,1.),kd_range=(1.,1.),operation="scale")
