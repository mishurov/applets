#!/usr/local/bin/python3

# brew install pyqt5
# /usr/local/bin/pip3 install -U PyObjC
# mkdir ~/.cache

import signal
import os
import sys
import re
import json
from datetime import datetime, timedelta
from PyQt5.QtCore import Qt, QTimer, QPoint, QUrl
from PyQt5.QtWidgets import (
    QApplication, QSystemTrayIcon, QVBoxLayout, QHBoxLayout, QPushButton,
    QDesktopWidget, QWidget, QMenu, QWidgetAction, QSpinBox, QLabel
)
from PyQt5.QtGui import QIcon, QFont, QPalette


signal.signal(signal.SIGINT, signal.SIG_DFL)

if sys.platform == 'darwin':
    import AppKit
    info = AppKit.NSBundle.mainBundle().infoDictionary()
    info["LSUIElement"] = "1"


CLOCK_FONT_SIZE = 35
ALERT_FONT_SIZE = 60
SPINBOX_SPACING = 3
SPINBOX_WINDOW_SPACING = 9
SPINBOX_WINDOW_TITLE = 'Reminder'
ALERT_TEXT = 'Alert'
EXIT_LABEL = 'Exit'
BUTTON_LABEL = 'Start'

HOME = os.environ.get("HOME")
CACHE_DIR = os.environ.get("XDG_CACHE_HOME", None) or os.path.join(HOME, ".cache")
REMINDER_FILE = os.path.join(CACHE_DIR, "reminder_data.json")

FILE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(FILE_DIR, '..', 'Resources')
LINUX_CSS = os.path.join(ASSETS_DIR, 'linux.css')
MACOS_CSS = os.path.join(ASSETS_DIR, 'macos.css')
APP_STYLESHEET = MACOS_CSS if sys.platform == 'darwin' else LINUX_CSS
ALARM_PATH = os.path.join(ASSETS_DIR, 'alarm-clock.svg')
ALARM_ACTIVE_PATH = os.path.join(ASSETS_DIR, 'alarm-clock-active.svg')
ALARM_URGENT_PATH = os.path.join(ASSETS_DIR, 'alarm-clock-urgent.svg')


def str_to_timedelta(s):
    m = re.match(r'(?P<hours>\d+):(?P<minutes>\d+):(?P<seconds>\d[\.\d+]*)', s)
    kwargs = {key: float(val) for key, val in m.groupdict().items()}
    return timedelta(**kwargs)


class ShowCenterMixin(object):
    def show_center(self, win):
        centerPoint = QDesktopWidget().availableGeometry().center()
        win.show()
        win_geo = win.frameGeometry()
        win_geo.moveCenter(centerPoint)
        win.move(win_geo.topLeft())


class OsxMenuMixin(object):
    def set_up_menu_macos(self, menu):
        menu.hovered.connect(self.on_menu_hovered_macos)

    def update_style(self, obj):
        obj.style().unpolish(obj)
        obj.style().polish(obj)

    def on_menu_hovered_macos(self, action):
        for a in self.menu.actions:
            if a == action:
                a.button.setProperty('objectName', 'menuhover')
            else:
                a.button.setProperty('objectName', 'menu')
            self.update_style(a.button)

    def on_menu_activated_macos(self):
        for a in self.menu.actions:
            a.button.setProperty('objectName', 'menu')
            self.update_style(a.button)


class ButtonSpinBox(QHBoxLayout):
    def __init__(self, *args, **kwargs):
        text = kwargs.pop('label')
        super().__init__(*args, **kwargs)
        label = QLabel(text)
        self.spin = QSpinBox()
        self.spin.setRange(0, 23 if text == 'h' else 59)
        self.spin.setButtonSymbols(QSpinBox.NoButtons)
        if sys.platform == 'darwin':
            self.spin.setAttribute(Qt.WA_MacShowFocusRect, 0)
        minus = QPushButton('-')
        minus.setProperty('objectName', 'spin')
        minus.clicked.connect(lambda: self.spin.stepBy(-1))
        plus = QPushButton('+')
        plus.setProperty('objectName', 'spin')
        plus.clicked.connect(lambda: self.spin.stepBy(1))
        self.setSpacing(SPINBOX_SPACING)
        self.addWidget(label)
        self.addWidget(self.spin)
        self.addWidget(minus)
        self.addWidget(plus)


