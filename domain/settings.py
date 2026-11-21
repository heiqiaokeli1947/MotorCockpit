"""配置持久化：JSON 存 flash，掉电不丢（亮度、单位、WS2812 效果等）。"""
import json
import os

import config

_FILE = "/settings.json"
_DEFAULTS = {
    "backlight": 100,
    "auto_brightness": True,
    "unit_speed": "kmh",   # kmh / mph
    "unit_temp": "c",      # c / f
    "ws2812_mode": "off",  # off / ambient / rpm / turn
    "ws2812_color": [0, 229, 255],
    "ws2812_brightness": 80,
}


class Settings:
    _instance = None

    def __init__(self):
        self._data = dict(_DEFAULTS)
        self.load()

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def load(self):
        try:
            with open(_FILE) as f:
                saved = json.load(f)
            self._data.update(saved)
        except (OSError, ValueError):
            pass

    def save(self):
        try:
            with open(_FILE, "w") as f:
                json.dump(self._data, f)
        except OSError:
            pass

    def get(self, key, default=None):
        return self._data.get(key, default)

    def set(self, key, value):
        self._data[key] = value
        self.save()

    def all(self):
        return dict(self._data)
