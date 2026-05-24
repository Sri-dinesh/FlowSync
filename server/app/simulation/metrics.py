from typing import Dict

from .intersection import Intersection


class MetricsTracker:
    def __init__(self) -> None:
        self._ticks = 0
        self._total_wait_time = 0.0
        self._total_throughput = 0
        self._total_queue_length = 0
        self._last_passed_total = 0
        self._last_reward = 0.0
        self._last_queue_lengths: Dict[str, int] = {}
        self._last_total_waiting = 0
        self._last_avg_wait = 0.0
        self._last_throughput = 0

    def update(self, intersection: Intersection, reward: float) -> None:
        self._ticks += 1
        self._last_reward = reward

        queue_lengths = intersection.get_queue_lengths()
        total_waiting = intersection.get_total_waiting()
        avg_wait = intersection.get_avg_wait_time()
        throughput = intersection.total_passed - self._last_passed_total

        self._last_passed_total = intersection.total_passed
        self._last_queue_lengths = queue_lengths
        self._last_total_waiting = total_waiting
        self._last_avg_wait = avg_wait
        self._last_throughput = throughput

        self._total_wait_time += avg_wait
        self._total_queue_length += total_waiting
        self._total_throughput += throughput

    def get_snapshot(self) -> Dict[str, float | int | Dict[str, int]]:
        if self._ticks == 0:
            return {
                "avg_wait_time": 0.0,
                "avg_throughput": 0.0,
                "avg_queue_length": 0.0,
                "queue_lengths": {},
                "total_waiting": 0,
                "reward": 0.0,
                "last_throughput": 0,
            }

        return {
            "avg_wait_time": self._total_wait_time / self._ticks,
            "avg_throughput": self._total_throughput / self._ticks,
            "avg_queue_length": self._total_queue_length / self._ticks,
            "queue_lengths": self._last_queue_lengths,
            "total_waiting": self._last_total_waiting,
            "reward": self._last_reward,
            "last_throughput": self._last_throughput,
        }

    def reset(self) -> None:
        self.__init__()
