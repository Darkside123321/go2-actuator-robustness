"""Paired, first-failure evaluation. Does not train or automatically recycle failures."""
import argparse
from contextlib import ExitStack
from dataclasses import asdict
import csv
import hashlib
import json
import math
import subprocess
from pathlib import Path
import time
import torch
from .upstream import ROOT, setup
setup()
from mjlab.envs import ManagerBasedRlEnv
from mjlab.rl import MjlabOnPolicyRunner, RslRlVecEnvWrapper
from mjlab.tasks.registry import load_rl_cfg, load_runner_cls
from mjlab.managers.event_manager import EventTermCfg
from mjlab.envs.mdp.dr.actuator import pd_gains
from mjlab.utils.torch import configure_torch_backends
from .tasks import OFFICIAL, make_cfg, configure_delay

def command_at(profile, seconds):
    result = profile[0]["velocity"]
    for stage in profile:
        if seconds >= stage["start_s"]:
            result = stage["velocity"]
    return result

def profile_event(env, env_ids, profile):
    del env_ids
    value = command_at(profile, env.common_step_counter * env.step_dt)
    env.command_manager.get_term("twist").vel_command_b[:] = torch.tensor(value, device=env.device)

def make_evaluation_cfg(variant, spec, condition):
    cfg = make_cfg(variant, play=True)
    cfg.scene.num_envs = spec["num_envs"]
    cfg.episode_length_s = spec["duration_s"] + 10
    cfg.curriculum = {}
    cfg.terminations = {}  # first failure measured below; no automatic reset/reentry
    cfg.events = {k:v for k,v in cfg.events.items()
                  if k in ("reset_base", "reset_robot_joints")}
    cfg.events["reset_base"].params["pose_range"] = {
        "x": (0.,0.), "y": (0.,0.), "z": (0.,0.), "yaw": (-0.1,0.1)}
    cfg.events["reset_robot_joints"].params["position_range"] = (-0.02,0.02)
    cfg.events["fixed_pd"] = EventTermCfg(func=pd_gains, mode="startup", params={
        "kp_range": (condition["kp_scale"],)*2,
        "kd_range": (condition["kd_scale"],)*2, "operation": "scale"})
    cfg.events["profile"] = EventTermCfg(func=profile_event, mode="step",
                                        params={"profile": spec["command_profile"]})
    command = cfg.commands["twist"]
    command.heading_command = False
    command.ranges.heading = None
    command.rel_standing_envs = 0.
    command.init_velocity_prob = 0.
    command.resampling_time_range = (1000.,1000.)
    command.ranges.lin_vel_x = (0.,0.)
    command.ranges.lin_vel_y = (0.,0.)
    command.ranges.ang_vel_z = (0.,0.)
    for group in cfg.observations.values():
        group.enable_corruption = False
    configure_delay(cfg, condition["delay_steps"], condition["delay_steps"])
    cfg.sim.nan_guard.enabled = True
    return cfg

def optional_rmse(total, count):
    return math.sqrt(total/count) if count else None

