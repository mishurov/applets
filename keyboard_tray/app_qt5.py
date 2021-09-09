import os
import sys
import signal

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt5.QtGui import QIcon, QColor, QPainter, QPixmap

from core import XKBMixin, EXIT_LABEL, ICON_SIZE, FONT_FACE, FONT_COLOR


signal.signal(signal.SIGINT, signal.SIG_DFL)

FONT_SIZE = 17


class KeyboardIcon(XKBMixin):
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        # start class name with underscore so i3bar puts the icon first
        self.app.setApplicationName('_ input sources')
        self._init_menu()
        self._init_xcb_xkb()
        #self._init_xkb_groups()
        self._init_xkb_groups_simple()
        #self._draw_langs_icon_theme()
        self._draw_langs_renderer()
        self.icon = QSystemTrayIcon()
        self.icon.activated.connect(self.activate_icon)
        self.icon.setContextMenu(self.menu)
        self._init_xkb_handler()
        self.update_icon()

    def _init_menu(self):
        self.menu = QMenu()
        self.menu.addAction(EXIT_LABEL, self._exit)

    def _draw_text(self, text):
        dpr = self.app.devicePixelRatio()
        pixmap = QPixmap(int(ICON_SIZE * dpr), int(ICON_SIZE * dpr))
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        color = QColor()
        color.setRgbF(*FONT_COLOR)
        painter.setPen(color)
        font = painter.font()
        font.setFamily(FONT_FACE)
        font.setPixelSize(int(FONT_SIZE * dpr))
        font.setBold(True)
        painter.setFont(font)
        rect = pixmap.rect()
        rect.moveTop(-4)
        painter.drawText(rect, Qt.AlignCenter, text)
        painter.end()
        return QIcon(pixmap)

    def _get_theme_icon(self, icon_name):
        return QIcon.fromTheme(icon_name)

    def activate_icon(self, reason):
        if reason != QSystemTrayIcon.Trigger:
            return
        self.set_next_group()
        self.update_icon()

    def update_icon(self):
        group = self.get_xkb_group()
        self.icon.setIcon(self.langs[group])

    def async_listener(self):
        while True:
            e = self.xcb.xcb_wait_for_event(self.conn)
            if e:
                self.xcb.free(e)
                self.update_icon()

    def run(self):
        self.icon.show()
        sys.exit(self.app.exec_())

    def _exit(self, *args):
        self.xcb.xcb_disconnect(self.conn)
        os._exit(0)


if __name__ == '__main__':
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    keyboard_icon = KeyboardIcon()
    keyboard_icon.run()
