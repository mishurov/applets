#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) Alexander Mishurov All rights reserved.
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following
# conditions are met:

# 1. Redistributions of source code must retain the above
# copyright notice, this list of conditions and the following disclaimer

# 2. Redistributions in binary form must reproduce the above
# copyright notice, this list of conditions and the following disclaimer
# in the documentation and/or other materials provided with
# the distribution.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,
# STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED
# OF THE POSSIBILITY OF SUCH DAMAGE.


import re
import signal
import subprocess
from gi.repository import GLib
from gi.repository import Gtk
from gi.repository import Gdk


BUTTON_LABEL = "Pulse Audio"
ICON_SIZE = 22
MIXER_CMD = "pavucontrol"
WIDTH = 250
TOP_OFFSET = 28
RIGHT_OFFSET = 5
STEP=1


class SoundIcon:
    def __init__(self):
        sig = signal.SIGUSR1
        GLib.idle_add(self.install_glib_handler, sig,
                      priority=GLib.PRIORITY_HIGH)
        self.icon = Gtk.StatusIcon()
        self.icon_theme = Gtk.IconTheme.get_default()
        self.icon.connect('activate', self.activate)
        self.icon.connect('popup-menu', self.popup_menu)
        self.icon.connect('scroll-event', self.scroll)
        self.create_window()
        self.update_widget()

    def install_glib_handler(self, sig):
        unix_signal_add = None
        if hasattr(GLib, "unix_signal_add"):
            unix_signal_add = GLib.unix_signal_add
        elif hasattr(GLib, "unix_signal_add_full"):
            unix_signal_add = GLib.unix_signal_add_full
        if unix_signal_add:
            print("Register GLib signal handler: %r" % sig)
            unix_signal_add(GLib.PRIORITY_HIGH, sig, 
                            self.signal_handler, sig)
        else:
            print("Can't install GLib signal handler, too old gi.")

    def signal_handler(self, data):
        self.update_widget()
        return GLib.SOURCE_CONTINUE

    def update_widget(self):
        vol = self.get_volume()
        self.icon.set_from_pixbuf(self.get_icon(vol))

    def get_icon(self, value):
        if not value[1]:
            icon ="audio-volume-muted-panel"
        elif value[0] < 25:
            icon = "audio-volume-low-panel"
        elif value[0] > 75:
            icon = "audio-volume-high-panel"
        else:
            icon = "audio-volume-medium-panel"
        return self.icon_theme.load_icon(icon, ICON_SIZE, 0)

    def get_volume(self):
        stdout = subprocess.check_output(["amixer","get", "Master"])
        m = re.search("([0-9]+)%\] \[([a-z]+)\]", stdout)
        if m and len(m.groups()) == 2:
            vol = m.groups()[0]
            muted_str = m.groups()[1]
            if muted_str == "on":
                return (int(vol), True)
            else:
                return (int(vol), False)

    def set_volume(self, volume):
        cmd = ["amixer", "-q", "set", 
               "Master", str(volume) + "%"]
        subprocess.call(cmd)

    def toggle_volume(self):
        cmd = ["amixer", "-q", "set", 
               "Master", "toggle"]
        subprocess.call(cmd)

    def change_volume(self, direction="+"):
        cmd = ["amixer", "-q", "set", "Master", 
               str(STEP) + "%" + str(direction)]
        subprocess.call(cmd)

    def on_change_slider(self, widget):
        volume = widget.get_value()
        self.set_volume(int(volume))
        self.update_widget()

    def create_slider(self):
        slider = Gtk.HScale()
        slider.set_inverted(False)
        slider.set_range(0, 100)
        slider.set_increments(1, 10)
        slider.set_digits(0)
        slider.set_size_request(WIDTH, 1)
        slider.connect('value-changed', self.on_change_slider)
        slider.set_value(self.get_volume()[0])
        return slider

    def create_button(self):
        button = Gtk.Button(label=BUTTON_LABEL)
        button.connect("clicked", self.on_button_clicked)
        return button

    def create_window(self):
        self.window = Gtk.Window(Gtk.WindowType.POPUP)
        self.window.set_border_width(10)
        # Add event box to catch mouse events on childs
        self.eventbox = Gtk.EventBox()
        vbox = Gtk.VBox(spacing=0)
        vbox.add(self.create_slider())
        vbox.add(self.create_button())
        self.eventbox.connect("leave-notify-event",
                              self.on_window_leaved)
        self.eventbox.add(vbox)
        self.window.add(self.eventbox)

    def on_window_leaved(self, widget, event):
        self.hide_window()

    def on_button_clicked(self, widget):
        subprocess.call(MIXER_CMD)

    def move_window(self):
        icon_rect = self.icon.get_geometry()[2]
        screen_width = Gdk.Screen.width()
        if icon_rect.x + WIDTH / 2 + RIGHT_OFFSET > screen_width:
            window_x = screen_width - WIDTH - RIGHT_OFFSET
        else:
            window_x = icon_rect.x - WIDTH / 2 - RIGHT_OFFSET
        window_y = TOP_OFFSET
        self.window.move(window_x, window_y)

    def hide_window(self):
        self.window.hide()
        self.window.unrealize()

    def show_window(self):
        self.move_window()
        self.window.show_all()

    def activate(self, widget):
        if self.window.is_visible():
            self.hide_window()
        else:
            self.show_window()

    def popup_menu(self, widget, button, time):
        """Called on right click"""
        self.toggle_volume()
        self.update_widget()

    def scroll(self, widget, event):
        drct = event.direction
        if drct == Gdk.ScrollDirection.UP:
            self.change_volume("+")
        elif drct == Gdk.ScrollDirection.DOWN:
            self.change_volume("-")
        self.update_widget()

if __name__ == '__main__':
    SoundIcon()
    GLib.MainLoop().run()
