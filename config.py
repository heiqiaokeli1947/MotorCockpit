# MotorCockpit 唯一配置中心：引脚、参数、硬件启用开关。
# 引脚号只允许出现在本文件与 driver/bsp.py（_KB/PAT-0001）。
# 改任一引脚/参数后，先跑 tests/test_hardware.py 自检，再开 AUTO_START。

# ---------------- 总开关 ----------------
# 确认接线和手动运行稳定后，再开启自动启动。
AUTO_START = False
# 串口结构化调试日志（#DBG 前缀），发布前可关。
DEBUG_LOG = True

# ---------------- 屏幕 ST7796U 480x320 横屏（照抄已验证值，勿改） ----------------
ST7796_SCK = 18
ST7796_MOSI = 9
ST7796_MISO = 16          # 必须显式指定，避开 GPIO37 与 PSRAM 冲突（_KB/PIT-0030）
ST7796_CS = 15
ST7796_DC = 10
ST7796_RST = 11
ST7796_BL = 17            # 高电平点亮
ST7796_SPI_ID = 2
ST7796_BAUD = 60_000_000  # 实际 40MHz，勿超 61MHz（_KB/CON-0023）
ST7796_WIDTH = 320        # 控制器原生（竖向）
ST7796_HEIGHT = 480
ST7796_ROTATION = 1       # 0 竖 / 1 横屏 480x320
ST7796_MADCTL = 0x20      # 横屏列扫描方向修正
ST7796_BGR = True
ST7796_BUFFER_FACTOR = 4  # 128 行缓冲，覆盖脏区（_KB/PIT-0034）

# ---------------- 触摸 FT6336U（与传感器共用 I2C1） ----------------
TOUCH_I2C_ID = 1
TOUCH_SDA = 8
TOUCH_SCL = 3
TOUCH_ADDR = 0x38
TOUCH_INVERT_X = True    # swap 前翻转原始 x 轴（最终屏幕 Y 方向）
TOUCH_INVERT_Y = False
TOUCH_SWAP_XY = True     # 横屏 X=raw_y, Y=319-raw_x（_KB/PIT-0033）

# ---------------- I2C 传感器总线（I2C1，与触摸共用） ----------------
# 400kHz，挂 FT6336(0x38) + HDC1080(0x40) + BMP280(0x76) + ICM20948(0x68)
SENSOR_I2C_ID = 1
SENSOR_SDA = 8
SENSOR_SCL = 3
SENSOR_FREQ = 400_000
HDC1080_ADDR = 0x40
BMP280_ADDR = 0x76       # 部分模块为 0x77，按实际改
ICM20948_ADDR = 0x68     # ADO 接地 0x68 / 接高 0x69

# ---------------- 按键（6 个，低电平有效，内部上拉） ----------------
BTN_UP = 12
BTN_DOWN = 14
BTN_LEFT = 1
BTN_RIGHT = 2
BTN_OK = 13
BTN_CANCEL = 7
BTN_DEBOUNCE_MS = 25
BTN_LONG_PRESS_MS = 1000  # 长按判定阈值

# ---------------- 旋转编码器（双边沿中断，避开 33-37、39） ----------------
ENC_A = 41
ENC_B = 42
ENC_PRESS = 40           # 编码器按下（兼作 OK 快捷）
ENC_REVERSE = False

# ---------------- WS2812 灯带 ----------------
ENABLE_WS2812 = True
WS2812_PIN = 47          # 待按实际开发板核对
WS2812_COUNT = 12        # 灯珠数量，按实际改
WS2812_DEFAULT_BRIGHTNESS = 80  # 0-255

# ---------------- 串口 GPS（UART + NMEA） ----------------
ENABLE_GPS = True
GPS_UART_ID = 1
GPS_TX = 43              # ESP TX -> GPS RX
GPS_RX = 44              # GPS TX -> ESP RX
GPS_BAUD = 9600          # 常见模块默认 9600，按实际改

# ---------------- 硬件启用开关（按需初始化，避免死代码拖启动 _KB/PIT-0016） ----------------
ENABLE_HDC1080 = True
ENABLE_BMP280 = True
ENABLE_ICM20948 = True
ENABLE_TOUCH = True
ENABLE_BUTTONS = True
ENABLE_ENCODER = True

# ---------------- UI 参数 ----------------
UI_WIDTH = 480
UI_HEIGHT = 320
UI_REFRESH_MS = 100      # 数据刷新 10Hz
UI_BACKLIGHT = 100       # 默认背光 0-100

# 赛博霓虹主题配色（见 ui/theme.py）
THEME = "cyber"

# 行程统计持久化文件
TRIP_FILE = "/trip.json"

# 无效值统一约定（_KB/CON-0006）
INVALID = -9999
SENSOR_STALE_MS = 10_000  # 10 秒老化
