import os
import sys
import signal
import time
import subprocess
from PyQt5.QtCore import (
    Qt,
    QObject,
    QThread,
    QPoint,
    QRect,
    pyqtSignal,
)
from PyQt5.QtWidgets import (
    QApplication,
    QSystemTrayIcon,
    QMenu,
    QAction,
    QWidgetAction,
    QSlider,
    QLabel,
    QDialog,
    QWidget,
    QVBoxLayout,
)
from PyQt5.QtGui import QIcon, QWheelEvent, QPainter, QCursor

from core import Brightness, UPower

# sudo cp ./90-brightness.rules /etc/udev/rules.d/
# usermod -aG video ${USER}
# reboot

# sway config 20 px is the height of the waybar (top)
# for_window [app_id="^power_tray$" floating] move position mouse, move down 20 px

ICON_THEME = 'Adwaita-Xfce'

BRIGHTNESS_WIDTH = 250
BRIGHTNESS_HEIGHT = 50

LABEL_EXIT = 'Exit'
LABEL_MANAGER = 'Settings...'
CMD_MANAGER = 'xfce4-power-manager --customize'

FILE_DIR = os.path.dirname(os.path.abspath(__file__))
LINUX_CSS = os.path.join(FILE_DIR, 'linux.css')

signal.signal(signal.SIGINT, signal.SIG_DFL)


class LabelledSlider(QSlider):
    SLIDER_H_PADDING = 20
    RECT_W = 26
    RECT_H = 10

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setStyleSheet('padding: 30px {hm}px 15px {hm}px'.format(
            hm=self.SLIDER_H_PADDING)
        )
        self.setProperty('hovered', 'false')

    def paintEvent(self, e):
        super().paintEvent(e)
        rect = e.rect()
        if (rect.width() != BRIGHTNESS_WIDTH):
            return
        painter = QPainter(self)
        value = self.value()
        width = BRIGHTNESS_WIDTH - self.SLIDER_H_PADDING * 2
        mid_x = width * (value / 100) + self.SLIDER_H_PADDING
        rect = QRect(int(mid_x - self.RECT_W / 2), 12,
                     self.RECT_W, self.RECT_H)
        painter.drawText(rect, Qt.AlignCenter, str(value));

    def updateStyle(self):
        self.style().unpolish(self)
        self.style().polish(self)

    def enterEvent(self, e):
        super().enterEvent(e)
        self.setProperty(
            'hovered', 'true' if self.isEnabled() else 'false')
        self.updateStyle()

    def leaveEvent(self, e):
        super().leaveEvent(e)
        self.setProperty('hovered', 'false')
        self.updateStyle()


class SliderItem(QWidgetAction):
    value_changed = pyqtSignal(int)
    rmb_clicked = pyqtSignal()
    init_x = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.attachSlider()

    def createSlider(self):
        slider = LabelledSlider(Qt.Horizontal)
        self.setDefaultWidget(slider)
        slider.setMinimum(0)
        slider.setMaximum(100)
        slider.setSingleStep(10)
        slider.setMinimumWidth(BRIGHTNESS_WIDTH)
        slider.setMinimumHeight(BRIGHTNESS_HEIGHT)
        slider.valueChanged.connect(self.onValueChanged)
        return slider

    def attachSlider(self):
        slider = self.createSlider()
        self._slider = slider

    def setValue(self, value):
        self._slider.setValue(value)

    def onValueChanged(self, value):
        self.value_changed.emit(value)

    def onRightButtonClicked(self):
        self.rmb_clicked.emit()

    def setEnabled(self, enabled):
        # super().setEnabled(enabled)
        self._slider.setEnabled(enabled)


class MenuItem(QWidgetAction):
    SLIDER_H_MARGIN = 8
    def __init__(self, *args, **kwargs):
        text = args[0]
        subtitle = kwargs.pop('subtitle', None)
        super().__init__(*args[1:], **kwargs)
        self.label = QLabel(text)
        if subtitle is None:
            self.setDefaultWidget(self.label)
        else:
            self.label.setProperty('objectName', 'title')
            self.sublabel = QLabel(subtitle)
            self.sublabel.setProperty('objectName', 'subtitle')
            layout = QVBoxLayout()
            layout.setSpacing(0)
            layout.setContentsMargins(0, 5, 0, 5)
            layout.addWidget(self.label)
            layout.addWidget(self.sublabel)
            widget = QWidget()
            widget.setLayout(layout)
            self.setDefaultWidget(widget)

    def setEnabled(self, enabled):
        super().setEnabled(enabled)
        self.label.setEnabled(enabled)


class BatteryReader(QObject):
    batteryUpdated = pyqtSignal(int, bool)
    battery = None
    line_power = None

    def __init__(self, battery, line_power):
        super().__init__()
        self.battery = battery
        self.line_power = line_power
        self.upower = UPower()

    def run(self):
        while True:
            percentage = 0
            if self.battery is not None:
                percentage = self.upower.get_battery_percentage(
                    self.battery)
            online = False
            if self.line_power is not None:
                online = self.upower.get_line_power_online(self.line_power)
            self.batteryUpdated.emit(percentage, online)
            time.sleep(1)

