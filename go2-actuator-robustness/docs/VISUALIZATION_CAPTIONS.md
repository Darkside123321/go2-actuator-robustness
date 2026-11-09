# Unified engineering figure contract and captions

## Shared contract
Core conclusion: actuator-randomized control improved survival in the fixed
latency cases; subsequent extra-budget precision fine-tuning improved nominal
tracking while preserving delayed completion. This is one training seed per
initial policy and one paired initial-state seed, not a universal superiority claim.

Layout: quantitative grids, each panel answering one engineering question.
Python/matplotlib only; actual Arial Bold, closed four-sided frames, inward
four-side ticks, 3.2-pt curves, fixed user palette, no footer explanations.
Large engineering presentation sizes are intentional, not journal-width claims.
PNG 300 dpi; TIFF 600 dpi LZW; editable SVG and embedded TrueType PDF.

## 01 Robustness overview
All 24 rows: four policies x six conditions. Completion and XY RMSE must be read
together because RMSE stops at first failure. Initial policies each have 1500
training cycles; balanced adds 500 cycles to DR. No error bars or invented CIs.
The balanced legend explicitly discloses the extra training budget.

## 02 Velocity response
Nominal condition only. Three policies with saved full nominal traces: baseline,
DR and balanced. History remains in overview/training figures, but has no saved
per-environment nominal trace and is not fabricated in temporal panels.
Lines are means across 16 initial states; bands are pointwise P10-P90 across
those states, not training-seed confidence intervals. All 600 control ticks per
state contribute, including the 2-second stand warmup. Command is held during
[t_start,t_end); measured velocity is sampled at t_end. Command changes occur at 2, 6 and 9 seconds; no phase-reference lines are drawn. All nominal episodes completed.

## 03 Error localization
All 18 available segment rows (three policies x six phase windows). Transition
is the first 1 second after each command change; remaining scored phase time is
steady. Panel a: XY RMSE; panel b: mean steady forward/lateral speeds calculated
from command plus signed bias. Diamond markers show target speeds. No significance
or across-seed uncertainty is implied.

## 04 State and control
Same nominal traces/16 states as figure 02. Base height, tilt, joint target error,
actuator torque RMS, sampled absolute mechanical power and absolute mechanical
work show physical/control behavior. Bands are pointwise P10-P90 across initial
states. Thick curves use a 5-tick (0.10 s) trailing mean except cumulative work;
faint curves retain every raw mean. Work integrates matched generalized force x
velocity after the 2-second warmup; it is not electrical/battery energy.

## 05 Training progress
All 4500 initial-training points and all 500 fine-tuning points are shown faintly.
Thick curves are 25-iteration trailing arithmetic means (shorter beginning windows).
Fine-tuning has its own additional-iteration axis, rather than hiding its extra
budget. Training distributions differ, so reward ranking alone is not evaluation
performance ranking. No simulated trajectories, data truncation or fake CI bands.

## Source-data selection
Temporal figures use 9600 rows per policy, all 16 states x 600 ticks. Baseline and
DR inputs each contain exactly these nominal records. Balanced input has 57600
rows over six conditions: the 48000 non-nominal rows are outside the explicitly
nominal temporal question and remain represented in the all-condition overview.
No time/state rows are dropped within the nominal panels. Filter counts are in
data_contract.json; unified original samples and aggregates accompany the bundle.
