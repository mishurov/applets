#!/usr/local/bin/python3

# brew install python3 pyqt6
# /usr/local/bin/pip3 install -U PyObjC
# mkdir ~/.cache

# sway config 20 px is the height of the waybar (top)
# for_window [title="^ReminderContextMenu$" app_id="^reminder_tray$" floating] {
#     move position mouse
#     move down 20 px
# }

import signal
import os
import sys
from PyQt6.QtCore import Qt, QTimer, QPoint, QUrl, QSize
from PyQt6.QtWidgets import (
    QApplication,
    QSystemTrayIcon,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QWidget,
    QMenu,
    QWidgetAction,
    QSpinBox,
    QLabel,
)
from PyQt6.QtGui import QIcon, QFont, QPalette, QCursor

from core import (
    TimerMixin,
    ALERT_TEXT,
    BUTTON_LABEL,
    EXIT_LABEL,
    ASSETS_DIR,
    ALARM_PATH,
    ALARM_URGENT_PATH,
    ALARM_ACTIVE_PATH,
    WINDOW_TITLE,
    DEFAULT_CLOCK,
)

from sway_ipc import get_socket, command


CLOCK_FONT_SIZE = 29
SPINBOX_SPACING = 3
SPINBOX_WINDOW_SPACING = 9

LINUX_CSS = os.path.join(ASSETS_DIR, 'linux.css')
MACOS_CSS = os.path.join(ASSETS_DIR, 'macos.css')
APP_STYLESHEET = MACOS_CSS if sys.platform == 'darwin' else LINUX_CSS


signal.signal(signal.SIGINT, signal.SIG_DFL)

if sys.platform == 'darwin':
    import AppKit
    info = AppKit.NSBundle.mainBundle().infoDictionary()
    info["LSUIElement"] = "1"


class ShowCenterMixin(object):
    def show_center(self, win):
        centerPoint = QApplication.primaryScreen().availableGeometry().center()
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
                a.button.setProperty('objectName', 'menuItemHover')
            else:
                a.button.setProperty('objectName', 'menuItem')
            self.update_style(a.button)

    def on_menu_activated_macos(self):
        for a in self.menu.actions:
            a.button.setProperty('objectName', 'menuItem')
            self.update_style(a.button)


class ButtonSpinBox(QHBoxLayout):
    def __init__(self, *args, **kwargs):
        text = kwargs.pop('label')
        super().__init__(*args, **kwargs)
        label = QLabel(text)
        self.spin = QSpinBox()
        self.spin.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.spin.setRange(0, 23 if text == 'h' else 59)
        self.spin.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        if sys.platform == 'darwin':
            self.spin.setAttribute(Qt.WidgetAttribute.WA_MacShowFocusRect, 0)
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


