import time


class Buttons:
    """低电平有效按键，带消抖。poll() 返回本周期触发的按键名列表。

    支持短按（按下即触发）与长按（按住超过阈值触发一次 long_<name>）。
    """

    def __init__(self, pins, debounce_ms=25, long_press_ms=1000):
        self.debounce_ms = debounce_ms
        self.long_press_ms = long_press_ms
        self.items = {}
        for name, pin in pins.items():
            if pin is None:
                continue
            # [pin, last_raw, pressed, changed_at, long_fired]
            self.items[name] = [pin, 1, False, time.ticks_ms(), False]

    def poll(self):
        events = []
        now = time.ticks_ms()
        for name, state in self.items.items():
            value = state[0].value()
            if value != state[1]:
                state[1] = value
                state[3] = now
                continue
            if time.ticks_diff(now, state[3]) < self.debounce_ms:
                continue
            if value == 0 and not state[2]:
                state[2] = True
                state[3] = now
                state[4] = False
                events.append(name)
            elif value == 0 and state[2] and not state[4]:
                if time.ticks_diff(now, state[3]) >= self.long_press_ms:
                    state[4] = True
                    events.append("long_" + name)
            elif value == 1:
                state[2] = False
        return events
