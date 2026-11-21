"""ST7796S/U 480x320 SPI 显示驱动与 LVGL 端口。

固件把 st77xx 冻结进了 flash，模块级数据位于只读区，不能改写。
这里只继承它的 SPI 收发与旋转逻辑，自己覆盖寻址窗口并接管 LVGL 显示驱动。
"""

import machine
import struct

import lvgl as lv
from lv_utils import event_loop
from st77xx import (
    ST77XX_CASET,
    ST77XX_COLMOD,
    ST77XX_COLOR_MODE_16BIT,
    ST77XX_COLOR_MODE_65K,
    ST77XX_DISPON,
    ST77XX_INVOFF,
    ST77XX_INVON,
    ST77XX_MADCTL,
    ST77XX_MADCTL_BGR,
    ST77XX_MADCTL_ROTS,
    ST77XX_NORON,
    ST77XX_RASET,
    ST77XX_SLPOUT,
    ST77XX_SWRESET,
    St77xx_hw,
)

import config

API_VERSION = 1

# 命令集切换（0xF0）必须成对：0xC3/0x96 进入厂商命令区，0x3C/0x69 退出。
_INIT = (
    (ST77XX_SWRESET, None, 120),
    (ST77XX_SLPOUT, None, 120),
    (ST77XX_COLMOD, bytes([ST77XX_COLOR_MODE_65K | ST77XX_COLOR_MODE_16BIT])),
    (0xF0, b"\xC3"),
    (0xF0, b"\x96"),
    (0xB4, b"\x01"),
    (0xB7, b"\xC6"),
    (0xB9, b"\x02\xE0"),
    (0xC0, b"\x80\x16"),
    (0xC1, b"\x15"),
    (0xC2, b"\xA7"),
    (0xC5, b"\x23"),
    (0xE8, b"\x40\x8A\x00\x00\x29\x19\xA5\x33"),
    (0xE0, b"\xF0\x09\x0B\x06\x04\x15\x2F\x54\x42\x3C\x17\x14\x18\x1B"),
    (0xE1, b"\xE0\x09\x0B\x06\x04\x03\x2B\x43\x42\x3B\x16\x14\x17\x1B"),
    (0xF0, b"\x3C"),
    (0xF0, b"\x69"),
    # 命令集切换后控制器可能把像素格式重置为 18bit，必须在退出扩展区后
    # 重新确认 RGB565，否则 16 位数据会被按 3 字节一像素切开而偏色。
    (ST77XX_COLMOD, bytes([ST77XX_COLOR_MODE_65K | ST77XX_COLOR_MODE_16BIT])),
    # 该模组为 IPS 面板，默认极性相反，必须开反色，否则黑变白、红变黄。
    (ST77XX_INVON, None),
    (ST77XX_NORON, None, 10),
    (ST77XX_DISPON, None, 120),
)


class St7796_hw(St77xx_hw):
    """ST7796S/U 的底层控制器驱动。"""

    def __init__(self, res=(320, 480), **kw):
        super().__init__(
            res=res, suppRes=[(320, 480)], model=None, suppModel=None, **kw
        )

    def config_hw(self):
        self._run_seq(_INIT)

    def set_window(self, x, y, w, h):
        """ST7796 显存从 (0,0) 开始，不需要 st77xx 的型号偏移表。"""
        struct.pack_into(
            ">HH", self.buf4, 0, self.start_x + x, self.start_x + x + w - 1
        )
        self.write_register(ST77XX_CASET, self.buf4)
        struct.pack_into(
            ">HH", self.buf4, 0, self.start_y + y, self.start_y + y + h - 1
        )
        self.write_register(ST77XX_RASET, self.buf4)

    def apply_rotation(self, rot):
        """该模组横屏时列扫描方向与标准表相反，允许用配置直接指定 MADCTL。"""
        self.rot = rot
        if (self.rot % 2) == 0:
            self.width, self.height = self.res
        else:
            self.height, self.width = self.res
        value = getattr(config, "ST7796_MADCTL", None)
        if value is None:
            value = ST77XX_MADCTL_ROTS[self.rot % 4]
        if self.bgr:
            value |= ST77XX_MADCTL_BGR
        self.write_register(ST77XX_MADCTL, bytes([value]))


class St7796Port:
    """建 SPI 总线、初始化控制器并挂上 LVGL 显示。"""

    api_version = API_VERSION

    def __init__(self):
        self.spi = None
        self.display = None
        self.disp = None
        self.frame = None
        self.event_loop = None

    def start(self):
        if self.disp is not None:
            return self
        # ESP32-S3 的 SPI2 默认 MISO 是 GPIO37，而 N16R8 的 Octal PSRAM
        # 占用 GPIO33-37。省略 miso 时驱动会保留默认值，初始化即与 PSRAM
        # 抢总线并触发看门狗复位。即使不接 SD 卡，也必须显式给一个空闲引脚。
        self.spi = machine.SPI(
            config.ST7796_SPI_ID,
            baudrate=config.ST7796_BAUD,
            polarity=0,
            phase=0,
            sck=machine.Pin(config.ST7796_SCK),
            mosi=machine.Pin(config.ST7796_MOSI),
            miso=machine.Pin(config.ST7796_MISO),
        )
        self.display = St7796_hw(
            res=(config.ST7796_WIDTH, config.ST7796_HEIGHT),
            rot=config.ST7796_ROTATION,
            spi=self.spi,
            cs=config.ST7796_CS,
            dc=config.ST7796_DC,
            rst=config.ST7796_RST,
            bl=config.ST7796_BL,
            bgr=config.ST7796_BGR,
        )
        self.display.set_backlight(100)

        if not lv.is_initialized():
            lv.init()
        width = self.display.width
        height = self.display.height
        # PARTIAL 模式：LVGL 只渲染脏区域，flush 只发送变化部分。
        # 缓冲区高度必须覆盖常见脏区域，否则一个脏矩形会被切成多次 flush，
        # 块与块之间屏幕扫描已推进，表现为横向撕裂。128 行可覆盖移动方块
        # 新旧位置的并集（约 107 行），单次写入约 3 ms，远小于 16.7 ms 扫描周期。
        self.frame = bytearray(width * 128 * 2)
        self.disp = lv.display_create(width, height)
        # ST7796 按大端解析 SPI 上的 RGB565，而 LVGL 的 RGB565 是小端存储，
        # 必须用 _SWAPPED 变体让 LVGL 在渲染阶段完成字节交换。
        self.disp.set_color_format(lv.COLOR_FORMAT.RGB565_SWAPPED)
        self.disp.set_buffers(
            self.frame, None, len(self.frame), lv.DISPLAY_RENDER_MODE.PARTIAL
        )
        self.disp.set_flush_cb(self._flush)
        self.event_loop = event_loop.current_instance() or event_loop()

        print("ST7796 已启动：%dx%d 旋转=%d" % (width, height, config.ST7796_ROTATION))
        return self

    def _flush(self, disp, area, color):
        width = area.x2 - area.x1 + 1
        height = area.y2 - area.y1 + 1
        size = width * height
        view = color.__dereference__(size * 2)
        # 字节交换已在 LVGL 渲染阶段由 RGB565_SWAPPED 完成，此处直接透传。
        # 若再交换一次，绿 0x07E0 会变成 0xE007（红+蓝=洋红）。
        self.display.blit(area.x1, area.y1, width, height, view)
        disp.flush_ready()

    def restore_spi(self):
        """SD 卡会改写共享总线的波特率，读写结束后恢复显示速率。"""
        self.spi.init(baudrate=config.ST7796_BAUD, polarity=0, phase=0)
