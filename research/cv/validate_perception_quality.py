"""Disabled legacy generator: its random metrics were not measured CV results."""


def run_cv_validation_evaluation(*args, **kwargs):
    raise RuntimeError(
        "Disabled: this generator fabricated perception metrics without annotations. "
        "Use research.cv.evaluate_crossings with recorded sessions and independently labeled video."
    )


if __name__ == "__main__":
    run_cv_validation_evaluation()
