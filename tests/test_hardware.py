"""M0 硬件综合自检。

AUTO_START=False 下，复位后在 REPL 运行：
    import tests.test_hardware as t
    t.run()              # 跑全部
    t.test_display()     # 只测显示
    t.test_buttons()     # 只测按键

每项独立 try/except，失败不影响后续。全部 PASS 后再把 config.AUTO_START 改 True。
"""
import time

import config


def _pump(ms):
    """跑 LVGL 事件循环，让 flush 把画面推出去。"""
    try:
        import lvgl as lv
    except ImportError:
        time.sleep_ms(ms)
        return
    end = time.ticks_add(time.ticks_ms(), ms)
    while time.ticks_diff(end, time.ticks_ms()) > 0:
        lv.task_handler()
        time.sleep_ms(5)


# ---------------- I2C 总线扫描 ----------------
def test_i2c_scan():
    from driver.bsp import Board

    i2c = Board.instance().sensor_i2c()
    devs = i2c.scan()
    print("I2C1 设备: %s" % [hex(d) for d in devs])
    expect = {
        config.TOUCH_ADDR: "FT6336触摸",
        config.HDC1080_ADDR: "HDC1080",
        config.BMP280_ADDR: "BMP280",
        config.ICM20948_ADDR: "ICM20948",
    }
    found = set(devs)
    ok = True
    for addr, name in sorted(expect.items()):
        present = addr in found
        print("  0x%02X %-10s %s" % (addr, name, "OK" if present else "MISSING"))
        ok = ok and present
    return ok


# ---------------- 传感器 ----------------
def test_hdc1080():
    from driver.bsp import Board
    from driver.hdc1080 import HDC1080

    s = HDC1080(Board.instance().sensor_i2c())
    t = s.temperature
    h = s.humidity
    print("HDC1080: T=%.2f°C  H=%.2f%%" % (t, h))
    return t != -9999 and h != -9999


def test_bmp280():
    from driver.bsp import Board
    from driver.bmp280 import BMP280

    s = BMP280(Board.instance().sensor_i2c())
    p = s.getPress()
    t = s.getTemp()
    print("BMP280: P=%dPa  T=%.2f°C" % (p, t))
    return p != -9999


def test_icm20948():
    from driver.bsp import Board
    from driver.icm20948 import ICM20948

    s = ICM20948(Board.instance().sensor_i2c())
    s.read()
    print(
        "ICM20948: ready=%s  ax=%.2f ay=%.2f az=%.2f  gx=%.1f gy=%.1f gz=%.1f"
        % (s.hardWareReady, s.ax, s.ay, s.az, s.gx, s.gy, s.gz)
    )
    return s.hardWareReady


# ---------------- 显示 ----------------
def test_display():
    """三原色 + 标题，确认方向与 RGB 顺序。返回 port（须保引用防 GC）。"""
    import lvgl as lv
    from driver.st7796 import St7796Port

    port = St7796Port().start()
    scr = lv.obj()
    scr.set_style_bg_color(lv.color_hex(0x0A0E14), 0)
    scr.set_style_bg_opa(lv.OPA.COVER, 0)
    scr.remove_flag(lv.obj.FLAG.SCROLLABLE)

    title = lv.label(scr)
    title.set_text("MotorCockpit ST7796 %dx%d" % (port.display.width, port.display.height))
    title.set_style_text_color(lv.color_white(), 0)
    title.align(lv.ALIGN.TOP_MID, 0, 24)

    for index, color in enumerate((0xFF0000, 0x00FF00, 0x0000FF)):
        box = lv.obj(scr)
        box.set_size(120, 90)
        box.set_pos(40 + index * 140, 140)
        box.set_style_bg_color(lv.color_hex(color), 0)
        box.set_style_bg_opa(lv.OPA.COVER, 0)
        box.set_style_border_width(0, 0)
        box.set_style_radius(0, 0)
    lv.screen_load(scr)
    _pump(2000)
    print("显示测试：请确认左红/中绿/右蓝，文字正向")
    return port


# ---------------- 触摸 ----------------
def test_touch(seconds=15):
    """打印触点坐标，确认 swap/invert 正确。"""
    from ft6x36 import ft6x36

    touch = ft6x36(
        i2c_dev=config.TOUCH_I2C_ID,
        sda=config.TOUCH_SDA,
        scl=config.TOUCH_SCL,
        addr=config.TOUCH_ADDR,
        width=config.ST7796_WIDTH,
        height=config.ST7796_HEIGHT,
        inv_x=config.TOUCH_INVERT_X,
        inv_y=config.TOUCH_INVERT_Y,
        swap_xy=config.TOUCH_SWAP_XY,
    )
    print("触摸测试：请在 %d 秒内点击屏幕四角，观察坐标是否对应" % seconds)
    end = time.ticks_add(time.ticks_ms(), seconds * 1000)
    last_x = last_y = -1
    count = 0
    while time.ticks_diff(end, time.ticks_ms()) > 0:
        _pump(20)
        if getattr(touch, "presses", 0):
            point = touch.points[0]
            if point["x"] != last_x or point["y"] != last_y:
                print("  touch x=%d y=%d" % (point["x"], point["y"]))
                last_x, last_y = point["x"], point["y"]
                count += 1
        time.sleep_ms(20)
    print("触摸测试结束，收到 %d 次触点" % count)
    return count > 0


