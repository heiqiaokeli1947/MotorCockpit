"""GPS / 导航页：航向 + 速度 + 坐标 + 海拔 + 搜星。

罗盘用 lv_scale 圆形刻度待部署验证 API 后替换；M1 用大字方位 + 度数。
"""
import lvgl as lv

from ui import theme
from ui.page_base import Page

INVALID = -9999

_COMPASS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]


def _compass_text(course):
    if course is None or course == INVALID:
        return "--"
    return _COMPASS[int((course % 360) / 45) % 8]


def _fmt(val, template, invalid="--"):
    if val is None or val == INVALID:
        return invalid
    return template % val


class PageGPS(Page):
    name = "导航"

    def build(self, parent):
        super().build(parent)
        root = self._root
        W = 480

        # 状态栏
        self.lbl_time = theme.label(root, "--:--", 12, 6, font=theme.FONT_MID)
        self.lbl_gps = theme.label(root, "GPS --", 360, 6, color=theme.MUTED, font=theme.FONT_SMALL)
        theme.hline(root, 0, 28, W)

        # 中央航向大字
        self.lbl_compass = theme.big_number(root, "--", scale=300, color=theme.ACCENT_CYAN)
        self.lbl_compass.align(lv.ALIGN.TOP_MID, 0, 50)
        self.lbl_course = theme.label(root, "--°", 0, 130, color=theme.TEXT, font=theme.FONT_TITLE)
        self.lbl_course.align(lv.ALIGN.TOP_MID, 0, 130)

        # 卡片网格：速度 / 海拔 / 搜星 / 坐标
        self.lbl_speed = theme.label(root, "速度 -- km/h", 40, 180, color=theme.TEXT, font=theme.FONT_BODY)
        self.lbl_alt = theme.label(root, "海拔 -- m", 40, 212, color=theme.TEXT, font=theme.FONT_BODY)
        self.lbl_sats = theme.label(root, "搜星 --", 40, 244, color=theme.TEXT, font=theme.FONT_BODY)
        self.lbl_lat = theme.label(root, "纬 --", 260, 180, color=theme.MUTED, font=theme.FONT_BODY)
        self.lbl_lon = theme.label(root, "经 --", 260, 212, color=theme.MUTED, font=theme.FONT_BODY)
        self.lbl_fix = theme.label(root, "", 260, 244, color=theme.ACCENT_ORANGE, font=theme.FONT_SMALL)

        return root

    def update(self):
        bus = self.bus
        self.lbl_time.set_text(bus.get("clock", "--:--"))
        fix = bus.get("gps_fix", False)
        self.lbl_gps.set_text("GPS FIX" if fix else "GPS --")
        self.lbl_gps.set_style_text_color(
            lv.color_hex(theme.ACCENT_CYAN if fix else theme.MUTED), 0
        )
        course = bus.get("course")
        self.lbl_compass.set_text(_compass_text(course))
        self.lbl_course.set_text(_fmt(course, "%d°"))
        self.lbl_speed.set_text("速度 %s km/h" % _fmt(bus.get("speed_kmh"), "%.0f"))
        self.lbl_alt.set_text("海拔 %s m" % _fmt(bus.get("altitude"), "%.0f"))
        self.lbl_sats.set_text("搜星 %s" % _fmt(bus.get("sats"), "%d"))
        self.lbl_lat.set_text("纬 %s" % _fmt(bus.get("lat"), "%.4f"))
        self.lbl_lon.set_text("经 %s" % _fmt(bus.get("lon"), "%.4f"))
        self.lbl_fix.set_text("已定位" if fix else "搜星中…")
