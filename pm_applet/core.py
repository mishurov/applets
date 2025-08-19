import dbus  # sudo apt install python3-dbus
from pathlib import Path
from functools import lru_cache


class UPower(object):
    UPOWER_NAME = 'org.freedesktop.UPower'
    UPOWER_PATH = '/org/freedesktop/UPower'
    DBUS_PROPERTIES = 'org.freedesktop.DBus.Properties'

    DEVICE_STATE = {
        0: 'Unknown',
        1: 'Charging',
        2: 'Discharging',
        3: 'Empty',
        4: 'Fully charged',
        5: 'Pending charge',
        6: 'Pending discharge',
    }

    DEVICE_TYPE = {
        0: 'Unknown',
        1: 'Line Power',
        2: 'Battery',
        3: 'Ups',
        4: 'Monitor',
        5: 'Mouse',
        6: 'Keyboard',
        7: 'Pda',
        8: 'Phone',
        17: 'Bluetooth',
    }

    def __init__(self):
        super().__init__()
        self.bus = dbus.SystemBus()

    def device_detail(self, device):
        device_proxy = self.bus.get_object(self.UPOWER_NAME, device)
        device_proxy_interface = dbus.Interface(
            device_proxy, self.DBUS_PROPERTIES)
        device_type = device_proxy_interface.Get(
            self.UPOWER_NAME + ".Device", "Type")
        online = device_proxy_interface.Get(
            self.UPOWER_NAME + ".Device", "Online")
        percentage = device_proxy_interface.Get(
            self.UPOWER_NAME + ".Device", "Percentage")
        state = device_proxy_interface.Get(
            self.UPOWER_NAME + ".Device", "State")
        model = device_proxy_interface.Get(
            self.UPOWER_NAME + ".Device", "Model")
        vendor = device_proxy_interface.Get(
            self.UPOWER_NAME + ".Device", "Vendor")
        detail = {
            'device_type': self.DEVICE_TYPE.get(int(device_type), 'Undefined'),
            'vendor': str(vendor),
            'model': str(model),
            'online': bool(online),
            'percentage': int(percentage),
            'state': self.DEVICE_STATE.get(int(state), 'Undefined'),
            'device_proxy_interface': device_proxy_interface,
        }
        return detail

    def get_battery_percentage(self, device_proxy_interface):
        percentage = device_proxy_interface.Get(
            self.UPOWER_NAME + ".Device", "Percentage")
        return int(percentage)

    def get_line_power_online(self, device_proxy_interface):
        online = device_proxy_interface.Get(
            self.UPOWER_NAME + ".Device", "Online")
        return bool(online)

    def devices(self):
        upower_proxy = self.bus.get_object(self.UPOWER_NAME, self.UPOWER_PATH) 
        upower_interface = dbus.Interface(upower_proxy, self.UPOWER_NAME)
        devs = upower_interface.EnumerateDevices()
        return devs

    def detailed_devices(self):
        devs = self.devices()
        return [self.device_detail(d) for d in devs]


class Brightness(object):
    path = Path('/sys/class/backlight/intel_backlight')

    @property
    def intel_path_exists(self):
        return self.path.exists()

    @property
    def current(self) -> int:
        with open(self.path / 'actual_brightness') as f:
            return int(f.read().strip())

    @property
    def current_percent(self) -> float:
        return self.current / self.max * 100

    @property
    @lru_cache(maxsize=512)
    def max(self) -> int:
        with open(self.path / 'max_brightness') as f:
            return int(f.read().strip())

    def set(self, value: int):
        value = min(value, self.max)
        value = max(value, 0)
        value = str(int(value))
        with open(self.path / 'brightness', 'w') as f:
            f.write(value)

    def set_percent(self, percent: int | float):
        max_value = self.max
        value = int(max_value * percent / 100)
        self.set(value)


# TODO: remove
if __name__ == '__main__':
    upower = UPower()
    print(upower.detailed_devices())