# ---------------- 按键 ----------------
def test_buttons(seconds=12):
    from driver.bsp import Board
    from lib.buttons import Buttons

    b = Buttons(Board.instance().buttons(), config.BTN_DEBOUNCE_MS)
    names = list(b.items.keys())
    print("按键测试：%d 秒内依次按下 %s" % (seconds, "/".join(names)))
    pressed = set()
    end = time.ticks_add(time.ticks_ms(), seconds * 1000)
    while time.ticks_diff(end, time.ticks_ms()) > 0:
        for ev in b.poll():
            print("  key: %s" % ev)
            pressed.add(ev.replace("long_", ""))
        time.sleep_ms(20)
    missing = [n for n in names if n not in pressed]
    if missing:
        print("  未触发: %s" % missing)
    return not missing


# ---------------- 旋转编码器 ----------------
def test_encoder(seconds=12):
    from lib.rotary.rotary_irq_esp import RotaryIRQ

    r = RotaryIRQ(
        pin_num_clk=config.ENC_A,
        pin_num_dt=config.ENC_B,
        reverse=config.ENC_REVERSE,
        range_mode=RotaryIRQ.RANGE_UNBOUNDED,
    )
    last = r.value()
    moved = False
    print("编码器测试：%d 秒内左右旋转，观察数值变化" % seconds)
    end = time.ticks_add(time.ticks_ms(), seconds * 1000)
    while time.ticks_diff(end, time.ticks_ms()) > 0:
        v = r.value()
        if v != last:
            print("  encoder: %d" % v)
            last = v
            moved = True
        time.sleep_ms(20)
    return moved


# ---------------- WS2812 ----------------
def test_ws2812():
    from driver.ws2812 import WS2812

    led = WS2812()
    print("WS2812 测试：依次红→绿→蓝→白，各 0.6 秒")
    for c in ((255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 255)):
        led.fill(*c)
        led.show()
        time.sleep_ms(600)
    led.clear()
    led.show()
    return True


# ---------------- GPS ----------------
def test_gps(seconds=8):
    from driver.bsp import Board
    from driver.gps import GPS

    g = GPS(Board.instance().gps_uart())
    print("GPS 测试：%d 秒内读取 NMEA（无天线可能搜不到星，但应有原始数据）" % seconds)
    got = False
    end = time.ticks_add(time.ticks_ms(), seconds * 1000)
    while time.ticks_diff(end, time.ticks_ms()) > 0:
        if g.poll():
            got = True
            s = g.summary()
            print("  fix=%s sats=%s spd=%s lat=%s lon=%s" %
                  (s["fix"], s["sats"], s["speed_kmh"], s["lat"], s["lon"]))
        time.sleep_ms(200)
    return got


# ---------------- 汇总运行 ----------------
def run():
    tests = [
        ("I2C扫描", test_i2c_scan),
        ("HDC1080", test_hdc1080),
        ("BMP280", test_bmp280),
        ("ICM20948", test_icm20948),
    ]
    # 显示/触摸需要 LVGL，且 port 须保引用
    display_tests = [
        ("显示", test_display),
        ("触摸", test_touch),
    ]
    input_tests = [
        ("按键", test_buttons),
        ("编码器", test_encoder),
        ("WS2812", test_ws2812),
        ("GPS", test_gps),
    ]

    results = {}
    for name, fn in tests + input_tests:
        try:
            ok = bool(fn())
            results[name] = ok
            print(">>> %s: %s" % (name, "PASS" if ok else "FAIL"))
        except Exception as exc:
            results[name] = False
            print(">>> %s: FAIL (%r)" % (name, exc))

    port = None
    for name, fn in display_tests:
        try:
            ret = fn()
            if name == "显示":
                port = ret  # 保引用，防 GC 回收导致回调悬空
            ok = True
            results[name] = ok
            print(">>> %s: PASS" % name)
        except Exception as exc:
            results[name] = False
            print(">>> %s: FAIL (%r)" % (name, exc))

    print("\n=== 自检汇总 ===")
    all_ok = True
    for name in ["I2C扫描", "HDC1080", "BMP280", "ICM20948",
                 "显示", "触摸", "按键", "编码器", "WS2812", "GPS"]:
        ok = results.get(name, False)
        all_ok = all_ok and ok
        print("  %-8s %s" % (name, "PASS" if ok else "FAIL"))
    print("\n全部通过后，把 config.py 的 AUTO_START 改为 True 再启动 UI。")
    return all_ok


if __name__ == "__main__":
    run()
