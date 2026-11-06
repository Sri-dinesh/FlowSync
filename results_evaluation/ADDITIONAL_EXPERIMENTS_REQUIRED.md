# FlowSync – Additional Experiments Required

**Document Date**: November 2026  
**Status**: Recommended Experimental Roadmap  
**Guiding Principle**: Recommend only targeted, high-value experiments that directly resolve unverified claims, methodological gaps, or critical scientific limitations. Do not rerun existing verified experiments.

---

## 1. Prioritized Experimental Recommendations

### Priority 1: Critical / Essential (Required to Validate Core Claims)

#### Experiment 1.1: Physical Embedded Hardware Profiling on NVIDIA Jetson Orin
- **Current Limitation**: The existing latency profile (`results/final/latency_profile_full.json`) was executed on an **x86_64 Linux CPU workstation** (quad-core CPU, CPU-only PyTorch, no CUDA acceleration). The claim in paper drafts that FlowSync achieved a 65.26 ms P95 latency on an embedded NVIDIA Jetson Orin board is unevidenced and factually contradicted by artifact metadata.
- **Proposed Protocol**:
  1. Deploy the exact perception and control pipeline onto physical NVIDIA Jetson Orin hardware (e.g., Jetson Orin Nano 8GB or Jetson AGX Orin).
  2. Export the YOLOv8n detector to a TensorRT engine (FP16 or INT8 precision) utilizing the Jetson's onboard Ampere GPU and DLA cores.
  3. Profile 10,000 steps of end-to-end execution (frame decode, TensorRT detection, ByteTrack, state construction, PyTorch/ONNX policy inference, supervisor state machine, and safety shield).
  4. Log host telemetry (`tegrastats`), device temperature, power draw (W), and memory footprint.
- **Expected Outcome / Impact**: Replaces contradicted claims with genuine edge embedded hardware data; verifies whether real-time 10 Hz (100 ms) compliance holds under thermal and compute constraints of edge municipal cabinets.

#### Experiment 1.2: Independent SUMO Microscopic Evaluation of Learned D3QN and FlowSync-UQ
- **Current Limitation**: In the current repository, SUMO microscopic simulations (`results/sumo_sensing_recovery/full_20261031/`, 72 episodes) evaluated **only classical baselines** (Fixed, Halted-count, Max-Pressure). **Learned D3QN and FlowSync-UQ were never evaluated in SUMO**. The paper claims regarding sim-to-sim transfer and learned controller performance in realistic microscopic traffic are unsupported.
- **Proposed Protocol**:
  1. Integrate the frozen D3QN checkpoints (Seeds 101, 202, 303) and the FlowSync-UQ supervisor into the SUMO TraCI control interface (`research/policies/` and `research/experiments/sumo_sensing.py`).
  2. Execute the matched 72-episode experimental design (4 sensing conditions $\times$ 6 traffic seeds across Balanced, NS-dominant, and EW-dominant demand families).
  3. Log stopped delay per requested vehicle, completed trips, switch onsets, safety shield interventions, and fallback transfers.
- **Expected Outcome / Impact**: Conclusively establishes whether D3QN and FlowSync-UQ maintain control stability and efficiency in SUMO microscopic simulation with realistic car-following (Krauss) and lane-changing models.

---

## Priority 2: Important (Required for Methodological Rigor)

#### Experiment 2.1: Vision-Calibrated Perception Uncertainty Training
- **Current Limitation**: The uncertainty calibration (`results/uncertainty_calibration/pilot_20261014/calibration.json`) was fitted against synthetic simulator queue count discrepancies ($\ge 3$ vehicles), resulting in zero weights on 5 of the 7 features (detector confidence, tail uncertainty, observation age, missing frame, and track instability). The uncertainty estimator does not reflect real computer vision error distributions.
- **Proposed Protocol**:
  1. Run YOLOv8n on real traffic video datasets (e.g., UA-DETRAC, DAWN, or synthetic CARLA adverse weather scenes with rain, fog, and nighttime conditions).
  2. Record true per-movement bounding box detection errors and count deviations relative to annotated ground truth.
  3. Re-fit the logistic uncertainty estimator using genuine vision features (mean detection confidence, bounding box jitter, track loss rate).
  4. Evaluate whether a vision-calibrated uncertainty score triggers fallback more effectively during true visual degradation than during benign synthetic noise.
