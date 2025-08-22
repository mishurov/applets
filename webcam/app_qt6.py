import os
import sys
import signal

from PyQt6 import sip
from PyQt6.QtCore import Qt, QObject, pyqtSignal, QPoint, QSize
from PyQt6.QtWidgets import (QApplication, QSystemTrayIcon, QMenu,
    QWidgetAction, QLabel, QScrollArea, QGridLayout, QPushButton, QWidget,
    QHBoxLayout, QSpinBox, QSlider, QComboBox, QCheckBox, QFileDialog,
    QStyledItemDelegate)
from PyQt6.QtGui import QIcon, QResizeEvent, QCursor

from core import V4l2Ctl


APP_NAME = 'Cam'
MENU_HEIGHT = 400
FILE_DIR = os.path.dirname(os.path.abspath(__file__))
ICON_PATH = os.path.join(FILE_DIR, 'cam-icon.svg')
LINUX_CSS = os.path.join(FILE_DIR, 'linux.css')


signal.signal(signal.SIGINT, signal.SIG_DFL)
os.chdir(FILE_DIR)

def clear_layout(layout):
    while layout.count():
        child = layout.takeAt(0)
        if child.widget():
            child.widget().deleteLater()
        child_layout = child.layout()
        if child_layout:
            clear_layout(child_layout)
            sip.delete(child_layout)

class IgnoreWheel(object):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def wheelEvent(self, e):
        if not self.hasFocus():
            e.ignore()

class BaseControl(object):
    valueChanged = pyqtSignal(str, int)
    changeFinished = pyqtSignal()

    def __init__(self, name, *args, **kwargs):
        self.name = name
        return super().__init__(*args, **kwargs)

    def get_value(self):
        return self.value


class HoverSlider(IgnoreWheel, QSlider):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setProperty('hovered', 'false')

    def updateStyle(self):
        self.style().unpolish(self)
        self.style().polish(self)

    def enterEvent(self, e):
        super().enterEvent(e)
        if self.isEnabled():
            self.setProperty('hovered', 'true')
        self.updateStyle()

    def leaveEvent(self, e):
        super().leaveEvent(e)
        self.setProperty('hovered', 'false')
        self.updateStyle()


class SpinWheel(IgnoreWheel, QSpinBox):
    pass


