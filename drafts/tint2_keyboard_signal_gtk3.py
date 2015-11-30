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


import signal
import re
import subprocess
import cairo
from gi.repository import GLib
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GdkPixbuf

ICON_SIZE = 22
FONT_SIZE = 19
Y_OFFSET = 16
FONT_FACE = "Ubuntu"


class KeyboardIcon:
    def __init__(self):
        sig = signal.SIGUSR1
        GLib.idle_add(self.install_glib_handler, sig,
                      priority=GLib.PRIORITY_HIGH)
        self.icon = Gtk.StatusIcon()
        self.draw_langs()
        self.icon.connect('activate', self.activate)
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
        """
        On change layout some outer daemon
        (xkb-switch -U) must send USR1 signal
        """

        self.update_widget()
        return GLib.SOURCE_CONTINUE

    def draw_langs(self):
        self.lang_en = self.draw_text("en")
        self.lang_ru = self.draw_text("ru")

    def update_widget(self):
        stdout = subprocess.check_output(["xkb-switch"])
        if re.search("ru", stdout):
            self.icon.set_from_pixbuf(self.lang_ru)
        else:
            self.icon.set_from_pixbuf(self.lang_en)

    def activate(self, widget):
        subprocess.call(["xkb-switch", "--next"])
        self.update_widget()

    def draw_text(self, text):
        pixbuf = GdkPixbuf.Pixbuf.new(
            GdkPixbuf.Colorspace.RGB, True, 8, ICON_SIZE, ICON_SIZE
        )
        surface = cairo.ImageSurface(
            cairo.FORMAT_ARGB32,
            pixbuf.get_width(),
            pixbuf.get_height()
        )
        context = cairo.Context(surface)
        Gdk.cairo_set_source_pixbuf(context, pixbuf, 0, 0)
        context.paint()

        context.select_font_face(
            FONT_FACE,
            cairo.FONT_SLANT_NORMAL,
            cairo.FONT_WEIGHT_BOLD
        )
        context.set_source_rgba(0.9, 0.9, 0.9, 1)
        context.set_font_size(FONT_SIZE)
        context.move_to(0, Y_OFFSET)
        context.show_text(text)

        #get the resulting pixbuf
        surface= context.get_target()
        pixbuf= Gdk.pixbuf_get_from_surface(surface, 0, 0, surface.get_width(), surface.get_height())

        return pixbuf

if __name__ == '__main__':
    KeyboardIcon()
    GLib.MainLoop().run()