- **Expected Outcome / Impact**: Upgrades the uncertainty estimator from an arbitrary simulator error predictor to a validated perception-safety monitor.

#### Experiment 2.2: Full Execution of the SUMO Service Ledger Panel (144 Runs)
- **Current Limitation**: The service ledger study (`results/sumo_service_ledger/full_20261103/report.json`) successfully evaluated debt-batch and service-ledger mechanisms designed to eliminate starvation without incurring the +0.44s shield penalty, but execution was cut short at **111 of 144 runs** due to hitting the 3,600-second session cap.
- **Proposed Protocol**:
  1. Complete the remaining 33 episodes across sessions 0002 and 0003 using `research/pilots/run_sumo_service_ledger_panel.py`.
  2. Compute final paired contrasts against Max-Pressure and Watchdog baselines.
- **Expected Outcome / Impact**: Provides a complete, publication-ready evaluation of service-ledger control as a viable alternative to heuristic safety shields.

#### Experiment 2.3: Matched-Recipe Unshielded Policy Training Ablation
- **Current Limitation**: In the existing 2,800-run evaluation, the "Bare D3QN" controller was evaluated by simply bypassing the safety shield on a policy that had been *trained in an environment with safety watchdogs and max-green penalties*. This is an inference-time intervention, not a matched training ablation.
- **Proposed Protocol**:
  1. Train 3 independent replicas of D3QN completely from scratch in an unshielded environment (no starvation penalties, no watchdog overrides).
  2. Evaluate the unshielded-trained policy against the shielded-trained policy.
- **Expected Outcome / Impact**: Establishes whether policies trained specifically without safety constraints discover different reward optima or whether they inevitably induce catastrophic approach starvation.

---

## Priority 3: Low / Desirable Extensions (Strengthening Generalization)

#### Experiment 3.1: Multi-Intersection Arterial Corridor Progression Study
- **Current Limitation**: All primary evaluations are confined to an isolated 4-way intersection. Real municipal traffic involves arterial coordination, vehicle platooning, and queue spillback between adjacent intersections.
- **Proposed Protocol**:
  1. Construct a 3-intersection arterial corridor network in SUMO.
  2. Compare independent FlowSync-UQ controllers against coordinated Max-Pressure and actuated green-wave timing plans.
  3. Measure network throughput, progression speed, and spillback frequency.
- **Expected Outcome / Impact**: Assesses multi-agent scalability and reveals whether local fallback decisions cause downstream arterial disruptions.

---

## 2. Summary of Experiments to AVOID Rerunning

To preserve research integrity and prevent resource waste:
1. **DO NOT rerun the 2,800-run custom simulator panel**: The data in `matched_shield_v5_20261015/runs.jsonl` is complete, uncorrupted, and statistically definitive.
2. **DO NOT rerun the 360-second SUMO robustness study**: The 24-run panel in `results/sumo_robustness/full_20261023` already definitively proved that over 360 seconds, counting errors cause +39.5% P95 delay and severe minor-approach starvation. Rerunning this would be redundant.
3. **DO NOT retrain D3QN or PPO on the isolated intersection expecting superiority over Max-Pressure**: Both D3QN and PPO have been empirically and mathematically proven to converge to or trail Max-Pressure on this single-stage topology.
4. **DO NOT perform ad-hoc threshold sweeps**: Arbitrary manual tuning of $\tau_{\mathrm{high}}$ and $\tau_{\mathrm{low}}$ without genuine camera error data constitutes p-hacking and does not solve the fundamental perception-control gap.