def evaluate_condition(variant, checkpoint, spec, condition, trace, sample_trace=None):
    cfg = make_evaluation_cfg(variant, spec, condition)
    env = ManagerBasedRlEnv(cfg, device="cuda:0")
    try:
        agent = load_rl_cfg(OFFICIAL)
        wrapper = RslRlVecEnvWrapper(env, clip_actions=agent.clip_actions)
        cls = load_runner_cls(OFFICIAL) or MjlabOnPolicyRunner
        runner = cls(wrapper, asdict(agent), device="cuda:0")
        runner.load(str(checkpoint), load_cfg={"actor":True}, strict=True, map_location="cuda:0")
        policy = runner.get_inference_policy(device="cuda:0")
        env.common_step_counter = 0
        obs,_ = env.reset(seed=spec["seed"])
        from tensordict import TensorDict
        obs=TensorDict(obs, batch_size=[env.num_envs])
        robot = env.scene["robot"]
        n=env.num_envs
        alive=torch.ones(n, dtype=torch.bool, device=env.device)
        failure_time=torch.full((n,),float("nan"), device=env.device)
        counts=torch.zeros(n, device=env.device)
        exy=torch.zeros_like(counts); eyaw=exy.clone(); torque2=exy.clone()
        work=exy.clone(); peak=exy.clone(); da2=exy.clone()
        previous=torch.zeros((n,12),device=env.device)
        dt=env.step_dt
        steps=round(spec["duration_s"]/dt)
        warmup=round(spec["warmup_s"]/dt)
        for i in range(steps):
            reference=torch.tensor(command_at(spec["command_profile"],i*dt),device=env.device)
            with torch.inference_mode():
                action=policy(obs)
                obs,_,_,_=wrapper.step(action)
                vel=robot.data.root_link_lin_vel_b
                yaw=robot.data.root_link_ang_vel_b[:,2]
                force=robot.data.actuator_force
                state=torch.cat([vel,yaw[:,None],robot.data.root_link_pos_w,
                                 robot.data.projected_gravity_b,force],dim=1)
                if not torch.isfinite(state).all():
                    raise FloatingPointError("Nonfinite evaluation state")
                valid=alive.clone() if i>=warmup else torch.zeros_like(alive)
                if valid.any():
                    counts+=valid
                    exy+=((vel[:,:2]-reference[:2]).square().sum(1))*valid
                    eyaw+=(yaw-reference[2]).square()*valid
                    torque2+=force.square().mean(1)*valid
                    peak=torch.maximum(peak,force.abs().max(1).values*valid)
                    power=(env.sim.data.qfrc_actuator*env.sim.data.qvel).abs().sum(1)
                    work+=power*dt*valid
                    da2+=(action-previous).square().mean(1)*valid
                if sample_trace is not None:
                    power_diag=(env.sim.data.qfrc_actuator*env.sim.data.qvel).abs().sum(1)
                    tilt=torch.acos((-robot.data.projected_gravity_b[:,2]).clamp(-1,1))*180/math.pi
                    gap=(robot.data.joint_pos_target-robot.data.joint_pos).square().mean(1).sqrt()
                    payload=torch.cat([vel[:,:2],yaw[:,None],robot.data.root_link_pos_w[:,2:3],
                                       tilt[:,None],force.square().mean(1).sqrt()[:,None],
                                       power_diag[:,None],gap[:,None],valid.float()[:,None]],dim=1).cpu().tolist()
                    for env_id,values in enumerate(payload):
                        sample_trace.writerow([i,i*dt,(i+1)*dt,env_id,*reference.tolist(),*values[:-1],int(values[-1])])
                failed=(robot.data.root_link_pos_w[:,2]<spec["failure_height_m"]) | (
                    robot.data.projected_gravity_b[:,2]>-math.cos(math.radians(spec["failure_tilt_deg"])))
                newly=alive & failed
                failure_time[newly]=(i+1)*dt
                alive &= ~failed
                previous=action.clone()
                if i%5==0:
                    trace.writerow([condition["name"],(i+1)*dt,*reference.tolist(),
                                    *vel.mean(0).tolist(),float(yaw.mean()),int(alive.sum())])
        entries=[]
        for k in range(n):
            c=float(counts[k]); seconds=c*dt
            entries.append(dict(scenario=condition["name"],episode=k,completed=bool(alive[k]),
                failure_s=None if alive[k] else float(failure_time[k]),
                scored_seconds=seconds,xy_rmse_mps=optional_rmse(float(exy[k]),c),
                yaw_rmse_radps=optional_rmse(float(eyaw[k]),c),
                torque_rms_Nm=optional_rmse(float(torque2[k]),c),
                peak_torque_Nm=float(peak[k]),
                mechanical_absolute_work_J=float(work[k]),
                mean_absolute_mechanical_power_W=float(work[k])/seconds if seconds else None,
                issued_action_delta_rms=optional_rmse(float(da2[k]),c)))
        total=float(counts.sum())
        result=dict(**condition,episodes=n,completed=int(alive.sum()),
            completion_rate=float(alive.float().mean()),
            sample_coverage=total/(n*(steps-warmup)),
            xy_rmse_mps=optional_rmse(float(exy.sum()),total),
            yaw_rmse_radps=optional_rmse(float(eyaw.sum()),total),
            torque_rms_Nm=optional_rmse(float(torque2.sum()),total),
            mean_absolute_mechanical_power_W=float(work.sum())/(total*dt) if total else None,
            issued_action_delta_rms=optional_rmse(float(da2.sum()),total))
        return result,entries
    finally:
        env.close()

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--variant",choices=["baseline","dr","history","balanced"],required=True)
    p.add_argument("--checkpoint",type=Path,required=True)
    p.add_argument("--spec",type=Path,default=ROOT/"configs/evaluation.json")
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--samples",action="store_true",help="Keep every environment/control-tick sample for later visualization")
    a=p.parse_args()
    checkpoint=a.checkpoint.resolve()
    if not checkpoint.is_file():p.error("Checkpoint not found")
    if a.output.exists():p.error("Output exists; use a new result directory")
    spec=json.loads(a.spec.read_text())
    if spec["duration_s"]<=spec["warmup_s"]:p.error("duration must exceed warmup")
    a.output.mkdir(parents=True)
    configure_torch_backends()
    start=time.monotonic();summary=[];episodes=[]
    manifest=dict(variant=a.variant,checkpoint=str(checkpoint),
        checkpoint_sha256=hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
        spec=spec,success=False,
        extension_commit=subprocess.check_output(["git","-C",str(ROOT),"rev-parse","HEAD"],text=True).strip(),
        upstream_commit=subprocess.check_output(["git","-C",str(setup()),"rev-parse","HEAD"],text=True).strip())
    (a.output/"manifest.json").write_text(json.dumps(manifest,indent=2))
    try:
        with ExitStack() as stack:
            samples=None
            if a.samples:
                sf=stack.enter_context((a.output/"samples.csv").open("w",newline=""))
                sw=csv.writer(sf)
                sw.writerow(["scenario","step","t_start_s","t_end_s","env_id","cmd_vx","cmd_vy","cmd_wz","vx","vy","wz","height_m","tilt_deg","torque_rms_Nm","mechanical_power_W","joint_gap_rms_rad","scored"])
                class ScenarioWriter:
                    name=""
                    def writerow(self,row):sw.writerow([self.name,*row])
                samples=ScenarioWriter()
            f=stack.enter_context((a.output/"trace.csv").open("w",newline=""))
            trace=csv.writer(f)
            trace.writerow(["scenario","time_s","cmd_vx","cmd_vy","cmd_yaw",
                            "mean_vx_all_envs","mean_vy_all_envs","mean_vz_all_envs",
                            "mean_yaw_all_envs","survivors"])
            for condition in spec["scenarios"]:
                if samples is not None:samples.name=condition["name"]
                row,items=evaluate_condition(a.variant,checkpoint,spec,condition,trace,samples)
                summary.append(row);episodes.extend(items)
                (a.output/"summary.json").write_text(json.dumps(summary,indent=2))
                print("CONDITION_RESULT",json.dumps(row),flush=True)
        with (a.output/"episodes.csv").open("w",newline="") as f:
            writer=csv.DictWriter(f,fieldnames=list(episodes[0]));writer.writeheader();writer.writerows(episodes)
        manifest["success"]=True
    finally:
        manifest["wall_seconds"]=time.monotonic()-start
        (a.output/"manifest.json").write_text(json.dumps(manifest,indent=2))

if __name__=="__main__":main()
