# Figure contract and project style

Backend: Python / matplotlib. Style configuration: configs/figure_style.json.
All plot text uses the installed Arial Bold font; large engineering presentation sizes
follow the user's preference. Trend lines are 3.2 pt. Canvas and axes are white.
No background grid or phase-reference lines; all policy and command curves are solid.
Closed four-sided axes with inward ticks on all sides. No figure-footer explanations.
Baseline = #5B83BC; actuator DR = #FC9262; history = #94BFDC; balanced = #E9A4C1.
The remaining supplied colors are #C4EAF2 and #FEDE8E.

## Evidence and layout
Five figures cover robustness, velocity response, phase error, state/control cost,
and training progress. Measurements and transformations are recorded in
reports/visualization/data_contract.json and source_data/.
The overview contains all 24 policy-condition rows. Temporal panels use all 28,800
saved nominal samples from three policies and 16 paired initial states each.
Bands show pointwise P10-P90 across initial states, not training-seed confidence intervals.
The history variant has no saved per-environment nominal trace and is omitted from
temporal panels; it remains in the overview and training comparison.
All 5000 training observations are retained. Thick training curves show a 25-iteration
trailing arithmetic mean; raw traces remain faintly visible. The balanced policy's
extra 500 iterations use a separate axis and are disclosed in legends.
Mechanical work is a proxy, not measured battery consumption.
Detailed captions are in docs/VISUALIZATION_CAPTIONS.md.

## Export and QA
PNG 300 dpi; TIFF 600 dpi with LZW compression; editable SVG; embedded TrueType PDF.
Arial font files are not redistributed. No new simulation or training is run for plotting.
Both plotting modules pass static preflight: 13 PASS, 1 WARN, 0 FAIL each.
The warning concerns presentation widths exceeding common journal column widths,
as requested by the user. All five rendered PNGs have been visually inspected.
Current outputs and export metadata: reports/visualization/qa.json.
Legacy comparison/training plots were removed; metric reporting no longer recreates them.
