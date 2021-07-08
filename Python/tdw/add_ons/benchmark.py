from time import time
from typing import List
from tdw.add_ons.add_on import AddOn


class Benchmark(AddOn):
    """
    Benchmark the FPS over a given number of frames.

    ```python
    from tdw.controller import Controller
    from tdw.add_ons.benchmark import Benchmark

    c = Controller()
    b = Benchmark()
    b.start()
    c.add_ons.append(b)
    while b.fps < 0:
        c.communicate([])
    b.stop()
    c.communicate({"$type": "terminate"})
    print(b.speed)
    ```
    """

    def __init__(self):
        """
        (no parameters)
        """

        super().__init__()
        self.initialized = True
        """:field
        A list of time elapsed per `communicate()` call.
        """
        self.times: List[float] = list()
        # If True, we are currently benchmarking.
        self._benchmarking: bool = False
        # The initial time.
        self._t0: float = -1

    def get_initialization_commands(self) -> List[dict]:
        return []

    def before_send(self, commands: List[dict]) -> None:
        if self._benchmarking:
            self._t0 = time()

    def on_send(self, resp: List[bytes]) -> None:
        # Clock the benchmark.
        if self._benchmarking:
            t1 = time()
            self.times.append(t1 - self._t0)
            self._t0 = t1

    def start(self) -> None:
        """
        Start bencharking each `communicate()` call and clear `self.times`.
        """

        self.times.clear()
        self._benchmarking = True

    def stop(self) -> None:
        """
        Stop benchmarking each `communicate()` call.
        """

        self._benchmarking = False

    def get_speed(self) -> float:
        """
        :return: The average time elapsed per `communicate()` call.
        """

        if len(self.times) == 0:
            return -1
        else:
            return sum(self.times) / len(self.times)