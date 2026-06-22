# Lateral Active Response Analysis

- files: 3
- event_count: 44
- step_count: 2
- blocked_count: 1
- improvement_m_median: -0.0304
- improvement_m_min: -0.036
- rollback_improvement_m_median: 0.005
- recommendation: `keep_active_lateral_motion_disabled`
- recommendation_reason: `all_executed_lateral_steps_worsened_pose`

## By Vy Sign

- negative: count=1, improvement_m_median=-0.0247, improvement_m_min=-0.0247, improvement_m_max=-0.0247, worse_count=1, improved_count=0
- positive: count=1, improvement_m_median=-0.036, improvement_m_min=-0.036, improvement_m_max=-0.036, worse_count=1, improved_count=0

## Reasons

- lateral_sample_unstable: 2
- linear_y_direction_not_calibrated: 2

## Executed Steps

| run_id | pass | direction | vy_mps | before | after | improvement | rollback_lateral | rollback_improvement | status |
|---|---:|---|---:|---:|---:|---:|---:|---:|---|
| 20260611_174740_770530f2 | 1 | None | 0.03 | -0.0582 | -0.0943 | -0.036 | -0.083 | 0.0113 | no_improvement_rollback_done |
| 20260611_174903_80802719 | 1 | None | -0.03 | -0.0815 | -0.1062 | -0.0247 | -0.1075 | -0.0013 | no_improvement_rollback_done |

## Blocked Decisions

| run_id | direction | lateral | sample_span | reasons | status |
|---|---|---:|---:|---|---|
| 20260611_175122_368b46ff | disabled | -0.1095 | 0.092 | lateral_sample_unstable, linear_y_direction_not_calibrated | blocked |

## Files

- `logs/lateral_centering_probe_direction_disabled_20260611_1801.jsonl`
- `logs/lateral_centering_probe_tight_target_20260611_1752.jsonl`
- `logs/lateral_centering_probe_tight_target_fixed_sign_20260611_1757.jsonl`
