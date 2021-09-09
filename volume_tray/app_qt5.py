import os
import sys
import signal

from PyQt5.QtCore import Qt, QPoint, QRect, pyqtSignal, QObject
from PyQt5.QtWidgets import (
    QApplication, QSystemTrayIcon, QMenu, QAction, QWidgetAction, QSlider,
    QLabel
)
from PyQt5.QtGui import QIcon, QWheelEvent, QPainter

from core import (
    PulseMixer,
    VolumeMixin,
    APP_NAME,
    LABEL_MIXER,
    LABEL_EXIT,
    SCROLL_BY
)

VOLUME_WIDTH = 250
VOLUME_HEIGHT = 50

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
        if (rect.width() != VOLUME_WIDTH):
            return
        painter = QPainter(self)
        value = self.value()
        width = VOLUME_WIDTH - self.SLIDER_H_PADDING * 2
        mid_x = width * (value / 100) + self.SLIDER_H_PADDING
        rect = QRect(int(mid_x - self.RECT_W / 2), 12, self.RECT_W, self.RECT_H)
        painter.drawText(rect, Qt.AlignCenter, str(value));

    def updateStyle(self):
        self.style().unpolish(self)
        self.style().polish(self)

    def enterEvent(self, e):
        super().enterEvent(e)
        self.setProperty('hovered', 'true')
        self.updateStyle()

    def leaveEvent(self, e):
        super().leaveEvent(e)
        self.setProperty('hovered', 'false')
        self.updateStyle()


class SliderItem(QWidgetAction):
    value_changed = pyqtSignal(int)
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
        slider.setMinimumWidth(VOLUME_WIDTH)
        slider.setMinimumHeight(VOLUME_HEIGHT)
        slider.valueChanged.connect(self.onValueChanged)
        return slider

    def attachSlider(self):
        slider = self.createSlider()
        self._slider = slider

    def setValue(self, value):
        self._slider.setValue(value)

    def onValueChanged(self, value):
        self.value_changed.emit(value)


class MenuItem(QWidgetAction):
    SLIDER_H_MARGIN = 8
    def __init__(self, *args, **kwargs):
        text = args[0]
        super().__init__(*args[1:], **kwargs)
        self.label = QLabel(text)
        self.setDefaultWidget(self.label)

    def setEnabled(self, enabled):
        super().setEnabled(enabled)
        self.label.setEnabled(enabled)


class SoundIcon(QObject, VolumeMixin):
    icon_updated = pyqtSignal(object)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        self.app.setApplicationName(APP_NAME)
        self.screen_height = self.app.primaryScreen().geometry().height()
        with open(LINUX_CSS, 'r') as css_file:
            self.app.setStyleSheet(css_file.read())

        self.mixer = PulseMixer()
        self.init_dbus()
        self.create_icon()
        self.mixer.start_listener(lambda: self.icon_updated.emit)
        self.icon_updated.connect(self.update_icon)
        self.create_menu()
        self.update_icon()

        self.run()

    def create_icon(self):
        self.icon_name = ''
        self.icon = QSystemTrayIcon()
        self.icon.activated.connect(self.activate)
        self.icon.eventFilter = self.on_scroll
        self.icon.installEventFilter(self.icon)

    def create_menu(self):
        self.menu = QMenu()
        self.slider_item = SliderItem(self.menu)
        self.slider_item.value_changed.connect(self.on_value_changed)
        mixer_item = self.create_mixer()
        exit_item = self.create_exit()
        self.menu.addAction(self.slider_item)
        self.menu.addAction(mixer_item)
        self.menu.addSeparator()
        self.menu.addSeparator()
        self.menu.addAction(exit_item)

    def create_mixer(self):
        item = MenuItem(LABEL_MIXER, self.menu)
        item.triggered.connect(self.activate_mixer)
        return item

    def create_exit(self):
        item = MenuItem(LABEL_EXIT, self.menu)
        item.triggered.connect(self.activate_exit)
        return item

    def activate_exit(self, *args):
        os._exit(0)
        return True

    def on_value_changed(self, value):
        self.mixer.set_volume(value)
        return True

    def activate(self, reason):
        if reason == QSystemTrayIcon.Context:
            self.mixer.toggle_mute()
            return True
        if reason != QSystemTrayIcon.Trigger:
            return False
        self.update_menu()
        volume, mute = self.mixer.get_sink_volume_and_mute()
        self.slider_item.setValue(int(volume))
        self.slider_item.setEnabled(not mute)

        icon_pos = self.icon.geometry().bottomRight()
        width = min(self.menu.geometry().width(), VOLUME_WIDTH)
        if icon_pos.y() > self.screen_height / 2:
            pos = icon_pos - QPoint(width, 40)
            self.menu.popup(pos, self.menu.actions()[-1])
        else:
            pos = icon_pos - QPoint(width, 0)
            self.menu.popup(pos)
        return True

    def destroy_item(self, item):
        self.menu.removeAction(item)
        item.deleteLater()

    def insert_label_item(self, label, pos):
        item = MenuItem(label, self.menu)
        item.label.setProperty('objectName', 'section')
        before = self.menu.actions()[pos]
        self.menu.insertAction(before, item)
        item.setEnabled(False)
        self.profile_items.append(item)

    def insert_subaction_item(self, profile, link, pos):
        item = MenuItem(profile, self.menu)
        item.label.setProperty('objectName', 'subaction')
        item.triggered.connect(lambda c: self.mixer.set_profile(link))
        before = self.menu.actions()[pos]
        self.menu.insertAction(before, item)
        if link == self.mixer.current_profile:
            item.setEnabled(False)
        self.profile_items.append(item)

    def on_scroll(self, obj, event):
        if not isinstance(event, QWheelEvent):
            return False
        delta_y = event.angleDelta().y()
        if delta_y == 0:
            return
        change = SCROLL_BY if delta_y > 0 else -SCROLL_BY
        self.mixer.change_volume(change)
        return True

    def set_theme_icon(self, icon_name):
        qicon = QIcon.fromTheme(icon_name)
        self.icon.setIcon(qicon)

    def is_menu_visible(self):
        return self.menu.isVisible()

    def run(self):
        self.icon.show()
        sys.exit(self.app.exec_())

if __name__ == '__main__':
    SoundIcon()
