"""Own training preparation and task errors within one application event loop."""
from contextlib import contextmanager
import asyncio
import logging

logger = logging.getLogger(__name__)


def training_busy(state) -> bool:
    task = getattr(state,"training_task",None)
    return bool(getattr(state,"training_state_reserved",False) or state.trainer.is_training
        or (task is not None and not task.done()))


@contextmanager
def reserve_training_state(state):
    """Reserve before the first await in start/load preparation.

    The synchronous claim applies to this process's application event loop;
    it is not a lock across processes or independent worker threads.
    """
    if training_busy(state):
        yield False
        return
    state.training_state_reserved = True
    try:
        yield True
    finally:
        state.training_state_reserved = False


async def run_training(trainer, *args, **kwargs) -> None:
    """Deliver background failures through the same progress callback as training."""
    try:
        await trainer.train(*args,**kwargs)
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        logger.exception("Training task failed")
        await trainer.ws_broadcast_fn({
            "type":"training_error","is_training":trainer.is_training,
            "message":str(exc) or exc.__class__.__name__,
        })