class PowerIcon(QObject):
    battery_proxy_interface = None
    line_power_proxy_interface = None
    device_actions = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app = QApplication(sys.argv)
        self.app.setApplicationName('XFCE Adwaita Power Tray')
        self.app.setDesktopFileName('power_tray')
        self.app.setQuitOnLastWindowClosed(False)
        self.screen_height = self.app.primaryScreen().geometry().height()
        with open(LINUX_CSS, 'r') as css_file:
            self.app.setStyleSheet(css_file.read())

        self.brightness = Brightness()
        self.upower = UPower()

        self.create_icon()
        self.create_menu()

        self.set_theme_icon('ac-adapter')
        self.setup_devices()

        if os.environ.get('SWAYSOCK', None) is not None:
            fake_menu = QMenu()
            fake_menu.addAction('Fuck Wayland')
            self.icon.setContextMenu(fake_menu)

        self.run()

    def create_icon(self):
        QIcon.setThemeName(ICON_THEME)
        self.icon_name = ''
        self.icon = QSystemTrayIcon()
        self.icon.activated.connect(self.activate)

    def set_theme_icon(self, icon_name):
        qicon = QIcon.fromTheme(icon_name)
        self.icon.setIcon(qicon)

    def create_menu(self):
        self.menu = QMenu()
        if self.brightness.intel_path_exists:
            self.slider_item = SliderItem(self.menu)
            self.slider_item.value_changed.connect(self.on_value_changed)
        exit_item = self.create_exit()
        manager_item = self.create_manager()
        if hasattr(self, 'slider_item'):
            self.menu.addSeparator()
            self.menu.addAction(self.slider_item)
        self.menu.addSeparator()
        self.menu.addAction(manager_item)
        self.menu.addAction(exit_item)
        self.menu.setWindowFlags(Qt.FramelessWindowHint | Qt.Popup)

    def get_devices(self):
        battery = None
        line_power = None
        misc = []
        devices = self.upower.detailed_devices()
        for d in devices:
            device_type = d['device_type']
            if device_type == 'Battery':
                battery = d
            elif device_type == 'Line Power':
                line_power = d
            else:
                misc.append(d)
        return battery, line_power, misc

    def setup_devices(self):
        battery, line_power, misc = self.get_devices()
        if line_power is not None:
            self.line_power_proxy_interface = line_power[
                'device_proxy_interface']
        if battery is None:
            return
        self.battery_proxy_interface = battery[
            'device_proxy_interface']
        self.thread = QThread()
        self.battery_reader = BatteryReader(
            self.battery_proxy_interface,
            self.line_power_proxy_interface,
        )
        self.battery_reader.moveToThread(self.thread)
        self.thread.started.connect(self.battery_reader.run)
        self.battery_reader.batteryUpdated.connect(self.on_battery_updated)
        self.thread.start()

    def battery_icon_percentage(self, percent):
        if percent < 10:
            return '0'
        if percent < 20:
            return '10'
        if percent < 30:
            return '20'
        if percent < 40:
            return '30'
        if percent < 50:
            return '40'
        if percent < 60:
            return '50'
        if percent < 70:
            return '60'
        if percent < 80:
            return '70'
        if percent < 90:
            return '80'
        if percent < 100:
            return '90'
        else:
            return '100'

    def on_battery_updated(self, percentage, online):
        # ac-adapter
        # battery-full-symbolic
        # battery-full-charging-symbolic
        # battery-missing-symbolic
        # battery-level-100-charged-symbolic
        icon_name = 'battery-level-{percentage}{charging}-symbolic'.format(
            percentage=self.battery_icon_percentage(percentage),
            charging='-charging' if online else '',
        )
        self.set_theme_icon(icon_name)

    def on_value_changed(self, value):
        self.brightness.set_percent(value)
        return True

    def activate(self, reason):
        if reason != QSystemTrayIcon.Trigger:
            return False
        if self.menu.isVisible():
            self.menu.close()
            return True

        if hasattr(self, 'slider_item'):
            self.slider_item.setValue(int(self.brightness.current_percent))
        self.update_menu()

        self.menu.setFixedSize(self.menu.sizeHint())
        icon_pos = self.icon.geometry().bottomRight()
        pos = QPoint(QCursor.pos().x(), icon_pos.y())
        if icon_pos.y() > self.screen_height / 2:
            self.menu.popup(pos, self.menu.actions()[-1])
        else:
            self.menu.popup(pos)
        return True

    def destroy_action(self, item):
        self.menu.removeAction(item)
        item.deleteLater()

    def update_menu(self):
        battery, line_power, misc = self.get_devices()
        for a in self.device_actions:
            self.destroy_action(a)
        self.device_actions = []
        self.devices = [battery, line_power] + misc
        for pos, d in enumerate(self.devices):
            if d is None:
                continue
            v = d['vendor']
            vendor = v + ' ' if len(v) else ''
            title = vendor + d['model']
            charge = ' ' + str(d['percentage']) + '%'
            if d == battery:
                subtitle = d['state'] + charge
            elif d == line_power:
                title = d['device_type']
                subtitle = 'online' if d['online'] else 'offline'
            else:
                subtitle = 'Current charge' + charge
            item = MenuItem(title, self.menu, subtitle=subtitle)
            before = self.menu.actions()[pos]
            self.menu.insertAction(before, item)
            self.device_actions.append(item)

    def create_exit(self):
        item = MenuItem(LABEL_EXIT, self.menu)
        item.label.setProperty('objectName', 'subaction')
        item.triggered.connect(self.activate_exit)
        return item

    def activate_exit(self, *args):
        os._exit(0)
        return True

    def create_manager(self):
        item = MenuItem(LABEL_MANAGER, self.menu)
        item.label.setProperty('objectName', 'subaction')
        item.triggered.connect(self.activate_manager)
        return item

    def activate_manager(self, *args):
        subprocess.Popen(
            [CMD_MANAGER], shell=True, stdin=None,
            stdout=None, stderr=None, close_fds=True
        )
        return True

    def run(self):
        self.icon.show()
        sys.exit(self.app.exec_())


if __name__ == '__main__':
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    PowerIcon()
