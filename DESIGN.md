# MotorCockpit 摩托车仪表盘 · 设计文档

> 状态：方案已与用户交互确认，进入实施。
> 平台：ESP32-S3（N16R8，Octal PSRAM）+ MicroPython v1.29.0 + LVGL 9.3.0
> 屏幕：ST7796U 480×320 横屏 + FT6336U 电容触摸
> 传感器：HDC1080（温湿度）、BMP280（气压）、ICM20948（9 轴姿态）、WS2812（灯带）、串口 GPS
> 输入：电容触摸 + 旋转编码器 + 6 按键（上下左右 / 确认 / 取消）

---

## 1. 项目目标

为摩托车打造一块基于 LVGL 的炫酷全液晶仪表盘，要求：

- 视觉炫酷（赛博霓虹风），夜间骑行可读；
- 信息分层清晰，骑行核心信息一屏直达；
- 软件架构可灵活扩展，后续增加硬件/页面只需增量添加，不改动既有代码；
- 输入同时支持触摸、旋转编码器、物理按键，三者统一抽象、可互换。

---

## 2. 复用基线（全部来自已硬件验证的知识库）

本项目不是从零起步，硬件组合与已验证项目 `CustomMicropython` 高度重合。

| 资产 | 来源 | 验证状态 |
|---|---|---|
| 固件：MicroPython v1.29.0 + LVGL 9.3.0 + ESP-IDF 5.5.6，16MiB 双 5MiB OTA | `_KB/REC-0011` | 硬件已验证 |
| ST7796 480×320 横屏显示参数与驱动 | `_KB/REC-0012`、`CustomMicropython/device/driver/st7796.py` | 硬件已验证 |
| FT6336U 触摸坐标映射 | `_KB/PIT-0033` | 硬件已验证 |
| 中文字体 `song_16/20/24`（思源宋体 GB2312，已冻结） | DEVELOPMENT_GUIDE §8.10 | 硬件已验证 |
| 三层架构 driver/domain/ui + Port 抽象 + 心跳线程 | `_KB/PAT-0001`、`CustomMicropython/device/ui/app.py` | 硬件已验证 |
| 按键库 `lib/buttons.py` | `CustomMicropython/device/lib/buttons.py` | 硬件已验证 |
| 旋转编码器 `lib/rotary/`（双边沿中断） | `_KB/REC-0006`、`ReadingLampController4ESP32S3/lib/rotary/` | 硬件已验证 |
| HDC1080 / BMP280 驱动 | `_KB/REC-0005`、`Aotomizer4ESP32S3/driver/` | 硬件已验证 |

**新增硬件（实施时先逐个自检，未验证前标 code-only）**：

| 硬件 | 方案 | 来源 |
|---|---|---|
| ICM20948 | 移植 `jposada202020/MicroPython_ICM20948`，I2C 地址 0x68/0x69 | GitHub（待硬件验证） |
| WS2812 | 内置 `neopixel` 模块，底层 RMT `machine.bitstream` | MicroPython 官方文档（待硬件验证） |
| 串口 GPS | UART + NMEA 解析（RMC/GGA），注意 `UART.read()` 可能返回 None | `_KB/PIT-0009`（待硬件验证） |

---

## 3. 硬件清单与引脚分配

### 3.1 已验证引脚（直接复用，减少接线改动）

| 信号 | GPIO | 说明 |
|---|---|---|
| ST7796 SCK / MOSI / MISO | 18 / 9 / 16 | SPI2，MISO 必须显式指定（避开 GPIO37 PSRAM 冲突） |
| ST7796 CS / DC / RST / BL | 15 / 10 / 11 / 17 | BL 高电平点亮 |
| FT6336 + HDC1080 + BMP280 + ICM20948 | SDA=8 / SCL=3 | 共用 I2C1（400kHz），地址 0x38 / 0x40 / 0x76 / 0x68 互不冲突 |
| 按键 up / down / ok | 12 / 14 / 13 | 低电平有效，内部上拉 |

