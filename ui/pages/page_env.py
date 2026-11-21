"""环境 / 姿态页：温湿度气压 + 加速度 + 俯仰横滚。

趋势图 lv_chart 待部署验证 API 后添加；M1 用数值 + 进度条。
"""
import lvgl as lv

from ui import theme
from ui.page_base import Page

INVALID = -9999


def _fmt(val, template, invalid="--"):
    if val is None or val == INVALID:
        return invalid
    return template % val


def _bar(parent, x, y, w, h, lo, hi, color):
    bar = lv.bar(parent)
    bar.set_pos(x, y)
    bar.set_size(w, h)
    bar.set_range(lo, hi)
    bar.set_value(0, 0)
    bar.set_style_bg_color(lv.color_hex(0x1A2332), 0)
    bar.set_style_bg_opa(lv.OPA.COVER, 0)
    bar.set_style_border_width(0, 0)
    bar.set_style_radius(h // 2, 0)
    bar.set_style_pad_all(0, 0)
    bar.set_style_bg_color(lv.color_hex(color), lv.PART.INDICATOR)
    bar.set_style_bg_opa(lv.OPA.COVER, lv.PART.INDICATOR)
    bar.set_style_radius(h // 2, lv.PART.INDICATOR)
    return bar


class PageEnv(Page):
    name = "环境姿态"

    def build(self, parent):
        super().build(parent)
        root = self._root
        W = 480

        theme.label(root, "--:--", 12, 6, font=theme.FONT_MID)  # 占位时钟
        theme.hline(root, 0, 28, W)

        # 左：环境
        self.lbl_temp = theme.label(root, "温度 --°C", 24, 48, color=theme.TEXT, font=theme.FONT_BODY)
        self.lbl_hum = theme.label(root, "湿度 --%", 24, 80, color=theme.TEXT, font=theme.FONT_BODY)
        self.lbl_press = theme.label(root, "气压 -- Pa", 24, 112, color=theme.TEXT, font=theme.FONT_BODY)

        # 右：姿态
        self.lbl_pitch = theme.label(root, "俯仰 --°", 260, 48, color=theme.ACCENT_ORANGE, font=theme.FONT_BODY)
        self.lbl_roll = theme.label(root, "横滚 --°", 260, 80, color=theme.ACCENT_ORANGE, font=theme.FONT_BODY)
        self.lbl_g = theme.label(root, "G --", 260, 112, color=theme.ACCENT_CYAN, font=theme.FONT_BODY)

        # 加速度条 x/y/z
        self.lbl_ax = theme.label(root, "X", 24, 170, color=theme.MUTED, font=theme.FONT_SMALL)
        self.bar_ax = _bar(root, 50, 168, 180, 12, -20, 20, theme.ACCENT_CYAN)
        self.lbl_ay = theme.label(root, "Y", 24, 196, color=theme.MUTED, font=theme.FONT_SMALL)
        self.bar_ay = _bar(root, 50, 194, 180, 12, -20, 20, theme.ACCENT_ORANGE)
        self.lbl_az = theme.label(root, "Z", 24, 222, color=theme.MUTED, font=theme.FONT_SMALL)
        self.bar_az = _bar(root, 50, 220, 180, 12, 0, 20, theme.PURPLE)

        # 倾斜可视化：横滚角左右条
        self.bar_roll = _bar(root, 260, 168, 200, 14, -45, 45, theme.ACCENT_ORANGE)
        theme.label(root, "横滚", 260, 190, color=theme.MUTED, font=theme.FONT_SMALL)
        self.lbl_roll_val = theme.label(root, "--°", 380, 188, color=theme.TEXT, font=theme.FONT_BODY)

        return root

    def update(self):
        bus = self.bus
        self.lbl_temp.set_text("温度 %s°C" % _fmt(bus.get("temperature"), "%.1f"))
        self.lbl_hum.set_text("湿度 %s%%" % _fmt(bus.get("humidity"), "%.0f"))
        self.lbl_press.set_text("气压 %s Pa" % _fmt(bus.get("pressure"), "%d"))
        self.lbl_pitch.set_text("俯仰 %s°" % _fmt(bus.get("pitch"), "%.1f"))
        self.lbl_roll.set_text("横滚 %s°" % _fmt(bus.get("roll"), "%.1f"))
        az = bus.get("accel_z")
        g = round(az, 2) if az not in (None, INVALID) else INVALID
        self.lbl_g.set_text("G %s" % _fmt(g, "%.2f"))
        for key, bar in (("accel_x", self.bar_ax), ("accel_y", self.bar_ay), ("accel_z", self.bar_az)):
            v = bus.get(key)
            if v in (None, INVALID):
                v = 0
            bar.set_value(int(v * 10), 0)
        roll = bus.get("roll")
        if roll in (None, INVALID):
            roll = 0
        self.bar_roll.set_value(int(roll), 0)
        self.lbl_roll_val.set_text("%s°" % _fmt(bus.get("roll"), "%.0f"))
