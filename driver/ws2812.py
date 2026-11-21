"""WS2812 / NeoPixel 灯带封装（内置 neopixel 模块，底层 RMT）。

验证状态：code-only（待硬件验证）。颜色顺序按 GRB（WS2812 常见）。
"""
import machine

try:
    import neopixel
except ImportError:
    neopixel = None

import config


class WS2812:
    def __init__(self, pin=None, count=None, brightness=None):
        if neopixel is None:
            raise RuntimeError("固件未内置 neopixel 模块")
        self.pin = pin if pin is not None else config.WS2812_PIN
        self.count = count if count is not None else config.WS2812_COUNT
        self.brightness = brightness if brightness is not None else config.WS2812_DEFAULT_BRIGHTNESS
        self._np = neopixel.NeoPixel(machine.Pin(self.pin), self.count)
        self._buf = [(0, 0, 0)] * self.count

    def _scale(self, color):
        r, g, b = color
        s = self.brightness / 255
        return (int(r * s), int(g * s), int(b * s))

    def set(self, index, r, g, b):
        if 0 <= index < self.count:
            self._buf[index] = (r, g, b)

    def fill(self, r, g, b):
        for i in range(self.count):
            self._buf[i] = (r, g, b)

    def clear(self):
        self.fill(0, 0, 0)

    def show(self):
        for i in range(self.count):
            self._np[i] = self._scale(self._buf[i])
        self._np.write()

    def set_brightness(self, value):
        self.brightness = max(0, min(255, int(value)))
