# Unified visualization plan (rendering deferred)

Current assets: six-condition comparison, actual training-reward curves, and the
interactive 3D viewer. These do not fully explain control behavior.

Next unified set uses the latest style: closed frames, inward ticks, Arial Bold,
large labels, thick curves, fixed user palette, no explanation text below plots.
Explanations, sample definitions and limitations belong in captions/docs.

1. Command response: target vs measured vx, vy and wz; initial-state traces plus
   explicitly defined ensemble summaries, not invented multi-training-seed CIs.
2. Error localization: forward/lateral/turn, each split into first 1-second
   transition and remaining steady phase. Show raw units and overall score.
3. Robustness: completion paired with pre-failure error across the fixed six
   conditions. Never rank partially surviving models by RMSE alone.
4. Control cost and state: torque RMS, sampled mechanical power, body height,
   tilt and joint-target tracking error. Mechanical power is not battery power.

Full nominal baseline/DR data are in results/nominal_diagnostic_v1. The new
balanced candidate evaluation records every environment/tick in samples.csv.
Old latency-condition traces are aggregate diagnostics only; collect targeted
per-environment data later if detailed baseline latency envelopes are needed.
No unrecorded trajectory or confidence band will be fabricated to fill a panel.

The fine-tuned candidate has 500 additional training iterations. Visual labels
must expose this budget difference from the earlier equal-budget comparison.
