# G2A WXF Pick/Place AB Versioning - 2026-06-27

## V1 Baseline

Validated live success:

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624
./run_fast_live_script.sh yolo/task_all_pick_place_ab.py --execute
```

Successful run log:

```text
/data/wxf/wxf/mqtt_gateway_workspace_20260624/run_logs/20260627/20260627_143606_fast_live_script_yolo_task_all_pick_place_ab.py_1328405.log
```

Result:

```text
exit_code: 0
pick_a: 103.299s
place_a: 66.957s
pick_b: 102.727s
place_b: 80.262s
```

The V1 entry point remains unchanged and can continue to be used at any time.

## V2 Optimization

New entry point:

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624
./run_fast_live_script.sh yolo/task_all_pick_place_ab_v2.py --execute
```

V2 does not edit the four validated child scripts. It loads each child
`TASK_SEQUENCE` and runs them in the same Python process. This removes one layer
of child Python process startup while preserving:

- child order: pick A, place A, pick B, place B
- per-child vision retry/fallback state
- per-child environment-variable isolation
- fail-fast behavior

If V2 has any issue, run V1 directly:

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624
./run_fast_live_script.sh yolo/task_all_pick_place_ab.py --execute
```

## Files

- `yolo/task_all_pick_place_ab.py`: V1 baseline, unchanged.
- `yolo/task_all_pick_place_ab_v1.py`: frozen copy of V1 for explicit version runs.
- `yolo/task_all_pick_place_ab_v2.py`: optimized single-process orchestrator.

## Validation

Before live use, V2 should pass:

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624
python3 -m py_compile yolo/task_all_pick_place_ab_v2.py
./run_fast_live_script.sh yolo/task_all_pick_place_ab_v2.py
```

## V3 Balanced-Speed Candidate

New entry point:

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624
./run_fast_live_script.sh yolo/task_all_pick_place_ab_v3.py --execute
```

V3 keeps V2's single-process child orchestration and adds only software-wait
tuning:

```text
G2_WXF_TTS_PRE_PLAY_DELAY_S=0.3
G2_WXF_NAV_IDLE_STABLE_S=0.5
```

No physical motion target is changed:

- no waypoint changes
- no arm speed changes
- no gripper target changes
- no EE offset-size changes
- no visual step skipping
- no TTS skipping

Expected speed change against the V1 success log:

```text
V1 observed total: about 354s
V3 estimated total: about 338-342s
Expected saving: about 12-16s
```

Tunable overrides:

```bash
G2_WXF_V3_TTS_PRE_PLAY_DELAY_S=0.5 G2_WXF_V3_NAV_IDLE_STABLE_S=0.8 \
  ./run_fast_live_script.sh yolo/task_all_pick_place_ab_v3.py --execute
```

If V3 is not stable onsite, run V1 directly:

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624
./run_fast_live_script.sh yolo/task_all_pick_place_ab.py --execute
```

V3 validation before live use:

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624
python3 -m py_compile yolo/task_all_pick_place_ab_v3.py
./run_fast_live_script.sh yolo/task_all_pick_place_ab_v3.py
```

## V3 Live Result

Operator live run:

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624
./run_fast_live_script.sh yolo/task_all_pick_place_ab_v3.py --execute
```

Live result on 2026-06-27:

```text
exit_code: 0
pick_a: 106.366s
place_a: 62.205s
pick_b: 103.079s
place_b: 72.320s
V3 total: 343.972s
error keyword count: 0
vision retry/fallback count: 0
log: /data/wxf/wxf/mqtt_gateway_workspace_20260624/run_logs/20260627/20260627_151206_fast_live_script_yolo_task_all_pick_place_ab_v3.py_1554027.log
```

Measured gain vs the V1 success log is about `10s` for this run. The gain is
not perfectly deterministic because chassis navigation time varies at the
physical site. The main stable V3 improvement is reduced TTS wait and one
combined top-level orchestration process while preserving the original child
flows.

Rollback remains:

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624
./run_fast_live_script.sh yolo/task_all_pick_place_ab.py --execute
```

## V4 Low-Risk YOLO Resident Candidate

New entry point:

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624
./run_fast_live_script.sh yolo/task_all_pick_place_ab_v4.py --execute
```

What V4 changes:

- Keeps V3 action order and software waits.
- Enables `G2_WXF_YOLO_RESIDENT=1` for the V4 entry point.
- Runs `yolo_depth.py` through `yolo/yolo_depth_worker.py`, which keeps YOLO
  model objects loaded across the combined A/B run.

What V4 does not change:

- no waypoint changes
- no arm speed changes
- no gripper target changes
- no EE offset-size changes
- no visual step skipping
- no TTS text skipping
- no correction math changes

Software validation on 2026-06-27:

```text
py_compile: passed
V4 dry-run plan: exit_code 0
worker single request: rc 0
worker cache smoke: first shelf.pt request 1.626s, second shelf.pt request 0.658s
```

Expected speed change:

- V3 live total was `343.972s`.
- V4 should mainly reduce the six `yolo_depth.py` calls.
- Conservative expected live total is about `320-330s`, depending on chassis
  navigation variability.

Rollback remains:

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624
./run_fast_live_script.sh yolo/task_all_pick_place_ab.py --execute
```
