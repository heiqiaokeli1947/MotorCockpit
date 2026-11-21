"""行程统计页：本次行程 + 累计数据。

数据由 domain/trip 发布到 DataBus（M3 实现持久化）；M1 先读 bus 演示布局。
"""
import lvgl as lv

from ui import theme
from ui.page_base import Page

INVALID = -9999


def _fmt(val, template, invalid="--"):
    if val is None or val == INVALID:
        return invalid
    return template % val


def _fmt_duration(seconds):
    if seconds is None or seconds == INVALID or seconds < 0:
        return "--:--"
    h = seconds // 3600
    m = (seconds % 3600) // 60
    return "%d:%02d" % (h, m)


class PageTrip(Page):
    name = "行程"

    def build(self, parent):
        super().build(parent)
        root = self._root
        W = 480

        theme.label(root, "行程统计", 12, 6, color=theme.TEXT, font=theme.FONT_BODY)
        theme.hline(root, 0, 28, W)

        # 本次行程
        card1 = theme.card(root, W - 48, 110, 24, 44)
        theme.label(card1, "本次行程", 0, 0, color=theme.ACCENT_CYAN, font=theme.FONT_BODY)
        self.lbl_t_km = theme.label(card1, "里程 -- km", 0, 28, font=theme.FONT_BODY)
        self.lbl_t_time = theme.label(card1, "时长 --:--", 0, 56, font=theme.FONT_BODY)
        self.lbl_t_avg = theme.label(card1, "均速 -- km/h", 200, 28, font=theme.FONT_BODY)
        self.lbl_t_max = theme.label(card1, "极速 -- km/h", 200, 56, color=theme.ACCENT_ORANGE, font=theme.FONT_BODY)

        # 累计
        card2 = theme.card(root, W - 48, 70, 24, 170)
        theme.label(card2, "累计", 0, 0, color=theme.MUTED, font=theme.FONT_MID)
        self.lbl_total_km = theme.label(card2, "总里程 -- km", 0, 26, color=theme.TEXT, font=theme.FONT_BODY)
        self.lbl_total_time = theme.label(card2, "总时长 --:--", 200, 26, color=theme.TEXT, font=theme.FONT_BODY)

        theme.label(root, "长按 [取消] 清零本次行程（M3）", 24, 270,
                    color=theme.MUTED, font=theme.FONT_SMALL)
        return root

    def update(self):
        bus = self.bus
        self.lbl_t_km.set_text("里程 %s km" % _fmt(bus.get("trip_km"), "%.1f"))
        self.lbl_t_time.set_text("时长 %s" % _fmt_duration(bus.get("trip_time_s")))
        self.lbl_t_avg.set_text("均速 %s km/h" % _fmt(bus.get("avg_speed"), "%.0f"))
        self.lbl_t_max.set_text("极速 %s km/h" % _fmt(bus.get("max_speed"), "%.0f"))
        self.lbl_total_km.set_text("总里程 %s km" % _fmt(bus.get("total_km"), "%.1f"))
        self.lbl_total_time.set_text("总时长 %s" % _fmt_duration(bus.get("total_time_s")))