### 3.2 新增硬件建议引脚（实施前按开发板物理位置核对）

核对依据：`_KB/TOOL-0002` 引脚表。必须避开：
- Strapping 引脚：GPIO0 / 3 / 45 / 46（`_KB/CON-0009`）；
- Octal PSRAM：GPIO33–37（`_KB/PIT-0030`）；
- 旋转编码器黑名单：GPIO33–37、39（`_KB/CON-0012`、`_KB/CON-0022`）。

| 信号 | 建议 GPIO | 说明 |
|---|---|---|
| 按键 left / right / cancel | 1 / 2 / 7 | 低电平有效 + 内部上拉 |
| 旋转编码器 A / B / 按键 | 41 / 42 / 40 | 双边沿中断；避开 33–37、39 |
| WS2812 DIN | 47（待核） | 单 GPIO，RMT 驱动 |
| GPS RX（模块 TX→ESP） / TX（ESP→模块 RX） | UART1 空闲引脚 | 波特率默认 9600，config 可调 |

> 引脚号唯一允许出现在 `config.py` 与 `driver/bsp.py`（`_KB/PAT-0001`）。本项目为单屏，不保留副屏 OLED，原 OLED 的 I2C0（GPIO4/5）释放备用。

### 3.3 I2C 总线约束

- I2C1 挂 4 个设备（触摸 + 3 个传感器），总线长度 ≤1.5m，使用 2.2k 上拉（`_KB/CON-0005`）。
- 传感器异常时驱动层吞掉异常、返回无效值 -9999 并老化，不上抛到框架（`_KB/PAT-0013`、`_KB/CON-0006`）。

---

## 4. 固件与显示配置（直接照抄已验证值）

| 参数 | 值 | 来源 |
|---|---|---|
| 颜色格式 | `lv.COLOR_FORMAT.RGB565_SWAPPED` 配 `BGR=True` | `_KB/PIT-0032` |
| SPI 波特率 | `60_000_000`（实际 40MHz，勿超 61MHz） | `_KB/CON-0023` |
| 旋转 | `ROTATION=1`，`MADCTL=0x20` | `_KB/REC-0012` |
| 缓冲因子 | `BUFFER_FACTOR=4`（128 行，须覆盖脏区域） | `_KB/PIT-0034` |
| 触摸映射 | `SWAP_XY=True`，`INVERT_X=True`，`INVERT_Y=False`，X=raw_y，Y=319-raw_x | `_KB/PIT-0033` |
| Flash / 分区 | 16MiB，双 5MiB OTA 槽 + VFS | `_KB/CON-0017` |
| 启动开关 | `AUTO_START = False` 默认，自检通过再开 | `_KB/REC-0012` |

---

## 5. 视觉设计规范（赛博霓虹风）

### 5.1 配色

| 角色 | 色值 | 用途 |
|---|---|---|
| BG 背景 | `#0A0E14` | 全局深色底，夜间不刺眼 |
| CARD 卡片 | `#111827` | 信息卡片底，圆角 12 |
| TEXT 主文字 | `#E6F1FF` | 数值、标题 |
| MUTED 次要文字 | `#8FA3B8` | 标签、单位、状态 |
| ACCENT_CYAN 青 | `#00E5FF` | 主强调色（速度、激活态） |
| ACCENT_ORANGE 橙 | `#FF6D00` | 次要强调（转速、航向） |
| ALARM_RED 红 | `#FF1744` | 告警、异常 |
| PURPLE 紫 | `#7C4DFF` | 姿态、装饰 |

### 5.2 字体

固件已冻结：`song_16` / `song_20` / `song_24`（中文）、`montserrat_14` / `montserrat_16`（数字/英文）。

- 超大速度数字：`song_24` 基础上 `transform_scale` 放大（参考 `app.py` 的 `_big_label` 做法）。
- 所有文字用统一主题函数创建，禁止页面内散落样式。

### 5.3 布局栅格（480×320）

- 顶部状态栏：高 28px，全宽。
- 主内容区：y=28 ~ y=300。
- 页面指示条：底部高 20px（●○○○○ 当前页高亮）。
- 卡片内边距 16px，圆角 12px，卡片间距 16px。

