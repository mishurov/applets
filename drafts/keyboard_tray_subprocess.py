#!/usr/bin/env python2

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


import os
import re
import signal
import subprocess
import pygtk
import gtk
import gobject
import cairo
from gtk import gdk

ICON_SIZE = 22
FONT_SIZE = 18
Y_OFFSET = 16
FONT_FACE = "Ubuntu"
POLL_TIMEOUT=100


class KeyboardIcon(object):
    def __init__(self):
        signal.signal(signal.SIGINT, gtk.main_quit)
        self.icon = gtk.StatusIcon()
        self.draw_langs()
        self.init_xkb()
        self.update_icon()
        self.icon.connect('activate', self.activate)
        self.icon.set_visible(True)

    def init_xkb(self):
        self.lang_line = ""
        cpid, cstdin, cstdout, cstderr = gobject.spawn_async(
            ['xkb-switch','-W'],
            flags=gobject.SPAWN_SEARCH_PATH|gobject.SPAWN_DO_NOT_REAP_CHILD,
            standard_output=True,
        )
        gobject.io_add_watch(cstdout,
                             gobject.IO_IN,
                             self.xkb_listener)
        self.channel = os.fdopen(cstdout)

    def xkb_listener(self, fd, condition):
        if condition == gobject.IO_IN:
            self.lang_line = self.channel.readline()
            self.update_icon()
        return True

    def draw_langs(self):
        self.lang_en = self.draw_text("en")
        self.lang_ru = self.draw_text("ru")

    def update_icon(self):
        if re.search("ru", self.lang_line):
            self.icon.set_from_pixbuf(self.lang_ru)
        else:
            self.icon.set_from_pixbuf(self.lang_en)

    def activate(self, widget):
        subprocess.call(["xkb-switch", "--next"])
        self.update_icon()

    def draw_text(self, text):
        pixbuf = gdk.Pixbuf(gdk.COLORSPACE_RGB,
                            True, 8, ICON_SIZE, ICON_SIZE)
        pixbuf.fill(0x00000000)
        pixmap = pixbuf.render_pixmap_and_mask(
            alpha_threshold=127
        )[0] 
        cr = pixmap.cairo_create()

        cr.select_font_face(FONT_FACE,
                            cairo.FONT_SLANT_NORMAL,
                            cairo.FONT_WEIGHT_BOLD)
        cr.set_source_rgba(0.9, 0.9, 0.9, 1)
        cr.set_font_size(FONT_SIZE)
        cr.move_to(0, Y_OFFSET)
        cr.show_text(text)

        pixbuf.get_from_drawable(pixmap, pixmap.get_colormap(),
                                 0, 0, 0, 0, ICON_SIZE, ICON_SIZE)
        pixbuf = pixbuf.add_alpha(True, 0x00, 0x00, 0x00)

        return pixbuf


if __name__ == '__main__':
    pygtk.require("2.0")
    KeyboardIcon()
    gtk.main()
