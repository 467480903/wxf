# Lateral Motion Trace Analysis

- files: 2
- trace_count: 2
- leg_count: 2
- improvement_m_median: -0.0163
- expected_lateral_m_median: 0.007
- odom_body_lateral_abs_m_median: 0.0015
- recommendation: `keep_active_lateral_motion_disabled`
- recommendation_reasons: ['all_trace_steps_worsened_rack_lateral_pose', 'positive_and_negative_linear_y_have_same_odom_lateral_sign', 'odom_lateral_response_less_than_half_expected_open_loop_distance']

## By Sign

- `negative`: count=1, improvement_m_median=-0.0178, improved=0, worse=1, odom_lateral_median=-0.001, odom_forward_median=0.0017, yaw_delta_deg_median=-0.4532
- `positive`: count=1, improvement_m_median=-0.0148, improved=0, worse=1, odom_lateral_median=-0.002, odom_forward_median=0.004, yaw_delta_deg_median=0.0399

## Legs

- `lateral_motion_trace_positive_tiny_20260611_1845.json` leg=1 vy=0.02: before=-0.0905, after=-0.1053, improvement=-0.0148, odom_lateral=-0.002, odom_forward=0.004, yaw_delta=0.0399, pre_robust_span=0.039, post_robust_span=0.036
- `lateral_motion_trace_negative_tiny_20260611_1850.json` leg=1 vy=-0.02: before=-0.1067, after=-0.1245, improvement=-0.0178, odom_lateral=-0.001, odom_forward=0.0017, yaw_delta=-0.4532, pre_robust_span=0.02, post_robust_span=0.057
