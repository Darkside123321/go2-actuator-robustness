# Engineering comparison

Single training seed; fixed evaluation initial-state seed. No hardware or statistical generalization claim.

|Policy|Condition|Completed|XY RMSE (m/s)|Yaw RMSE (rad/s)|Coverage|
|---|---|---:|---:|---:|---:|
|baseline|nominal|16/16|0.151|0.070|100.0%|
|baseline|soft|16/16|0.197|0.118|100.0%|
|baseline|stiff|16/16|0.149|0.077|100.0%|
|baseline|delay20|16/16|0.214|0.159|100.0%|
|baseline|delay40|7/16|0.485|0.472|61.3%|
|baseline|soft_delay40|14/16|0.422|0.379|99.5%|
|dr|nominal|16/16|0.206|0.078|100.0%|
|dr|soft|16/16|0.283|0.155|100.0%|
|dr|stiff|16/16|0.199|0.106|100.0%|
|dr|delay20|16/16|0.209|0.105|100.0%|
|dr|delay40|16/16|0.223|0.142|100.0%|
|dr|soft_delay40|16/16|0.293|0.205|100.0%|
|history|nominal|16/16|0.211|0.100|100.0%|
|history|soft|16/16|0.298|0.176|100.0%|
|history|stiff|16/16|0.209|0.074|100.0%|
|history|delay20|16/16|0.215|0.117|100.0%|
|history|delay40|16/16|0.218|0.141|100.0%|
|history|soft_delay40|16/16|0.296|0.201|100.0%|

## Predefined engineering gate

- baseline: NOT MET; {'nominal_completion': True, 'nominal_tracking': True, 'delay40_completion': False, 'soft_delay40_completion': True}
- dr: NOT MET; {'nominal_completion': True, 'nominal_tracking': False, 'delay40_completion': True, 'soft_delay40_completion': True}
- history: NOT MET; {'nominal_completion': True, 'nominal_tracking': False, 'delay40_completion': True, 'soft_delay40_completion': True}

RMSE includes samples until first failure, including the failure tick, after a 2-second warmup. Read it together with completion and coverage. Work/power proxies are control-rate samples of generalized actuation forces and velocities, not electrical consumption.
