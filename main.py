# main.py — 应用入口。
# AUTO_START=True 时由 boot.py 调用 run()；手动运行：from main import run; run()
import gc
import math
import time

import config

# 全局保引用：防 GC 回收导致 LVGL 回调悬空（_KB/PIT-0031）
_app = None


class _App:
    """轻量容器，供 Page / ViewManager 访问共享服务。"""

    def __init__(self, bus, settings, inp):
        self.bus = bus
        self.settings = settings
        self.input = inp
        self.view = None
        self.cycles = 0
        self.port = None
        self.vm = None
        self.sim_timer = None


class _Simulator:
    """M1 模拟数据源：没接硬件时让 UI 动起来，验证架构与布局。
    M2 接入真实传感器后停用。"""

    def __init__(self, bus):
        self.bus = bus
        self.t = 0
        self.trip = 0.0

    def tick(self):
        self.t += 1
        bus = self.bus
        speed = max(0, 60 + 55 * math.sin(self.t * 0.05))
        rpm = max(0, min(10000, speed * 95 + 800 * math.sin(self.t * 0.2)))
        gear = max(1, min(6, int(speed / 22) + 1))
        course = (self.t * 2) % 360
        tilt = 5 * math.sin(self.t * 0.1)
        self.trip += speed / 3600.0 * 0.2  # 每 tick 0.2s
        bus.publish("speed_kmh", round(speed))
        bus.publish("rpm", int(rpm))
        bus.publish("gear", gear)
        bus.publish("course", int(course))
        bus.publish("tilt", round(tilt))
        bus.publish("trip_km", round(self.trip, 1))
        bus.publish("temperature", 24.5)
        bus.publish("voltage", 12.8)
        bus.publish("gps_fix", True)
        # GPS 模拟
        bus.publish("lat", round(39.9042 + 0.001 * math.sin(self.t * 0.02), 6))
        bus.publish("lon", round(116.4074 + 0.001 * math.cos(self.t * 0.02), 6))
        bus.publish("altitude", round(50 + 5 * math.sin(self.t * 0.03), 1))
        bus.publish("sats", 8)
        # 环境/姿态模拟
        bus.publish("humidity", round(45 + 5 * math.sin(self.t * 0.05), 1))
        bus.publish("pressure", 101325)
        bus.publish("accel_x", round(0.1 * math.sin(self.t * 0.1), 3))
        bus.publish("accel_y", round(0.1 * math.cos(self.t * 0.1), 3))
        bus.publish("accel_z", round(1.0 + 0.05 * math.sin(self.t * 0.08), 3))
        bus.publish("pitch", round(3 * math.sin(self.t * 0.06), 1))
        bus.publish("roll", round(tilt, 1))
        # 行程统计模拟
        bus.publish("trip_time_s", int(self.t * 0.2))
        bus.publish("avg_speed", round(speed * 0.9, 1))
        bus.publish("max_speed", 115)
        bus.publish("total_km", round(1234.5 + self.trip, 1))
        bus.publish("total_time_s", 3600 * 52 + 1234)
        try:
            rtc = time.localtime()
            bus.publish("clock", "%02d:%02d" % (rtc[3], rtc[4]))
        except Exception:
            bus.publish("clock", "--:--")


def _build_input():
    try:
        from driver.bsp import Board
        from lib.buttons import Buttons
        from domain.input_manager import InputManager

        buttons = None
        if config.ENABLE_BUTTONS:
            buttons = Buttons(
                Board.instance().buttons(),
                config.BTN_DEBOUNCE_MS,
                config.BTN_LONG_PRESS_MS,
            )
        rotary = None
        if config.ENABLE_ENCODER:
            from lib.rotary.rotary_irq_esp import RotaryIRQ

            rotary = RotaryIRQ(
                pin_num_clk=config.ENC_A,
                pin_num_dt=config.ENC_B,
                reverse=config.ENC_REVERSE,
            )
        if buttons is None and rotary is None:
            return None
        return InputManager(buttons, rotary)
    except Exception as exc:
        print("输入初始化失败，降级为无输入：%r" % (exc,))
        return None


def _start_heartbeat(app):
    """独立心跳线程，检测 LVGL 调度停摆（_KB/PIT-0024）。栈 16KiB（_KB/PIT-0025）。"""
    try:
        import _thread

        def _heartbeat():
            last = -1
            stalled = 0
            while True:
                time.sleep(5)
                cycles = app.cycles
                print("#DBG ev=hb cycles=%d heap=%d" % (cycles, gc.mem_free()))
                if cycles == last:
                    stalled += 1
                else:
                    stalled = 0
                last = cycles
                if stalled >= 2:
                    print("#DBG ev=loop_stalled cycles=%d" % cycles)

        _thread.stack_size(16384)
        _thread.start_new_thread(_heartbeat, ())
    except Exception as exc:
        print("心跳线程启动失败：%r" % (exc,))


def run():
    global _app
    import lvgl as lv

    from driver.st7796 import St7796Port
    from domain.databus import DataBus
    from domain.settings import Settings
    from ui.view_manager import ViewManager
    from ui.pages.page_dash import PageDash
    from ui.pages.page_gps import PageGPS
    from ui.pages.page_env import PageEnv
    from ui.pages.page_trip import PageTrip
    from ui.pages.page_settings import PageSettings

    # 1. 显示
    port = St7796Port().start()

    # 2. 数据层
    bus = DataBus.instance()
    settings = Settings.instance()

    # 3. 输入
    inp = _build_input()

    # 4. 视图
    app = _App(bus, settings, inp)
    vm = ViewManager(app)
    app.view = vm
    for p in (PageDash(app), PageGPS(app), PageEnv(app), PageTrip(app), PageSettings(app)):
        vm.register(p)
    vm.start()

    # 5. 模拟数据源（M1）
    sim = _Simulator(bus)
    sim_timer = lv.timer_create(lambda t: sim.tick(), 200, None)

    # 6. 心跳
    _start_heartbeat(app)

    # 保引用，防 GC
    app.port = port
    app.vm = vm
    app.sim_timer = sim_timer
    _app = app

    print("MotorCockpit M1 已启动（模拟数据）。heap=%d" % gc.mem_free())
    while True:
        lv.task_handler()
        app.cycles += 1
        if inp is not None:
            for ev in inp.poll():
                vm.dispatch(ev)
        vm.update()
        time.sleep_ms(5)


if __name__ == "__main__":
    run()
