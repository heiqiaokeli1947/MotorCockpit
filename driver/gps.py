"""串口 GPS NMEA 解析。

解析 RMC（时间/定位/速度/航向）与 GGA（经纬度/海拔/搜星数）。
注意 UART.read() 可能返回 None（_KB/PIT-0009），需判空。

验证状态：code-only（待硬件验证）。
"""
import time

import config

INVALID = -9999


def _nmea_float(token):
    try:
        return float(token)
    except (ValueError, TypeError):
        return INVALID


def _parse_lat_lon(lat, lat_dir, lon, lon_dir):
    lat = _nmea_float(lat)
    lon = _nmea_float(lon)
    if lat == INVALID or lon == INVALID:
        return INVALID, INVALID
    lat_deg = int(lat / 100) + (lat % 100) / 60
    lon_deg = int(lon / 100) + (lon % 100) / 60
    if lat_dir == "S":
        lat_deg = -lat_deg
    if lon_dir == "W":
        lon_deg = -lon_deg
    return round(lat_deg, 6), round(lon_deg, 6)


class GPS:
    def __init__(self, uart):
        self.uart = uart
        self.fix = False
        self.lat = INVALID
        self.lon = INVALID
        self.speed_kn = INVALID   # 节
        self.course = INVALID     # 度
        self.altitude = INVALID   # 米
        self.sats = INVALID
        self.utc = ""             # hhmmss.sss
        self.date = ""            # ddmmyy
        self._buf = ""

    def poll(self):
        """读 UART，解析完整语句，返回 True 若有新数据。"""
        try:
            data = self.uart.read()
        except Exception:
            data = None
        if not data:
            return False
        try:
            self._buf += data.decode("ascii", "ignore")
        except Exception:
            self._buf = ""
            return False
        while "\n" in self._buf:
            line, self._buf = self._buf.split("\n", 1)
            line = line.strip()
            if line.startswith("$G"):
                self._parse(line)
        return True

    def _parse(self, line):
        # 去掉校验和
        if "*" in line:
            line = line[: line.index("*")]
        parts = line.split(",")
        if not parts:
            return
        tag = parts[0]
        try:
            if tag in ("$GPRMC", "$GNRMC") and len(parts) >= 10:
                self.utc = parts[1]
                self.fix = parts[2] == "A"
                self.lat, self.lon = _parse_lat_lon(
                    parts[3], parts[4], parts[5], parts[6]
                )
                self.speed_kn = _nmea_float(parts[7])
                self.course = _nmea_float(parts[8])
                self.date = parts[9]
            elif tag in ("$GPGGA", "$GNGGA") and len(parts) >= 10:
                self.lat, self.lon = _parse_lat_lon(
                    parts[2], parts[3], parts[4], parts[5]
                )
                self.sats = int(parts[7]) if parts[7].isdigit() else INVALID
                self.altitude = _nmea_float(parts[9])
                if parts[6] in ("1", "2", "4", "5"):
                    self.fix = True
        except (IndexError, ValueError):
            pass

    def speed_kmh(self):
        if self.speed_kn == INVALID:
            return INVALID
        return round(self.speed_kn * 1.852, 1)

    def summary(self):
        return {
            "fix": self.fix,
            "lat": self.lat,
            "lon": self.lon,
            "speed_kmh": self.speed_kmh(),
            "course": self.course,
            "altitude": self.altitude,
            "sats": self.sats,
            "utc": self.utc,
        }
