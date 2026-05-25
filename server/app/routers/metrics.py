from fastapi import APIRouter, Request

from ..schemas.metrics_schema import MetricsSnapshot

router = APIRouter(prefix="/metrics", tags=["metrics"])


def _build_snapshot(app_state: dict) -> MetricsSnapshot:
    intersection = app_state["intersection"]
    queue_lengths = intersection.get_queue_lengths()
    max_queue = max(queue_lengths.values(), default=0)
    trainer = app_state.get("trainer")

    return MetricsSnapshot(
        avg_wait_time=intersection.get_avg_wait_time(),
        throughput=intersection.total_passed,
        max_queue=max_queue,
        current_phase=intersection.signal.current_phase,
        is_training=trainer.is_training if trainer else False,
        current_episode=trainer.current_episode if trainer else 0,
        epsilon=trainer.epsilon if trainer else 0.0,
    )


@router.get("/current", response_model=MetricsSnapshot)
async def get_current_metrics(request: Request) -> MetricsSnapshot:
    app_state = request.app.state.app_state
    return _build_snapshot(app_state)
