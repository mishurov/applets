#!/usr/bin/python3

# python pyqt.py

import sys
import time

import numpy
from matplotlib import pyplot
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from OpenGL import GL

from PyQt5.QtCore import Qt, QDate, QFile, QIODevice, QTimer
from PyQt5.QtWidgets import (QApplication, QVBoxLayout, QWidget, QLabel,
QPushButton, QCalendarWidget, QScrollArea, QSlider, QRadioButton, QSizePolicy)
from PyQt5.QtGui import (QWindow, QPalette, QColor, QSurfaceFormat,
QOpenGLVersionProfile, QOpenGLContext)
from PyQt5.QtSvg import QSvgWidget


def get_dark_palette():
    light = QColor(255, 255, 255)
    dark = QColor(0, 0, 0)
    accent = QColor(255, 0, 0)
    hilight = QColor(127, 1, 1)
    palette = QPalette()
    light_gray = QColor(53, 53, 53)
    dark_gray = QColor(15, 15, 15)
    palette.setColor(QPalette.Window, light_gray)
    palette.setColor(QPalette.WindowText, light)
    palette.setColor(QPalette.Base, dark_gray)
    palette.setColor(QPalette.AlternateBase, light_gray)
    palette.setColor(QPalette.ToolTipBase, light)
    palette.setColor(QPalette.ToolTipText, light)
    palette.setColor(QPalette.Text, light)
    palette.setColor(QPalette.Button, light_gray)
    palette.setColor(QPalette.ButtonText, light)
    palette.setColor(QPalette.BrightText, accent)
    palette.setColor(QPalette.Highlight, hilight.lighter())
    palette.setColor(QPalette.HighlightedText, dark)
    return palette


class WindowPlot(FigureCanvasQTAgg):
    def __init__(self, parent=None):
        pyplot.style.use("dark_background")
        fig = Figure(figsize=(8, 5), dpi=80)
        self.axes = fig.add_subplot(111)

        super().__init__(fig)
        self.setParent(parent)

        FigureCanvasQTAgg.setSizePolicy(
            self, QSizePolicy.Expanding, QSizePolicy.Expanding
        )
        FigureCanvasQTAgg.updateGeometry(self)

        timer = QTimer(self)
        timer.timeout.connect(self.update_figure)
        timer.start(50)

        self.x  = numpy.arange(0, 4 * numpy.pi, 0.1)
        self.y  = numpy.sin(self.x)

        self.setWindowTitle("Plot")

    def update_figure(self):
        self.axes.clear()
        self.axes.plot(self.x, self.y)
        self.y = numpy.roll(self.y, -1)
        self.draw()


class WindowUI(QWidget):
    def __init__(self, parent=None):
        super().__init__()
        label = QLabel("Label")
        slider = QSlider(Qt.Horizontal)
        slider.setValue(50)
        radiobutton1 = QRadioButton("Radio")
        radiobutton1.setChecked(True)
        radiobutton2 = QRadioButton("Button")
        button = QPushButton("Push The Button")

        layout = QVBoxLayout()
        layout.addWidget(label)
        layout.addWidget(slider)
        layout.addWidget(radiobutton1)
        layout.addWidget(radiobutton2)
        layout.addWidget(button)

        self.setLayout(layout)
        self.setWindowTitle("UI")


class WindowSvg(QWidget):
    def __init__(self, parent=None):
        super().__init__()

        image = QFile('foundry.svg')
        image.open(QIODevice.ReadOnly)
        self.data = image.readAll()
        image.close()

        area = QScrollArea()
        self.label = QSvgWidget()
        self.label.renderer().load(self.data)
        area.setWidget(self.label)

        layout = QVBoxLayout()
        layout.addWidget(area)
        self.setLayout(layout)
        self.setWindowTitle("SVG")


class WindowCal(QWidget):
    def __init__(self):
        super().__init__()

        self.create_calendar()
        layout = QVBoxLayout()
        layout.addWidget(self.calendar)
        self.setLayout(layout)
        self.setWindowTitle("Calendar")

    def create_calendar(self):
        self.calendar = QCalendarWidget()
        self.calendar.setMinimumDate(QDate(1900, 1, 1))
        self.calendar.setMaximumDate(QDate(3000, 1, 1))
        self.calendar.setGridVisible(True)



class WindowGL(QWindow):
    def __init__(self):
        super().__init__()

        fmt = QSurfaceFormat()
        fmt.setVersion(2, 0)
        fmt.setProfile(QSurfaceFormat.CompatibilityProfile)
        fmt.setStereo(False)
        fmt.setSwapBehavior(QSurfaceFormat.DoubleBuffer)

        self.setSurfaceType(QWindow.OpenGLSurface)
        self.context = QOpenGLContext()
        self.context.setFormat(fmt)

        if not self.context.create():
            raise Exception("Unable to create context")

        self.create()
        self.setTitle("OpenGL")

    def exposeEvent(self, e):
        e.accept()
        if self.isExposed() and self.isVisible():
            self.update()

    def makeCurrent(self):
        self.context.makeCurrent(self)

    def swapBuffers(self):
        self.context.swapBuffers(self)

    def resize(self, w, h):
        super().resize(w, h)
        self.makeCurrent()
        GL.glViewport(0, 0, w, h)

    def update(self):
        tri_size = 0.7
        self.makeCurrent()
        GL.glClearColor(0,0,0,0)
        GL.glClearDepth(1)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
        GL.glBegin(GL.GL_TRIANGLES)
        GL.glVertex2f(0, tri_size)
        GL.glColor3f(1, 0, 0)
        GL.glVertex2f(-tri_size, -tri_size)
        GL.glColor3f(0, 1, 0)
        GL.glVertex2f(tri_size, -tri_size)
        GL.glColor3f(0, 0, 1)
        GL.glEnd()
        GL.glFlush()
        self.swapBuffers()



if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setPalette(get_dark_palette())


    opengl_window = WindowGL()
    opengl_window.resize(500, 500)
    opengl_window.setPosition(25, 225)
    opengl_window.show()

    cal_window = WindowCal()
    cal_window.move(625, 125)
    cal_window.show()

    ui_window = WindowUI()
    ui_window.resize(350, 150)
    ui_window.move(1425, 225)
    ui_window.show()

    plot_window = WindowPlot()
    plot_window.move(625, 625)
    plot_window.show()

    svg_window = WindowSvg()
    svg_window.resize(400, 250)
    svg_window.move(1375, 575)
    svg_window.show()



    sys.exit(app.exec_())
