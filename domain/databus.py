"""数据总线：所有传感器发布最新值，UI 订阅读取。

泛化自 CustomMicropython 的 Environment。新增硬件 = 加一个发布者，UI 零改动。
统一老化：超过 SENSOR_STALE_MS 未更新的值读出来为 INVALID（_KB/CON-0006）。
"""
import time

import config


class DataBus:
    _instance = None

    def __init__(self):
        # key -> [value, timestamp_ms]
        self._data = {}
        self._subscribers = []  # 暂留扩展：值变化回调

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def publish(self, key, value):
        """发布一个最新值。value 为 INVALID 时也记录（表示传感器故障）。"""
        self._data[key] = [value, time.ticks_ms()]

    def get(self, key, default=None):
        """读取当前值，已老化返回 INVALID。"""
        entry = self._data.get(key)
        if entry is None:
            return config.INVALID if default is None else default
        if time.ticks_diff(time.ticks_ms(), entry[1]) > config.SENSOR_STALE_MS:
            return config.INVALID
        return entry[0]

    def get_stale(self, key):
        """读原始值（不做老化检查），用于趋势记录。"""
        entry = self._data.get(key)
        return entry[0] if entry else config.INVALID

    def is_stale(self, key):
        entry = self._data.get(key)
        if entry is None:
            return True
        return time.ticks_diff(time.ticks_ms(), entry[1]) > config.SENSOR_STALE_MS

    def keys(self):
        return list(self._data.keys())

    def snapshot(self):
        return {k: self.get(k) for k in self._data}
