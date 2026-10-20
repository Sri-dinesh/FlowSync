"""Research-only wrapper for matched baseline/shield component comparisons."""
from dataclasses import replace

from server.app.controllers.base import BaseController
from server.app.controllers.safety_shield import SafetyShield


class ShieldedController(BaseController):
    """Apply the unchanged sensor-only shield on every simulation microtick."""

    def __init__(self, controller):
        super().__init__(name=f"{controller.name}_shield")
        self.controller = controller
        self.shield = SafetyShield()

    def reset(self, seed=None):
        super().reset(seed)
        self.controller.reset(seed)
        self.shield.reset()

    def get_capabilities(self):
        return replace(self.controller.get_capabilities(), name=self.name,
                       supports_safety_shield=True)

    def act(self, observation, context):
        self._step_count += 1
        proposed = self.controller.act(observation, context)
        decision = self.shield.filter_context(proposed, context)
        self._last_diagnostics = {"controller": self.name, **decision.to_dict()}
        return decision.executed_action

    def get_diagnostics(self):
        return {**self.controller.get_diagnostics(), **self._last_diagnostics,
                "shield_enabled": True, "fallback_enabled": False,
                "shield": self.shield.get_audit_metrics()}
