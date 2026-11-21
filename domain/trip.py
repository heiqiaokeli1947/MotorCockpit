"""行程统计：本次行程 + 累计，JSON 持久化到 flash。

速度来自 DataBus 的 speed_kmh，按时间积分算里程。M3 接入真实数据。
"""
import json
import time

import config

_FILE = config.TRIP_FILE
INVALID = -9999


class Trip:
    _instance = None

    def __init__(self, bus):
        self.bus = bus
        self.cur = {
            "start_ms": None,
            "km": 0.0,
            "time_s": 0,
            "max_speed": 0,
            "speed_sum": 0.0,
            "speed_n": 0,
        }
        self.total = {"km": 0.0, "time_s": 0}
        self._last_ms = None
        self.load()

    @classmethod
    def instance(cls, bus=None):
        if cls._instance is None:
            cls._instance = cls(bus)
        return cls._instance

    def load(self):
        try:
            with open(_FILE) as f:
                saved = json.load(f)
            self.total.update(saved.get("total", {}))
        except (OSError, ValueError):
            pass

    def save(self):
        try:
            with open(_FILE, "w") as f:
                json.dump({"total": self.total}, f)
        except OSError:
            pass

    def start(self):
        self.cur = {
            "start_ms": time.ticks_ms(),
            "km": 0.0,
            "time_s": 0,
            "max_speed": 0,
            "speed_sum": 0.0,
            "speed_n": 0,
        }
        self._last_ms = time.ticks_ms()

    def update(self):
        """每个 UI 周期调用：用速度积分里程。"""
        now = time.ticks_ms()
        if self.cur["start_ms"] is None:
            self.start()
        if self._last_ms is None:
            self._last_ms = now
        dt = time.ticks_diff(now, self._last_ms) / 1000.0
        self._last_ms = now
        speed = self.bus.get("speed_kmh")
        if speed not in (None, INVALID) and speed > 0:
            self.cur["km"] += speed * dt / 3600.0
            self.cur["time_s"] += dt
            self.cur["speed_sum"] += speed
            self.cur["speed_n"] += 1
            if speed > self.cur["max_speed"]:
                self.cur["max_speed"] = speed
        # 发布到总线
        self.bus.publish("trip_km", round(self.cur["km"], 1))
        self.bus.publish("trip_time_s", int(self.cur["time_s"]))
        self.bus.publish("avg_speed", self._avg())
        self.bus.publish("max_speed", int(self.cur["max_speed"]))
        self.bus.publish("total_km", round(self.total["km"], 1))
        self.bus.publish("total_time_s", int(self.total["time_s"]))

    def _avg(self):
        if self.cur["speed_n"] == 0:
            return 0
        return round(self.cur["speed_sum"] / self.cur["speed_n"], 1)

    def stop_and_save(self):
        self.total["km"] += self.cur["km"]
        self.total["time_s"] += self.cur["time_s"]
        self.save()
        self.cur["start_ms"] = None

    def reset_current(self):
        self.start()
