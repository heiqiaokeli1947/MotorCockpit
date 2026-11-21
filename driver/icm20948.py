"""ICM20948 9 轴传感器最小驱动（I2C）。

最小实现：读 WHO_AM_I、加速度、陀螺仪（bank 0）。
磁力计（AK09916）与完整姿态解算留到 M2 验证后补全。

验证状态：code-only（待硬件验证）。参考 jposada202020/MicroPython_ICM20948。
寄存器来自 ICM-20948 数据手册。
"""
import struct
import time

import config

INVALID = -9999

WHO_AM_I = 0x00
WHO_AM_I_VALUE = 0xEA
REG_BANK_SEL = 0x7F

# Bank 0
PWR_MGMT_1 = 0x06
PWR_MGMT_2 = 0x07
ACCEL_XOUT_H = 0x2D
GYRO_XOUT_H = 0x33

_ACCEL_SENS = 16384.0   # ±2g 量程
_GYRO_SENS = 131.0      # ±250°/s 量程


class ICM20948:
    def __init__(self, i2c, addr=None):
        self.i2c = i2c
        self.addr = addr if addr is not None else config.ICM20948_ADDR
        self.hardWareReady = False
        self.ax = self.ay = self.az = INVALID
        self.gx = self.gy = self.gz = INVALID

    def _bank(self, bank):
        self.i2c.writeto_mem(self.addr, REG_BANK_SEL, bytes([bank << 4]))

    def _read_regs(self, reg, n):
        return self.i2c.readfrom_mem(self.addr, reg, n)

    def initHardware(self):
        try:
            self._bank(0)
            who = self._read_regs(WHO_AM_I, 1)[0]
            if who != WHO_AM_I_VALUE:
                print("ICM20948 WHO_AM_I mismatch: 0x%02X (expect 0x%02X)" % (who, WHO_AM_I_VALUE))
                self.hardWareReady = False
                return
            # 唤醒：清 PWR_MGMT_1 的 sleep 位
            self.i2c.writeto_mem(self.addr, PWR_MGMT_1, b"\x01")
            time.sleep_ms(20)
            # 使能加速度/陀螺仪
            self.i2c.writeto_mem(self.addr, PWR_MGMT_2, b"\x00")
            self.hardWareReady = True
        except OSError:
            self.hardWareReady = False

    def read(self):
        try:
            if not self.hardWareReady:
                self.initHardware()
                if not self.hardWareReady:
                    return False
            self._bank(0)
            a = struct.unpack(">hhh", self._read_regs(ACCEL_XOUT_H, 6))
            g = struct.unpack(">hhh", self._read_regs(GYRO_XOUT_H, 6))
            self.ax, self.ay, self.az = (round(v / _ACCEL_SENS, 3) for v in a)
            self.gx, self.gy, self.gz = (round(v / _GYRO_SENS, 2) for v in g)
            return True
        except OSError:
            self.hardWareReady = False
            self.ax = self.ay = self.az = INVALID
            self.gx = self.gy = self.gz = INVALID
            return False
