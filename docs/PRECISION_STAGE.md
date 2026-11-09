# Precision stage: nominal/robust reset mixture

The nominal replay reproduced prior RMSE within 0.00002 m/s. Per-environment,
per-control-tick samples locate approximately 73% of the added XY squared error
in forward/lateral steady windows. DR forward steady vx is approximately 0.316
m/s for a 0.5 m/s command (baseline approximately 0.433 m/s).

Targeted change: 50% reset episodes use exact nominal PD and zero command delay;
the other 50% retain the previous PD and 0/20/40-ms randomization. A shared reset
mask couples gains and delay. Other upstream randomization, rewards, hidden
layers and PPO remain unchanged. Event reset runs before action reset in the
pinned framework; the delay reset consumes the same per-environment mode mask.

Fine-tuning starts from the completed DR checkpoint and restores the official
runner's optimizer/normalizers. Budget: 500 ADDITIONAL iterations at 256 envs,
3,072,000 additional control samples, parent budget 9,216,000 samples. This is
engineering fine-tuning, not an equal-total-budget algorithm comparison against
the 1500-iteration baseline. Gate thresholds are unchanged.

The upstream runner resumes at its saved iteration index, so saved filenames
may overlap iteration numbering by one. Actual optimizer-step counts and added
training calls define the budget; do not infer cumulative updates solely from
the checkpoint filename.

No figures are rendered during this stage. Rich per-tick samples are retained
for later unified visualization: command tracking, transient/steady error,
body height/tilt, torque/power, and joint target error.
