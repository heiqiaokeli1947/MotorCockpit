"""主驾驶页（默认页）：速度大数字 + RPM 进度 + 状态栏 + 卡片行。

M1 数据来自 DataBus（由模拟数据源或真实传感器发布）。
炫酷指针圆弧（lv_scale/lv_arc）待部署验证 API 后在 widgets/gauge.py 替换。
"""
import lvgl as lv

from ui import theme
from ui.page_base import Page

INVALID = -9999


def _fmt(val, template, invalid="--"):
    if val is None or val == INVALID:
        return invalid
    return template % val


class PageDash(Page):
    name = "主驾驶"

    def build(self, parent):
        super().build(parent)
        root = self._root
        W = 480

        # ---- 状态栏 ----
        self.lbl_time = theme.label(root, "--:--", 12, 6, color=theme.TEXT, font=theme.FONT_MID)
        self.lbl_gps = theme.label(root, "GPS --", 110, 6, color=theme.MUTED, font=theme.FONT_SMALL)
        self.lbl_temp = theme.label(root, "--°C", 300, 6, color=theme.MUTED, font=theme.FONT_SMALL)
        self.lbl_volt = theme.label(root, "--.-V", 380, 6, color=theme.MUTED, font=theme.FONT_SMALL)
        theme.hline(root, 0, 28, W)

        # ---- 速度大数字 ----
        self.lbl_speed = theme.big_number(root, "--", scale=320, color=theme.ACCENT_CYAN)
        self.lbl_speed.align(lv.ALIGN.TOP_MID, 0, 60)
        self.lbl_speed_unit = theme.label(root, "km/h", 0, 0, color=theme.MUTED, font=theme.FONT_MID)
        self.lbl_speed_unit.align(lv.ALIGN.TOP_MID, 0, 168)

        # ---- RPM 数字 ----
        self.lbl_rpm = theme.label(root, "0 RPM", 0, 196, color=theme.ACCENT_ORANGE, font=theme.FONT_BODY)
        self.lbl_rpm.align(lv.ALIGN.TOP_MID, 0, 196)

        # ---- RPM 横向进度条 ----
        self.rpm_bar = lv.bar(root)
        self.rpm_bar.set_pos(40, 224)
        self.rpm_bar.set_size(400, 14)
        self.rpm_bar.set_range(0, 10000)
        self.rpm_bar.set_value(0, 0)
        self.rpm_bar.set_style_bg_color(lv.color_hex(0x1A2332), 0)
        self.rpm_bar.set_style_bg_opa(lv.OPA.COVER, 0)
        self.rpm_bar.set_style_border_width(0, 0)
        self.rpm_bar.set_style_radius(7, 0)
        self.rpm_bar.set_style_pad_all(0, 0)
        self.rpm_bar.set_style_bg_color(lv.color_hex(theme.ACCENT_ORANGE), lv.PART.INDICATOR)
        self.rpm_bar.set_style_bg_opa(lv.OPA.COVER, lv.PART.INDICATOR)
        self.rpm_bar.set_style_radius(7, lv.PART.INDICATOR)

        # ---- 卡片行：挡位 / 航向 / 倾斜 / 里程 ----
        cards = [
            ("gear", "挡位", "--"),
            ("course", "航向", "--"),
            ("tilt", "倾斜", "--"),
            ("trip", "里程", "--"),
        ]
        self.card_vals = {}
        cw = 104
        gap = 8
        total = len(cards) * cw + (len(cards) - 1) * gap
        start_x = (W - total) // 2
        for i, (key, title, val) in enumerate(cards):
            x = start_x + i * (cw + gap)
            card = theme.card(root, cw, 56, x, 256)
            theme.label(card, title, 8, 6, color=theme.MUTED, font=theme.FONT_SMALL)
            v = theme.label(card, val, 8, 24, color=theme.TEXT, font=theme.FONT_BODY)
            self.card_vals[key] = v

        return root

    def update(self):
        bus = self.bus
        self.lbl_time.set_text(bus.get("clock", "--:--"))
        fix = bus.get("gps_fix", False)
        self.lbl_gps.set_text("GPS FIX" if fix else "GPS --")
        self.lbl_gps.set_style_text_color(
            lv.color_hex(theme.ACCENT_CYAN if fix else theme.MUTED), 0
        )
        t = bus.get("temperature")
        self.lbl_temp.set_text(_fmt(t, "%.0f°C"))
        v = bus.get("voltage")
        self.lbl_volt.set_text(_fmt(v, "%.1fV"))

        spd = bus.get("speed_kmh")
        self.lbl_speed.set_text(_fmt(spd, "%d", "0"))
        rpm = bus.get("rpm")
        if rpm is None or rpm == INVALID:
            rpm = 0
        self.lbl_rpm.set_text("%d RPM" % int(rpm))
        self.rpm_bar.set_value(int(max(0, min(10000, rpm))), 0)

        self.card_vals["gear"].set_text(_fmt(bus.get("gear"), "%d", "N"))
        course = bus.get("course")
        self.card_vals["course"].set_text(_fmt(course, "%d°", "--"))
        tilt = bus.get("tilt")
        self.card_vals["tilt"].set_text(_fmt(tilt, "%d°", "--"))
        trip = bus.get("trip_km")
        self.card_vals["trip"].set_text(_fmt(trip, "%.1f", "--"))

    def on_event(self, event):
        # 主驾驶页不消费切页事件（由 ViewManager 处理）
        return False