### 5.4 动画

- 指针表数值变化用 `lv_anim` 平滑过渡（200–300ms），避免生硬跳变。
- 页面切换用淡入淡出（`lv_screen_load_anim`），不做复杂位移（性能优先）。
- 告警文字 0.5s 黑白反显闪烁（复用 `app.py` 已有模式）。
- WS2812 转向 1Hz 闪烁，转速跟随颜色渐变。

---

## 6. 页面设计（5 页）

页面切换：触摸左右滑动 / 编码器旋转 / 左右按键。当前页在底部指示条高亮。

### 6.1 主驾驶页（默认，骑行核心）

```
┌───────────────────────────────────────────────────┐
│ 12:34   🛰️FIX   🌡24°C   ⚡12.8V      页面 ●○○○○ │ ← 状态栏
├───────────────────────────────────────────────────┤
│                                                   │
│            ┌──────────┐                           │
│            │    86    │  ← 超大速度（青）          │
│            │   km/h   │                           │
│            └──────────┘                           │
│     ╭───────────────────────────────╮             │
│     │  ▔▔▔▔▔▔ RPM 弧/指针 0~10000   │ ← lv_scale │
│     ╰───────────────────────────────╯             │
│   [挡 3]  [NE ↑]  [倾斜 0°]  [里程 12.3km]       │ ← 卡片行
└───────────────────────────────────────────────────┘
```

### 6.2 GPS / 导航页

- 中央航向罗盘（`lv_scale` 圆形刻度 + 指北指针，数据 = ICM20948 磁力计或 GPS 航向）。
- 卡片：速度、经纬度、海拔、搜星数、行程时间。
- 无信号：显示"搜星中…"，罗盘静止指北。

### 6.3 环境 / 姿态页

- 左：温度 / 湿度 / 气压 数值 + `lv_chart` 趋势小图。
- 右：姿态水平仪（ICM20948 解算俯仰/横滚，自定义绘制）+ 实时 G 值。
- 底部：WS2812 当前效果预览。

### 6.4 行程统计页（用户新增）

- 本次行程：里程、时长、平均速度、最高速度、起止时间。
- 累计：总里程、总时长（持久化到 flash）。
- 长按"取消"清零本次行程（需二次确认）。

### 6.5 设置页

列表菜单，复用 `app.py` 菜单交互（上下选择 / OK 进入编辑 / 取消返回），同时支持触摸点击：

- 背光亮度、自动亮度开关
- 单位（km/h ↔ mph、℃ ↔ ℉）
- WS2812：效果（关闭 / 氛围常亮 / 转速跟随 / 转向）、氛围颜色、亮度
- 传感器校准（ICM20948 磁力计校准触发）
- 关于（固件版本、硬件列表）

---

## 7. 软件架构（可扩展设计）

在已验证的 `CustomMicropython` 三层骨架上泛化，核心是三个解耦层：**数据总线、输入抽象、页面系统**。

### 7.1 目录结构

