"""环形缓冲：用于趋势图（温度/气压等历史序列）。

泛化自 CustomMicropython 的 history_t / history_h。
"""
import time


class History:
    def __init__(self, capacity=60):
        self.capacity = capacity
        self.times = []
        self.values = []

    def append(self, value):
        if value is None or value == -9999:
            return
        self.times.append(time.ticks_ms())
        self.values.append(value)
        if len(self.values) > self.capacity:
            self.times.pop(0)
            self.values.pop(0)

    def latest(self):
        return self.values[-1] if self.values else -9999

    def series(self):
        return list(self.values)

    def clear(self):
        self.times.clear()
        self.values.clear()
