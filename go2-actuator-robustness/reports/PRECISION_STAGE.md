# Precision correction stage

One engineering fine-tuning candidate; unchanged fixed evaluation protocol.

Change: 50% exact nominal PD/zero-delay reset episodes, 50% original actuator randomization. Rewards, hidden layers and PPO unchanged.

Budget: 500 additional iterations after the 1500-iteration DR model, 3,072,000 new control samples; cumulative 12,288,000. This is not an equal-total-budget algorithm comparison.

|Policy|Nominal XY RMSE (m/s)|40-ms completed|40-ms XY RMSE (m/s)|
|---|---:|---:|---:|
|baseline|0.151|7/16|0.485|
|dr|0.206|16/16|0.223|
|balanced|0.169|16/16|0.179|

Predefined gate: PASS for this fixed profile. All six conditions completed 16/16. One training seed, 16 paired initial states; not a hardware/general robustness claim.

Diagnosis: approximately 73% of prior added squared tracking error was in forward/lateral steady windows. Nominal replay differed from prior scores by less than 0.00002 m/s.

Final checkpoint: model_1998.pt; optimizer step count 40000; all logged scalar values and final parameters finite.

Graphics deferred by request: closed frames, inward ticks, no footer explanations; planned command-response, error-localization, state and control-cost figures use recorded per-environment samples.
