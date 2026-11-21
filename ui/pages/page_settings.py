"""设置页：列表菜单，上下选择 / OK 进入编辑 / 取消返回。

M1 实现选择高亮与值展示；编辑保存逻辑 M3 补全。参考 app.py 菜单交互。
"""
import lvgl as lv

from ui import theme
from ui.page_base import Page


class PageSettings(Page):
    name = "设置"

    def __init__(self, app):
        super().__init__(app)
        self.items = []     # (label, key, getter)
        self.labels = []
        self.idx = 0

    def build(self, parent):
        super().build(parent)
        root = self._root
        W = 480
        theme.label(root, "设置", 12, 6, color=theme.TEXT, font=theme.FONT_BODY)
        theme.hline(root, 0, 28, W)

        self.items = [
            ("背光亮度", "backlight", lambda s: "%d%%" % s.get("backlight", 100)),
            ("自动亮度", "auto_brightness", lambda s: "开" if s.get("auto_brightness") else "关"),
            ("速度单位", "unit_speed", lambda s: "km/h" if s.get("unit_speed") == "kmh" else "mph"),
            ("温度单位", "unit_temp", lambda s: "°C" if s.get("unit_temp") == "c" else "°F"),
            ("WS2812 模式", "ws2812_mode", lambda s: s.get("ws2812_mode", "off")),
            ("WS2812 亮度", "ws2812_brightness", lambda s: "%d" % s.get("ws2812_brightness", 80)),
        ]
        self.labels = []
        for i, (title, key, getter) in enumerate(self.items):
            y = 44 + i * 34
            lab = theme.label(root, title, 24, y, color=theme.TEXT, font=theme.FONT_BODY)
            val = theme.label(root, "", 360, y, color=theme.ACCENT_CYAN, font=theme.FONT_BODY)
            self.labels.append((lab, val))
        theme.label(root, "上下选择  OK编辑  取消返回", 12, 292,
                    color=theme.MUTED, font=theme.FONT_SMALL)
        self._refresh()
        return root

    def _refresh(self):
        s = self.settings
        for i, (lab, val) in enumerate(self.labels):
            title, key, getter = self.items[i]
            val.set_text(getter(s))
            lab.set_style_text_color(
                lv.color_hex(theme.ACCENT_CYAN if i == self.idx else theme.TEXT), 0
            )

    def update(self):
        self._refresh()

    def on_event(self, event):
        if event == "up":
            self.idx = (self.idx - 1) % len(self.items)
            self._refresh()
            return True
        if event == "down":
            self.idx = (self.idx + 1) % len(self.items)
            self._refresh()
            return True
        if event in ("ok", "enc_press"):
            # M3：进入编辑模式
            print("设置项选中：%s" % self.items[self.idx][0])
            return True
        return False