```
MotorCockpit/
├── boot.py                 # 启动入口（AUTO_START 开关，异常保留 REPL）
├── config.py               # 唯一引脚/参数/硬件启用开关集中地
├── DESIGN.md               # 本文档
├── driver/
│   ├── __init__.py
│   ├── bsp.py              # 板级：I2C/SPI/UART 总线 + 按键/编码器引脚，单例
│   ├── st7796.py           # 显示 Port（复用 CustomMicropython）
│   ├── ft6x36.py           # 触摸（固件已冻结，可直接 import）
│   ├── hdc1080.py          # 复用
│   ├── bmp280.py           # 从 Aotomizer 迁移
│   ├── icm20948.py         # 移植（新增）
│   ├── ws2812.py           # 封装 neopixel（新增）
│   ├── gps.py              # UART + NMEA 解析（新增）
│   └── input/
│       ├── buttons.py      # 复用（6 键）
│       └── rotary.py       # 复用 lib/rotary/
├── domain/
│   ├── __init__.py
│   ├── databus.py          # 【核心】数据总线：发布/订阅 + 老化
│   ├── input_manager.py    # 【核心】输入统一：触摸/编码器/按键 → 标准事件
│   ├── settings.py         # 配置持久化（复用现有思路）
│   ├── history.py          # 环形缓冲（泛化自 history_t/h）
│   └── trip.py             # 行程统计 + 持久化
├── ui/
│   ├── __init__.py
│   ├── theme.py            # 赛博霓虹配色/字体/控件工厂
│   ├── page_base.py        # 【核心】Page 基类
│   ├── view_manager.py     # 【核心】页面注册/切换
│   ├── widgets/            # 可复用炫酷控件
│   │   ├── gauge.py        # 指针表（lv_scale + needle + 动画）
│   │   ├── arc_meter.py    # 圆弧进度
│   │   ├── compass.py      # 航向罗盘
│   │   └── attitude.py     # 姿态水平仪
│   └── pages/
│       ├── page_dash.py    # 主驾驶
│       ├── page_gps.py     # GPS
│       ├── page_env.py     # 环境姿态
│       ├── page_trip.py    # 行程统计
│       └── page_settings.py# 设置
└── tests/                  # M0 硬件逐个自检脚本（不进固件，仅开发用）
```

### 7.2 数据流：DataBus（数据总线）

```
driver/hdc1080 ─┐
driver/bmp280  ─┤
driver/icm20948 ┼─ publish(key, value, ts) ─→ DataBus ─→ 各 Page 订阅读取
driver/gps      ┤                                │
driver/ws2812  ─┘                                └─ 无效值 -9999 + 10s 老化标记
```

- 每个传感器驱动按自己的周期采样，向 `DataBus` 发布最新值；
- `DataBus` 统一管理老化（超过 10s 未更新标记为失效，`_KB/CON-0006`）；
- UI 页面只从 `DataBus` 读，不直接碰硬件 → **新增硬件 = 加一个发布者，UI 零改动**；
- 异常在驱动层捕获，发布无效值，不上抛（`_KB/PAT-0013`）。

### 7.3 输入流：InputManager（输入抽象）

```
触摸 (FT6336) ─┐
编码器 (rotary) ┼─→ InputManager ─→ 标准事件总线 ─→ 当前 Page.on_event()
按键 (buttons)─┘     KEY_UP/DOWN/LEFT/RIGHT/OK/CANCEL
                     ENC_CW / ENC_CCW / ENC_PRESS
                     TOUCH 坐标
```

- 页面只认标准事件，不关心输入来源 → 触摸/编码器/按键可互换；
- 编码器旋转 = `ENC_CW/ENC_CCW`，主界面映射为切页，设置页映射为改数值；
- 编码器按下 = `ENC_PRESS`，映射为 `OK`；
- 长按事件（>1s）由 InputManager 识别，用于"清零行程"等。

### 7.4 页面系统：Page 基类 + ViewManager

```python
class Page:
    def build(self, parent): ...     # 创建 LVGL 控件
    def update(self): ...            # 每帧/定时从 DataBus 刷新数据
    def on_event(self, event): ...   # 处理标准输入事件
    def destroy(self): ...           # 释放资源（切页时防 GC 残留）
```

- 新增页面 = 写一个类继承 `Page` + 在 `ViewManager` 注册，不改其他页面；
- 切换时旧页 `destroy()`、新页 `build()`，过渡用淡入淡出动画；
- `ViewManager` 维护页面栈与当前索引，底部指示条由它驱动。

### 7.5 硬件按需初始化（避免死代码拖慢启动）

`config.py` 声明每个硬件的 `ENABLE_XXX` 开关，`bsp.py` 按需实例化。未启用的驱动不 import、不创建对象（`_KB/PIT-0016`：死传感器驱动顶层导入拖慢启动）。

---

## 8. 主循环与刷新策略

