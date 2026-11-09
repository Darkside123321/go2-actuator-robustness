"""One FIFO for the whole policy command; lag measured in 20-ms control ticks."""
from dataclasses import dataclass
import torch
from mjlab.envs.mdp.actions.actions import JointPositionAction, JointPositionActionCfg

class ActionFIFO:
    def __init__(self, num_envs, action_dim, min_lag=0, max_lag=2, device="cpu"):
        if not 0 <= min_lag <= max_lag:
            raise ValueError("Require 0 <= min_lag <= max_lag")
        self.min_lag, self.max_lag = min_lag, max_lag
        self.queue = torch.zeros((max_lag + 1, num_envs, action_dim), device=device)
        self.lags = torch.zeros(num_envs, dtype=torch.long, device=device)
        self.rows = torch.arange(num_envs, device=device)
        self.cursor = 0
        self.reset()

    def reset(self, env_ids=None):
        ids = self.rows if env_ids is None else self.rows[env_ids]
        self.queue[:, ids] = 0
        self.lags[ids] = torch.randint(self.min_lag, self.max_lag + 1,
                                      (len(ids),), device=self.queue.device)

    def push(self, action):
        self.queue[self.cursor].copy_(action)
        result = self.queue[(self.cursor - self.lags) % len(self.queue), self.rows].clone()
        self.cursor = (self.cursor + 1) % len(self.queue)
        return result

@dataclass(kw_only=True)
class DelayedJointPositionActionCfg(JointPositionActionCfg):
    use_nominal_mask: bool = False
    min_delay_steps: int = 0
    max_delay_steps: int = 0

    def build(self, env):
        return DelayedJointPositionAction(self, env)

class DelayedJointPositionAction(JointPositionAction):
    def __init__(self, cfg, env):
        super().__init__(cfg, env)
        self.fifo = ActionFIFO(env.num_envs, self.action_dim,
                              cfg.min_delay_steps, cfg.max_delay_steps, env.device)

    def process_actions(self, actions):
        super().process_actions(self.fifo.push(actions))

    def reset(self, env_ids=None):
        super().reset(env_ids)
        self.fifo.reset(env_ids)
        if self.cfg.use_nominal_mask:
            ids=self.fifo.rows if env_ids is None else self.fifo.rows[env_ids]
            self.fifo.lags[ids[self._env.nominal_episode_mask[ids]]]=0
