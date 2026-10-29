"""Research-only switch-margin calibration; frozen D3QN weights are retained."""
import math
from dataclasses import replace

from server.app.controllers.d3qn import D3QNController
from server.app.controllers.max_pressure import MaxPressureController


def check_margin(margin):
    if not math.isfinite(margin) or margin < 0:
        raise ValueError("Switch margin must be finite and nonnegative.")
    return float(margin)


class SwitchMarginD3QN(D3QNController):
    def __init__(self, checkpoint_path, margin):
        super().__init__(checkpoint_path=checkpoint_path)
        self.margin = check_margin(margin)
        self.name = "d3qn_switch_margin"
        self.margin_holds = self.switch_proposals = 0

    def reset(self, seed=None):
        super().reset(seed)
        self.margin_holds = self.switch_proposals = 0

    def get_capabilities(self):
        return replace(super().get_capabilities(), name=self.name,
                       description="Frozen D3QN with episode-fitted switch margin")

    def act(self, observation, context):
        decision = context.is_decision_step and context.timestep >= self._next_decision_step
        action = super().act(observation, context)
        if decision and context.can_switch_phase and action != context.current_phase:
            self.switch_proposals += 1
            q = self._last_diagnostics["q_values"]
            current = context.current_phase
            valid = context.valid_action_mask is None or context.valid_action_mask[current]
            if self.margin > 0 and valid and q[action]-q[current] <= self.margin:
                action = self._held_action = current
                self.margin_holds += 1
                self._last_diagnostics["selected_action"] = action
        return action

    def get_diagnostics(self):
        return {**super().get_diagnostics(), "switch_margin": self.margin,
                "margin_holds": self.margin_holds, "switch_proposals": self.switch_proposals}


class SwitchMarginPressure(MaxPressureController):
    def __init__(self, margin):
        super().__init__()
        self.margin = check_margin(margin)
        self.name = "max_pressure_switch_margin"
        self.margin_holds = self.switch_proposals = 0

    def reset(self, seed=None):
        super().reset(seed)
        self.margin_holds = self.switch_proposals = 0

    def get_capabilities(self):
        return replace(super().get_capabilities(), name=self.name,
                       description="Max-Pressure with episode-fitted switch margin")

    def act(self, observation, context):
        action = super().act(observation, context)
        if context.can_switch_phase and action != context.current_phase:
            self.switch_proposals += 1
            pressure = self._last_diagnostics["phase_pressures"]
            if self.margin > 0 and pressure[action]-pressure[context.current_phase] <= self.margin:
                action = context.current_phase
                self.margin_holds += 1
                self._last_diagnostics["selected_phase"] = action
        return action

    def get_diagnostics(self):
        return {**super().get_diagnostics(), "switch_margin": self.margin,
                "margin_holds": self.margin_holds, "switch_proposals": self.switch_proposals}
