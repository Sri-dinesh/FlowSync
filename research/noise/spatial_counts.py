"""Partition legacy detections without changing their count or random stream."""
import numpy as np


def bounded_upstream(upstream, reconstructed_total):
    values, total = np.asarray(upstream), np.asarray(reconstructed_total)
    if (values.shape != (12,) or total.shape != (12,) or not np.isfinite(values).all()
            or not np.isfinite(total).all() or (values < 0).any() or (total < 0).any()
            or not np.equal(values, np.floor(values)).all() or not np.equal(total, np.floor(total)).all()):
        raise ValueError("Spatial counts must be twelve finite nonnegative integers")
    # Match legacy tanh/float32 reconstruction at its upper saturation limit.
    return np.minimum(values, total).astype(int)


def thin_partition(upstream, total, detected, rng):
    """Conditional binomial thinning: sampled survivors are a subset of total."""
    up, total, detected = np.asarray(upstream, int), np.asarray(total, int), np.asarray(detected, int)
    if (up.shape != (12,) or total.shape != (12,) or detected.shape != (12,)
            or (up < 0).any() or (up > total).any() or (detected < 0).any() or (detected > total).any()):
        raise ValueError("Invalid spatial detection partition")
    result = np.zeros(12, dtype=int)
    active = total > 0
    result[active] = rng.hypergeometric(up[active], total[active] - up[active], detected[active])
    return result


def jitter_partition(upstream, before, after, rng):
    """Remove detected items uniformly, or allocate new jitter detections equally."""
    before, after = np.asarray(before, int), np.asarray(after, int)
    retained = thin_partition(upstream, before, np.minimum(before, after), rng)
    return retained + rng.binomial(np.maximum(0, after - before), .5)
