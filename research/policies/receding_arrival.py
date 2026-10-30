"""Cadence-alignment experiment; the arrival decision formula stays unchanged."""
from research.policies.arrival_extension import ArrivalExtension

VERSION = "receding_arrival_v1"
# The running-demand/prediction horizon remains 2 s for all adaptations. These
# are control-rate adaptations, not exact reproductions of the published setup.
SPECS = {
    "mp_all_native": ("mp_all_native", 1),
    "mp_all_2s": ("mp_all_native", 20),
    "mp_upstream_native": ("mp_upstream_native", 1),
    "advanced_mp_w1": ("advanced_mp_w1", 1),
    "advanced_mp_w2": ("advanced_mp_w2", 1),
    "advanced_mp_w4": ("advanced_mp_w4", 1),
    "age_gated_advanced_mp": ("age_gated_advanced_mp", 1),
    "receding_point": ("point_extension", 1),
    "receding_no_age": ("no_age_extension", 1),
    "window_2s": ("window_extension", 20),
    "receding_window": ("window_extension", 1),
}
PRIMARY = "receding_window"


class CadencedArrival(ArrivalExtension):
    def __init__(self, label, timing):
        if label not in SPECS:
            raise ValueError("Unknown frozen cadence-alignment method")
        base_method, cadence = SPECS[label]
        super().__init__(base_method, timing)
        self.label, self.cadence = label, cadence

    def act(self, state, context):
        proposal = super().act(state, context)
        if self.diagnostics["gate"]:
            self.next_decision = context.timestep+self.cadence
        return proposal