class Reminder(ShowCenterMixin, OsxMenuMixin):
    start = None
    timedelta = None
    discount = {'hours': 0, 'minutes': 0, 'seconds': 0}

    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        styleSheet = open(APP_STYLESHEET).read()
        if sys.platform == 'darwin':
            c = self.app.palette().color(QPalette.Highlight)
            color = 'rgba({},{},{},10%)'.format(c.red(), c.green(), c.blue())
            styleSheet = styleSheet.replace('palette(highlight)', color)
        self.app.setStyleSheet(styleSheet)

        self.setup_icon()
        self.setup_menu()
        self.setup_popup()
        self.setup_window()
        self.init_saved_alarm()
        self.idle()
        self.run()

    def init_saved_alarm(self):
        if not os.path.isfile(REMINDER_FILE):
            open(REMINDER_FILE, "w").close()
        else:
            with open(REMINDER_FILE, "r") as reminder_file:
                data = reminder_file.read()
                if data:
                    data = json.loads(data)
                    self.start = datetime.fromisoformat(data['start'])
                    self.timedelta = str_to_timedelta(data['timedelta'])
                    self.icon.setIcon(self.qicon_active)

    def save_alarm(self):
        data = {
            'start': self.start.isoformat(),
            'timedelta': str(self.timedelta),
        }
        data = json.dumps(data, indent=4)
        with open(REMINDER_FILE, "w") as reminder_file:
            reminder_file.write(data)

    def on_button_clicked(self, *args):
        self.window.hide()
        h = self.spins[0].value()
        m = self.spins[1].value()
        s = self.spins[2].value()
        self.timedelta = timedelta(hours=h, minutes=m, seconds=s)
        self.start = datetime.now()
        self.save_alarm()
        self.icon.setIcon(self.qicon_active)

    def setup_window(self):
        self.window = QWidget()
        self.window.setProperty('objectName', 'window')
        self.window.setWindowTitle(SPINBOX_WINDOW_TITLE)
        self.window.setWindowFlags(
            self.window.windowFlags() | Qt.WindowStaysOnTopHint | Qt.Dialog)
        vlayout = QVBoxLayout(self.window)
        hlayout = QHBoxLayout()
        hlayout.setSpacing(SPINBOX_WINDOW_SPACING)

        self.spins = []
        for label in ['h', 'm', 's']:
            button_spin = ButtonSpinBox(label=label)
            spin = button_spin.spin
            self.spins.append(spin)
            hlayout.addLayout(button_spin)

        button = QPushButton(BUTTON_LABEL)
        button.setProperty('objectName', 'start')

        vlayout.addLayout(hlayout)
        vlayout.addWidget(button)

        button.clicked.connect(self.on_button_clicked)
        self.window.closeEvent = self.on_window_close

    def on_window_close(self, *args):
        self.window.hide()

    def setup_icon(self):
        self.icon = QSystemTrayIcon(self.app)
        self.qicon = QIcon(ALARM_PATH)
        self.qicon_urgent = QIcon(ALARM_URGENT_PATH)
        self.qicon_active = QIcon(ALARM_ACTIVE_PATH)
        self.icon.setIcon(self.qicon)
        self.icon.activated.connect(self.activate_menu)

    def update_clock(self):
        if self.start is not None and self.timedelta is not None:
            t_time = '{hours:2d}:{minutes:02d}:{seconds:02d}'
        else:
            t_time = 'X:YY:ZZ'

        self.clock.setText(t_time.format(**self.discount))

    def setup_menu(self):
        self.menu = QMenu()
        clock_item = QWidgetAction(self.menu)
        self.clock = QPushButton(' ')
        self.clock.setProperty('objectName', 'menu')
        font = self.clock.font()
        font.setPixelSize(CLOCK_FONT_SIZE)
        self.clock.setFont(font)
        clock_item.setDefaultWidget(self.clock)
        self.clock.clicked.connect(self.activate_window)

        exit_item = QWidgetAction(self.menu)
        label = QPushButton(EXIT_LABEL)
        label.setProperty('objectName', 'menu')
        exit_item.setDefaultWidget(label)
        label.clicked.connect(self.activate_exit)

        self.menu.addAction(clock_item)
        self.menu.addAction(exit_item)

        if sys.platform == 'darwin':
            clock_item.button = self.clock
            exit_item.button = label
            self.menu.actions = [clock_item, exit_item]
            self.set_up_menu_macos(self.menu)

    def setup_popup(self):
        self.popup = QWidget()
        self.popup.setProperty('objectName', 'popup')
        vlayout = QVBoxLayout(self.popup)
        label = QLabel(ALERT_TEXT)
        font = label.font()
        font.setPixelSize(ALERT_FONT_SIZE)
        label.setFont(font)
        vlayout.addWidget(label)
        self.popup.setWindowFlags(Qt.Sheet | Qt.Popup |
            Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)

        self.popup.mouseReleaseEvent = self.on_popup_release

    def on_popup_release(self, *args):
        self.popup.hide()

    def activate_menu(self, reason):
        if self.icon.icon().cacheKey() == self.qicon_urgent.cacheKey():
            with open(REMINDER_FILE, "w") as reminder_file:
                reminder_file.write('')
            self.icon.setIcon(self.qicon)
        self.update_clock()
        if reason != QSystemTrayIcon.Trigger:
            return
        if sys.platform == 'darwin':
            self.on_menu_activated_macos()
            self.icon.setContextMenu(self.menu)
            self.icon.setContextMenu(None)
        else:
            icon_pos = self.icon.geometry().bottomRight()
            width = min(self.menu.geometry().width(), 135)
            pos = icon_pos - QPoint(width, 0)
            self.menu.popup(pos)

    def activate_window(self, *args):
        if sys.platform == 'darwin':
            clock_action = self.menu.actions[0]
            clock_action.activate(clock_action.Trigger)
        self.show_center(self.window)

    def activate_exit(self, *args):
        os._exit(0)

    def idle(self):
        if self.start is not None and self.timedelta is not None:
            td = datetime.now() - self.start
            if self.timedelta > td:
                td = self.timedelta - td
                self.discount.update({
                    'hours': int(td.seconds / 3600) % 24,
                    'minutes': int(td.seconds / 60) % 60,
                    'seconds': td.seconds % 60,
                })
            else:
                self.start = None
                self.timedelta = None
                self.discount.update({'hours': 0, 'minutes': 0, 'seconds': 0})
                self.icon.setIcon(self.qicon_urgent)
                self.show_center(self.popup)

            if self.menu.isVisible():
                self.update_clock()

        return True

    def run(self):
        timer = QTimer()
        timer.setInterval(1000)
        timer.timeout.connect(self.idle)
        timer.start(1000)
        self.icon.show()
        sys.exit(self.app.exec_())


if __name__ == '__main__':
    Reminder()
