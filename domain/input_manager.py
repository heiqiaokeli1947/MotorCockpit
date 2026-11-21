"""输入管理器：把触摸/编码器/按键统一成标准事件。

标准事件：
  up / down / left / right / ok / cancel        短按
  long_up / long_down / ...                      长按（_KB/PAT-0012 预留）
  enc_cw / enc_ccw                              编码器旋转
  enc_press                                     编码器按下（映射为 ok）

页面只认这些事件，不关心输入来源 → 三者可互换（DESIGN §7.3）。
触摸的点击由 LVGL indev 直接处理；切页手势在 M3 补充。
"""
from lib.buttons import Buttons


class InputManager:
    # 编码器按下映射到哪个按键事件
    ENC_PRESS_EVENT = "ok"

    def __init__(self, buttons: Buttons, rotary=None):
        self._buttons = buttons
        self._rotary = rotary
        self._last_enc = rotary.value() if rotary is not None else 0
        self._handlers = []

    def add_handler(self, cb):
        self._handlers.append(cb)

    def poll(self):
        """轮询一次，返回本周期产生的标准事件列表，并分发给 handler。"""
        events = []
        if self._buttons is not None:
            for name in self._buttons.poll():
                # 编码器按下引脚归在 buttons 里叫 enc_press，映射为 ok
                if name == "enc_press":
                    events.append(self.ENC_PRESS_EVENT)
                elif name == "long_enc_press":
                    events.append("long_" + self.ENC_PRESS_EVENT)
                else:
                    events.append(name)
        if self._rotary is not None:
            v = self._rotary.value()
            if v != self._last_enc:
                events.append("enc_cw" if v > self._last_enc else "enc_ccw")
                self._last_enc = v
        for ev in events:
            for h in self._handlers:
                try:
                    h(ev)
                except Exception:
                    pass
        return events
