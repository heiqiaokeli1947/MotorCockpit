"""赛博霓虹主题：配色、字体、控件工厂（DESIGN §5）。

所有页面通过本模块创建控件，禁止散落样式，便于统一换肤。
"""
import lvgl as lv

# ---- 配色 ----
BG = 0x0A0E14
CARD = 0x111827
TEXT = 0xE6F1FF
MUTED = 0x8FA3B8
ACCENT_CYAN = 0x00E5FF
ACCENT_ORANGE = 0xFF6D00
ALARM_RED = 0xFF1744
PURPLE = 0x7C4DFF
DIVIDER = 0x1F2A3A


def _font(name, fallback=lv.font_montserrat_14):
    f = getattr(lv, name, None)
    return f if f is not None else fallback


FONT_SMALL = _font("font_montserrat_14")
FONT_MID = _font("font_song_16")
FONT_BODY = _font("font_song_20")
FONT_TITLE = _font("font_song_24")


def apply_root(root):
    """给根屏幕/容器套主题背景。"""
    root.set_style_bg_color(lv.color_hex(BG), 0)
    root.set_style_bg_opa(lv.OPA.COVER, 0)
    root.set_style_border_width(0, 0)
    root.set_style_pad_all(0, 0)
    root.remove_flag(lv.obj.FLAG.SCROLLABLE)


def card(parent, w, h, x=0, y=0):
    obj = lv.obj(parent)
    obj.set_size(w, h)
    obj.set_pos(x, y)
    obj.set_style_bg_color(lv.color_hex(CARD), 0)
    obj.set_style_bg_opa(lv.OPA.COVER, 0)
    obj.set_style_border_width(0, 0)
    obj.set_style_radius(12, 0)
    obj.set_style_pad_all(16, 0)
    obj.remove_flag(lv.obj.FLAG.SCROLLABLE)
    return obj


def label(parent, text, x=0, y=0, color=TEXT, font=FONT_BODY, align=None):
    lab = lv.label(parent)
    lab.set_text(text)
    lab.set_style_text_color(lv.color_hex(color), 0)
    lab.set_style_text_font(font, 0)
    if align is not None:
        lab.align(align, x, y)
    else:
        lab.set_pos(x, y)
    return lab


def big_number(parent, text, scale=256, color=ACCENT_CYAN):
    """大号数字：用 transform_scale 放大字体（已验证做法，见 app.py）。"""
    lab = lv.label(parent)
    lab.set_text(text)
    lab.set_style_text_color(lv.color_hex(color), 0)
    lab.set_style_text_font(FONT_TITLE, 0)
    lab.set_style_transform_scale(scale, 0)
    lab.set_style_transform_pivot_x(0, 0)
    lab.set_style_transform_pivot_y(0, 0)
    return lab


def hline(parent, x, y, w, color=DIVIDER):
    line = lv.obj(parent)
    line.set_size(w, 1)
    line.set_pos(x, y)
    line.set_style_bg_color(lv.color_hex(color), 0)
    line.set_style_bg_opa(lv.OPA.COVER, 0)
    line.set_style_border_width(0, 0)
    line.set_style_radius(0, 0)
    return line
