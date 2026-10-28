import numpy as np

from research.cv.audit_camera_boundary import SPECIFICATION, movement_completions, state
from server.app.rl.observations import OBSERVED_VERSION, encode_policy_observation


def test_completion_set_preserves_every_approach_total_and_removes_only_duplicates():
    counts = []
    for totals in SPECIFICATION["approach_patterns"]:
        variants = list(movement_completions(totals))
        assert len({tuple(v.values()) for v in variants}) == len(variants)
        for variant in variants:
            for direction, total in zip(SPECIFICATION["direction_order"], totals):
                assert sum(variant[f"{direction}_{turn}"] for turn in ("straight", "left", "right")) == total
        counts.append(len(variants))
    assert counts == [81, 81, 81, 81, 9, 9]


def test_identical_approach_counts_allow_different_observation_and_mask():
    variants = list(movement_completions([2, 2, 2, 2]))
    straight, ctx_a = state(variants[0], 0)
    left, ctx_b = state(variants[-1], 0)
    assert ctx_a.valid_action_mask.tolist() == [True, True, False, False]
    assert ctx_b.valid_action_mask.tolist() == [True, False, True, True]
    assert np.array_equal(straight[12:], left[12:])
    assert not np.array_equal(straight[:12], left[:12])
    assert encode_policy_observation(straight, ctx_a, OBSERVED_VERSION).shape == (36,)
