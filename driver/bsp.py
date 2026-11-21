"""板级支持：集中管理总线与引脚，单例复用（_KB/PAT-0001）。

引脚号只来自 config；按 ENABLE_* 开关按需创建，未启用的硬件不初始化。
"""
import machine

import config


class Board:
    _instance = None

    def __init__(self):
        self._sensor_i2c = None
        self._buttons = None
        self._gps_uart = None

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ---------- I2C：传感器（与触摸共用 I2C1） ----------
    def sensor_i2c(self):
        if self._sensor_i2c is None:
            if config.SENSOR_SDA is None or config.SENSOR_SCL is None:
                raise ValueError("请在 config.py 配置 SENSOR_SDA/SCL")
            self._sensor_i2c = machine.I2C(
                config.SENSOR_I2C_ID,
                scl=machine.Pin(config.SENSOR_SCL),
                sda=machine.Pin(config.SENSOR_SDA),
                freq=config.SENSOR_FREQ,
            )
        return self._sensor_i2c

    # ---------- 按键 ----------
    def buttons(self):
        if self._buttons is None:
            self._buttons = {
                "up": self._input(config.BTN_UP),
                "down": self._input(config.BTN_DOWN),
                "left": self._input(config.BTN_LEFT),
                "right": self._input(config.BTN_RIGHT),
                "ok": self._input(config.BTN_OK),
                "cancel": self._input(config.BTN_CANCEL),
            }
            # 编码器按下也走按键轮询，InputManager 会把 enc_press 映射为 ok
            if config.ENABLE_ENCODER and config.ENC_PRESS is not None:
                self._buttons["enc_press"] = self._input(config.ENC_PRESS)
        return self._buttons

    # ---------- GPS UART ----------
    def gps_uart(self):
        if self._gps_uart is None:
            self._gps_uart = machine.UART(
                config.GPS_UART_ID,
                baudrate=config.GPS_BAUD,
                tx=config.GPS_TX,
                rx=config.GPS_RX,
            )
        return self._gps_uart

    @staticmethod
    def _input(number):
        if number is None:
            return None
        return machine.Pin(number, machine.Pin.IN, machine.Pin.PULL_UP)