class Slider(BaseControl, QHBoxLayout):
    valueChanged = pyqtSignal(str, int)
    changeFinished = pyqtSignal()

    controls = []

    def __init__(self, minimum, maximum, step, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.step = step
        self.slider = HoverSlider(Qt.Orientation.Horizontal)
        self.slider.setMinimum(int(minimum / step))
        self.slider.setMaximum(int(maximum / step))
        self.slider.setSingleStep(1)
        self.slider.valueChanged.connect(self.on_slider_changed)
        self.slider.sliderReleased.connect(self.on_slider_released)
        self.spin = SpinWheel()
        self.spin.valueChanged.connect(self.on_spin_changed)
        self.spin.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.spin.setRange(minimum, maximum)
        self.spin.setSingleStep(step)
        self.spin.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        minus = QPushButton('-')
        minus.clicked.connect(lambda: self.spin.stepBy(-1))
        plus = QPushButton('+')
        plus.clicked.connect(lambda: self.spin.stepBy(1))
        self.addWidget(self.slider)
        self.addWidget(self.spin)
        self.addWidget(minus)
        self.addWidget(plus)
        self.controls = [self.slider, self.spin, minus, plus]

    def setDisabled(self, disabled):
        for c in self.controls:
            c.setDisabled(disabled)

    def on_slider_released(self):
        self.changeFinished.emit()

    def on_slider_changed(self, value):
        self.value = int(value * self.step)
        self.spin.blockSignals(True)
        self.spin.setValue(self.value)
        self.spin.blockSignals(False)
        self.valueChanged.emit(self.name, self.value)

    def on_spin_changed(self, value):
        self.value = int(value)
        self.slider.blockSignals(True)
        self.slider.setValue(int(self.value / self.step))
        self.slider.blockSignals(False)
        self.valueChanged.emit(self.name, self.value)
        self.changeFinished.emit()

    def set_value(self, value):
        self.value = value
        self.spin.blockSignals(True)
        self.slider.blockSignals(True)
        self.spin.setValue(self.value)
        self.slider.setValue(int(self.value / self.step))
        self.spin.blockSignals(False)
        self.slider.blockSignals(False)


class Dropdown(BaseControl, IgnoreWheel, QComboBox):
    def __init__(self, options, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.options = options
        self.addItems(options.values())
        self.activated.connect(self.on_activated)
        self.setItemDelegate(QStyledItemDelegate())
        self.view().parentWidget().setStyleSheet('border: 0')

    def on_activated(self, index):
        self.value = int(list(self.options.keys())[index])
        self.valueChanged.emit(self.name, self.value)
        self.changeFinished.emit()

    def set_value(self, value):
        self.value = int(value)
        self.blockSignals(True)
        options = list(self.options.keys())
        value_str = str(self.value)
        if value_str in options:
            index = options.index(value_str)
            self.setCurrentIndex(index)
        self.blockSignals(False)


class CheckBox(BaseControl, QCheckBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stateChanged.connect(self.on_value_changed)

    def on_value_changed(self, state):
        self.value = 1 if state else 0
        self.valueChanged.emit(self.name, self.value)
        self.changeFinished.emit()

    def set_value(self, value):
        self.value = int(value)
        self.blockSignals(True)
        self.setCheckState(
            Qt.CheckState.Checked if self.value else Qt.CheckState.Unchecked)
        self.blockSignals(False)



class Action(QWidgetAction):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.widget = QWidget()
        self.layout = QGridLayout()
        self.widget.setLayout(self.layout)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setWidget(self.widget)
        self.setDefaultWidget(self.scroll)


class CameraIcon(QObject):
    formats = []
    ui_controls = {}
    ui_format = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.v4l2_ctl = V4l2Ctl()
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        self.app.setApplicationName(APP_NAME)
        with open(LINUX_CSS, 'r') as css_file:
            self.app.setStyleSheet(css_file.read())
        self.create_icon()
        self.create_menu()
        self.run()

    def create_icon(self):
        self.icon = QSystemTrayIcon(QIcon(ICON_PATH))
        self.icon.activated.connect(self.activate)

    def create_menu(self):
        self.menu = QMenu()
        self.action = Action(self.menu)
        self.menu.addAction(self.action)

    def activate_exit(self, *args):
        os._exit(0)
        return True

    def on_format_value_changed(self, name, value):
        pix, res, fps = self.formats[value]
        self.v4l2_ctl.set_format(pix, res, fps)

    def on_format_change_finished(self):
        self.current_format = self.v4l2_ctl.get_format()
        self.update_format()

    def on_control_value_changed(self, name, value):
        self.v4l2_ctl.set_control(name, value)

    def on_control_change_finished(self):
        self.controls_data = self.v4l2_ctl.read_controls()
        self.update_controls()

    def on_export(self):
        file_name, _ = QFileDialog.getSaveFileName()
        if file_name:
            script = self.v4l2_ctl.export_script()
            with open(filename, 'w') as f:
                f.write(script)

    def append_widget_to_layout(self, widget):
        layout = self.action.layout
        layout.rowCount()
        layout.addWidget(widget, layout.rowCount(), 0, 1, 2)

    def add_export(self):
        button = QPushButton('Export settings script')
        button.clicked.connect(self.on_export)
        self.append_widget_to_layout(button)

    def add_quit(self):
        button = QPushButton('Exit')
        button.clicked.connect(lambda: os._exit(0))
        self.append_widget_to_layout(button)

    def add_format(self):
        if len(self.formats):
            formats = {str(k) : f'{p} {r} {f}' for k, [p, r, f] in enumerate(self.formats)}
            self.ui_format = Dropdown(formats, 'formats')
            self.ui_format.valueChanged.connect(self.on_format_value_changed)
            self.ui_format.changeFinished.connect(self.on_format_change_finished)
            self.append_widget_to_layout(self.ui_format)
        else:
            self.ui_format = None

    def add_controls(self):
        self.ui_controls = {}
        layout = self.action.layout
        for row, [k, v] in enumerate(self.controls_data.items()):
            label = QLabel(k)
            layout.addWidget(label, row, 0, 1, 1, Qt.AlignmentFlag.AlignRight)

            ctl_type = v[0]
            params = v[1]
            control = None
            if ctl_type == 'bool':
                control = CheckBox(k)
            elif ctl_type == 'int':
                control = Slider(
                    int(params['min']),
                    int(params['max']),
                    int(params['step']),
                    k,
                )
            elif ctl_type == 'menu':
                control = Dropdown(v[2], k)

            if control is None:
                continue

            control.valueChanged.connect(self.on_control_value_changed)
            control.changeFinished.connect(self.on_control_change_finished)
            add = getattr(self.action.layout,
                'addWidget' if control.isWidgetType() else 'addLayout')
            add(control, row, 1)
            self.ui_controls[k] = control

    def readd_widgets(self):
        clear_layout(self.action.layout)
        self.add_controls()
        self.add_format()
        self.add_export()
        self.add_quit()

    def update_controls(self):
        for k, v in self.ui_controls.items():
            data = self.controls_data[k][1]
            v.set_value(int(data['value']))
            disabled = 'flags' in data and data['flags'] == 'inactive'
            v.setDisabled(disabled)

    def update_format(self):
        if self.current_format != [None, None, None]:
            self.ui_format.set_value(self.formats.index(self.current_format))

    def update_menu_size(self):
        self.action.layout.invalidate()
        self.action.layout.activate()
        hint = self.action.widget.sizeHint()
        width = hint.width() + 20
        height = min(MENU_HEIGHT, hint.height())
        self.action.scroll.setFixedWidth(width)
        self.action.scroll.setFixedHeight(height)
        self.menu.setFixedWidth(width)
        self.menu.setFixedHeight(height)
        self.menu.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
        self.menu.show()
        self.menu.hide()
        self.menu.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, False)

    def activate(self, reason):
        self.controls_data = self.v4l2_ctl.read_controls()
        self.formats = self.v4l2_ctl.read_formats()
        self.current_format = self.v4l2_ctl.get_format()
        self.readd_widgets()
        self.update_controls()
        self.update_format()
        icon_pos = self.icon.geometry().bottomRight()
        pos = QPoint(QCursor.pos().x(), icon_pos.y())
        self.update_menu_size()
        self.menu.popup(pos)
        return True

    def run(self):
        self.icon.show()
        sys.exit(self.app.exec())


if __name__ == '__main__':
    # X11 tray icon artefacts, can be set as env var
    # QT_SCALE_FACTOR_ROUNDING_POLICY
    # Round, Ceil, Floor, RoundPreferFloor, PassThrough
    #QApplication.setHighDpiScaleFactorRoundingPolicy(
    #    Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    #)
    CameraIcon()
