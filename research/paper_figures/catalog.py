"""Figure descriptions and source attribution; no empirical measurements."""
from dataclasses import dataclass
from importlib import import_module


@dataclass(frozen=True)
class Figure:
    identifier: str
    title: str
    module: str
    function: str
    caption: str
    sources: tuple[str, ...]
    status: str = "implementation_schematic"

    def render(self):
        return getattr(import_module("research.paper_figures."+self.module),self.function)()


FIGURES = (
    Figure("fig01_system_architecture", "System architecture", "architecture", "system_architecture",
        "FlowSync execution paths and ownership. The interactive application, audited custom-simulator research, independent two-phase SUMO studies and experimental camera workflow have separate input and evidence contracts. Arrows summarize data ownership; they do not establish numerical equivalence or physical signal actuation.",
        ("server/app/main.py","client/package.json","research/experiments/engine.py","research/experiments/sumo_service_ledger.py","server/app/realworld/pipeline/cctv_pipeline.py")),
    Figure("fig02_control_boundary", "Audited control and data boundary", "architecture", "control_boundary",
        "Audited custom-simulator control loop. Delivered synthetic observations supply the policy, context and masks. Optional fallback and additional shielding precede the shared physical signal FSM. Executed lamps and simulator truth support separate audits and evaluation; clean truth is not substituted into corrupted controller inputs.",
        ("research/experiments/engine.py","research/experiments/runtime.py","research/noise/fault_injector.py","server/app/controllers/supervisor.py","server/app/controllers/safety_shield.py","server/app/simulation/traffic_signal.py")),
    Figure("fig03_observation_schemas", "Versioned observation schemas", "learning", "observation_schemas",
        "Version-specific numeric input encodings. The 28-dimensional base expands to 36 observed features, 64 temporal features or 48 spatial features. Temporal lags are 10 and 30 delivered 0.1-second ticks. The four temporal tail fields encode observation age, two lag-availability indicators and age-known status. Matched controls zero only the added temporal or spatial inputs. One encoding is selected per checkpoint.",
        ("server/app/rl/observations.py",)),
    Figure("fig04_dueling_network", "Masked dueling network", "learning", "dueling_network",
        "Dueling network for the custom simulator. Two shared 256-unit Linear/LayerNorm/ReLU blocks feed 128-unit value and advantage heads. The implementation centers advantages over valid actions when a mask is supplied, then selects an allowed phase. The four outputs do not transfer automatically to two-phase SUMO.",
        ("server/app/rl/dqn_network.py","server/app/rl/dqn_agent.py","server/app/rl/observations.py")),
    Figure("fig05_research_training", "Audited research learning workflow", "learning", "research_training",
        "Corrected custom-simulator research learning path. Optional teacher data and completed online decision-to-decision transitions enter prioritized replay. Masked Double-DQN targets, importance-weighted Smooth L1 loss and an eligible demonstration margin update online weights; target weights are copied periodically. Validation and checkpoint identity are recorded separately. Warm-start stages and settings depend on the declared run; this is not the legacy website v4 collector.",
        ("research/training/train_policy.py","server/app/rl/dqn_agent.py","server/app/rl/replay_buffer.py","server/app/simulation/environment.py")),
    Figure("fig06_signal_execution", "Physical signal execution", "signals", "physical_signal",
        "Independent SUMO physical signal contract and an illustrative legal transition. A request after eight seconds of green enters three seconds of yellow and one second of all-red before the committed target becomes green. The timeline is a timing illustration, not measured traffic. Other project runtimes retain their own timing configuration.",
        ("research/audits/sumo_branch_feasibility.py",)),
    Figure("fig07_ledger_mechanism", "Service-ledger mechanism", "ledger", "ledger_mechanism",
        "Research-only service-ledger transaction. Delivered pressures and stored allocation debt choose a target and committed green budget at an unlocked eligible gate. The physical FSM executes the request; only validated actual target-green receipts retire the budget. Clearance gives no green credit. The equations specify the local hybrid mechanism, not a traffic benefit or global novelty guarantee.",
        ("research/policies/sumo_service_ledger.py","research/experiments/sumo_service_ledger.py","research/manifests/service_ledger_design.json")),
    Figure("fig08_ledger_witness", "Constructed allocation-history witness", "ledger", "ledger_witness",
        "Constructed service-ledger witness using the existing policy and physical-clock audit. Two continuously positive pressure histories reach identical current counts and signal clocks at 24 seconds, yet choose different targets because their allocation debts differ. The balanced history commits 16 seconds of EW green after clearance; subsequent NS-only pressure also illustrates the potential cost of commitment. These are constructed packet sequences, not native traffic or delay results.",
        ("research/audits/audit_sumo_service_ledger.py","research/policies/sumo_service_ledger.py","research/policies/sumo_classical.py","research/audits/sumo_branch_feasibility.py"),"constructed_mechanism_illustration"),
    Figure("fig09_paired_study_design", "Paired study design", "signals", "study_design",
        "Deferred service-ledger scientific design: six traffic seeds in three known demand families, two starting phases, two sensing conditions and six controllers produce 144 paired episodes. The 360-second endpoint is primary; the 180-second prefix overlaps it. Starts are averaged within traffic seed before family-stratified resampling. The diagram describes a frozen plan, not completed scientific collection.",
        ("research/manifests/sumo_service_ledger_panel.json","research/pilots/run_sumo_service_ledger_panel.py","research/analysis/sumo_service_ledger_metrics.py"),"deferred_protocol_schematic"),
    Figure("fig10_evidence_workflow", "Evidence and reproducibility workflow", "architecture", "evidence_workflow",
        "Evidence ownership and reproducibility workflow. Frozen source/configuration/model identities accompany executed packets, proposals and lamps. Saved traces, source archives and runtime hashes support reconstruction and provenance-aware exports. Offline verification does not independently rerun native trajectories; ignored local artifacts require separate distribution.",
        ("research/experiments/sumo_panel.py","research/evidence/export_methodology.py","research/audits/verify_sumo_panel.py","research/audits/audit_training_results.py")),
)


def select(identifiers=None):
    lookup = {f.identifier:f for f in FIGURES}
    if identifiers is None:
        return list(FIGURES)
    if not identifiers or len(set(identifiers)) != len(identifiers) or set(identifiers)-set(lookup):
        raise ValueError("Choose unique known figure identifiers; use --list")
    return [lookup[name] for name in identifiers]