class Reminder(ShowCenterMixin, OsxMenuMixin, TimerMixin):
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        self.app.setDesktopFileName('reminder_tray')
        self.screen_height = self.app.primaryScreen().geometry().height()
        styleSheet = open(APP_STYLESHEET).read()
        if sys.platform == 'darwin':
            c = self.app.palette().color(QPalette.ColorRole.Highlight)
            color = 'rgba({},{},{},10%)'.format(c.red(), c.green(), c.blue())
            styleSheet = styleSheet.replace('palette(highlight)', color)
        self.app.setStyleSheet(styleSheet)

        self.setup_icon()
        self.setup_menu()
        self.setup_popup()
        self.setup_window()

        self.sock = get_socket()
        if self.sock:
            fake_menu = QMenu()
            fake_menu.addAction('Fuck Wayland')
            self.icon.setContextMenu(fake_menu)

        self.init_saved_alarm()
        self.idle()
        self.run()

    def on_button_clicked(self, *args):
        self.window.hide()
        h = self.spins[0].value()
        m = self.spins[1].value()
        s = self.spins[2].value()
        self.start_timer(h, m, s)

    def setup_window(self):
        self.window = QWidget()
        self.window.setProperty('objectName', 'window')
        self.window.setWindowTitle(WINDOW_TITLE)
        self.window.setWindowFlags(
            self.window.windowFlags() |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Dialog)
        vlayout = QVBoxLayout(self.window)
        hlayout = QHBoxLayout()
        hlayout.setSpacing(SPINBOX_WINDOW_SPACING)

        if sys.platform == 'darwin':
            vlayout.setSpacing(0)
            vlayout.setContentsMargins(14, 7, 14, 16)

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
        self.icon_normal = QIcon(ALARM_PATH)
        self.icon = QSystemTrayIcon(self.icon_normal)
        self.icon_urgent = QIcon(ALARM_URGENT_PATH)
        self.icon_active = QIcon(ALARM_ACTIVE_PATH)
        self.icon.activated.connect(self.activate_menu)

    def setup_menu(self):
        self.menu = QMenu()
        self.menu.setWindowTitle(WINDOW_TITLE + 'ContextMenu')
        self.menu.setProperty('objectName', 'menu')
        clock_item = QWidgetAction(self.menu)
        self.clock = QPushButton(DEFAULT_CLOCK)
        self.clock.setProperty('objectName', 'menuItem')
        font = self.clock.font()
        font.setPointSize(CLOCK_FONT_SIZE)
        self.clock.setFont(font)

        clock_item.setDefaultWidget(self.clock)
        self.clock.clicked.connect(self.activate_window)

        exit_item = QWidgetAction(self.menu)
        label = QPushButton(EXIT_LABEL)
        label.setProperty('objectName', 'menuItem')
        exit_item.setDefaultWidget(label)
        label.clicked.connect(self.activate_exit)

        self.menu.addAction(clock_item)
        if sys.platform == 'darwin':
            self.menu.addSeparator()
        self.menu.addAction(exit_item)
        self.menu.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.Popup)

        if sys.platform == 'darwin':
            clock_item.button = self.clock
            exit_item.button = label
            self.menu.actions = [clock_item, exit_item]
            self.set_up_menu_macos(self.menu)

    def setup_popup(self):
        self.popup = QWidget()
        self.popup.setProperty('objectName', 'popup')
        self.popup.setWindowFlags(
            Qt.WindowType.Sheet |
            Qt.WindowType.Popup |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint)
        self.popup.setWindowTitle(WINDOW_TITLE + 'Popup')

        if sys.platform == 'darwin':
            self.popup.setAttribute(
                Qt.WidgetAttribute.WA_TranslucentBackground, True)
            cvlayout = QVBoxLayout(self.popup)
            self.popup.setProperty('objectName', 'popupContainer')
            roundBox = QWidget()
            roundBox.setProperty('objectName', 'popup')
            cvlayout.addWidget(roundBox)
            vlayout = QVBoxLayout(roundBox)
            cvlayout.setContentsMargins(0, 0, 0, 0)
            vlayout.setContentsMargins(0, 0, 0, 0)
        else:
            vlayout = QVBoxLayout(self.popup)

        label = QLabel(ALERT_TEXT)
        vlayout.addWidget(label)

        self.popup.setFixedSize(self.popup.sizeHint())
        self.popup.mouseReleaseEvent = self.on_popup_release

    def on_popup_release(self, *args):
        self.popup.hide()

    def activate_menu(self, reason):
        if reason != QSystemTrayIcon.ActivationReason.Trigger:
            return
        if self.menu.isVisible():
            self.menu.close()
            return True
        if self.window.isVisible():
            self.window.close()
        if self.popup.isVisible():
            self.popup.close()
        if self.icon.icon().cacheKey() == self.icon_urgent.cacheKey():
            self.clear_alarm()
            self.set_icon(self.icon_normal)
        self.update_clock()
        if sys.platform == 'darwin':
            self.on_menu_activated_macos()
            self.icon.setContextMenu(self.menu)
            self.icon.setContextMenu(None)
            return
        self.menu.setFixedSize(self.menu.sizeHint())
        icon_pos = self.icon.geometry().bottomRight()
        pos = QPoint(QCursor.pos().x(), icon_pos.y())
        if icon_pos.y() > self.screen_height / 2:
            self.menu.popup(pos, self.menu.actions()[-1])
        else:
            self.menu.popup(pos)

    def activate_window(self, *args):
        if sys.platform == 'darwin':
            clock_action = self.menu.actions[0]
            clock_action.activate(clock_action.ActivationReason.Trigger)
        self.window.setFixedSize(self.window.sizeHint())
        self.show_center(self.window)

    def activate_exit(self, *args):
        if self.sock:
            self.sock.close()
        os._exit(0)

    def set_icon(self, icon):
        self.icon.setIcon(icon)

    def update_clock_text(self, text):
        text = text.strip()
        self.clock.setText(text)

    def show_popup(self):
        self.menu.hide()
        if self.sock:
            command(self.sock, 'fullscreen disable')
        self.show_center(self.popup)

    def is_menu_visible(self):
        if sys.platform == 'darwin':
            return True
        return self.menu.isVisible()

    def run(self):
        timer = QTimer()
        timer.setInterval(1000)
        timer.timeout.connect(self.idle)
        timer.start(1000)
        self.icon.show()
        sys.exit(self.app.exec())


if __name__ == '__main__':
    # X11 tray icon artefacts, can be set as env var
    # QT_SCALE_FACTOR_ROUNDING_POLICY
    # Round, Ceil, Floor, RoundPreferFloor, PassThrough
    #if sys.platform != 'darwin':
    #    QApplication.setHighDpiScaleFactorRoundingPolicy(
    #        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    #    )
    Reminder()