- `main.py` 启动装配：硬件 → DataBus → InputManager → ViewManager → 启动主循环。
- UI 数据刷新 10Hz（100ms），传感器按各自周期（GPS 1Hz、姿态 50Hz 降采样到 10Hz 发布、温湿度气压 1Hz）。
- LVGL `timer_handler` 由主循环驱动；保留独立心跳线程（16KiB 栈，`_KB/PIT-0025`）检测调度停摆（`_KB/PIT-0024`）。
- `port` / `view` / `databus` / `input_manager` 必须持有引用防 GC（`_KB/PIT-0031`）。
- 定时器回调内不做阻塞操作（`_KB/CON-0019`）。

---

## 9. 已验证约束与避坑清单（实施时逐条遵守）

| ID | 约束 | 本项目落点 |
|---|---|---|
| CON-0006 | 传感器无效值 -9999，10s 老化 | DataBus 统一处理 |
| CON-0007 | 看门狗主循环活性检测 30s | 主循环喂狗 |
| CON-0012/22 | 编码器避开 GPIO33–37、39 | 引脚分配已避开 |
| CON-0016/17 | LVGL 须自编译固件 + 16MiB 双 OTA | 复用已有固件，不重编 |
| CON-0019 | 定时器回调禁阻塞 | 耗时动作交主循环 |
| CON-0023 | SPI2 整数分频，勿超 61MHz | ST7796_BAUD=60M |
| PAT-0001 | 三层架构，引脚只在 bsp/config | 目录结构遵守 |
| PAT-0013 | 硬件异常驱动层隔离 | 各 driver try/except |
| PIT-0009 | UART.read() 可能 None | gps.py 判空 |
| PIT-0016 | 死驱动顶层导入拖启动 | 按需 import |
| PIT-0024 | LVGL event_loop scheduled 不归还 → UI 停摆 | 心跳线程检测，异常复位 |
| PIT-0025 | 后台线程栈 4KiB 溢出 | 心跳线程 16KiB |
| PIT-0030 | SPI2 默认 MISO=37 与 PSRAM 冲突 | 显式 miso=16 |
| PIT-0031 | 双 display / GC 回收回调 → IllegalInstruction | 单屏 + 保引用 |
| PIT-0032 | ST77xx 颜色先验通路再调镜像 | 照抄已验证参数 |
| PIT-0033 | ft6x36 坐标映射 | 照抄已验证参数 |
| PIT-0034 | PARTIAL 缓冲高度覆盖脏区 | BUFFER_FACTOR=4 |

---

## 10. 实施里程碑（每步硬件验证后再推进）

1. **M0 硬件逐个自检**：在 `tests/` 下写自检脚本，分别点亮显示/触摸/每个传感器/编码器/按键/WS2812/GPS。全部通过才进下一步。AUTO_START 保持 False。
2. **M1 架构骨架 + 主驾驶页**：DataBus / InputManager / Page 基类 / ViewManager / theme 搭好；主驾驶页速度表 + RPM 弧跑通（数据先用模拟发布者）。
3. **M2 真实数据 + GPS/环境页**：传感器接入 DataBus；完成 GPS 页、环境姿态页。
4. **M3 行程统计页 + 设置页 + WS2812 效果 + 输入全链路联调**。
5. **M4 整机联调、续航/稳定性测试、踩坑回写 `_KB`**（按 `_KB/SKILL.md` 规程：kb.py new → index → lint）。

---

## 11. 待硬件验证事项（实施前/中确认）

- [ ] 实际开发板可用引脚与 §3.2 建议是否一致（核对 `_KB/TOOL-0002`）。
- [ ] GPS 模块具体型号与默认波特率（影响 `gps.py` 初始化）。
- [ ] WS2812 灯珠数量与 Din 引脚实际接线。
- [ ] ICM20948 模块地址是 0x68 还是 0x69（ADO 引脚电平）。
- [ ] 摩托车转速信号来源（本方案 RPM 暂用模拟/预留，若后续接点火信号需新增 driver）。
- [ ] 是否需要记录行程轨迹到 SD 卡（行程统计页默认存 flash，SD 可选）。
