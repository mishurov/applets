#!/usr/bin/env python2
# -*- coding: utf-8 -*-

# Copyright (c) Alexander Mishurov. All rights reserved.
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


import ctypes
import ctypes.util
import signal
import pygtk
import gtk
from gtk import gdk
import gobject
import cairo


FONT_FACE = "Ubuntu"
FONT_SIZE = 18
ICON_SIZE = 22
Y_OFFSET = 16
NATIVE_LANG_TEXT = "en"
FOREIGN_LANG_TEXT = "ru"
POLL_TIMEOUT=100


class Display(ctypes.Structure):
    pass


class XkbStateRec(ctypes.Structure):
   _fields_ = [
        ('group', ctypes.c_ubyte),
        ('locked_group', ctypes.c_ubyte),
        ('base_group', ctypes.c_ushort),
        ('latched_group', ctypes.c_ushort),
        ('mods', ctypes.c_ubyte),
        ('base_mods', ctypes.c_ubyte),
        ('latched_mods', ctypes.c_ubyte),
        ('locked_mods', ctypes.c_ubyte),
        ('compat_state', ctypes.c_ubyte),
        ('grab_mods', ctypes.c_ubyte),
        ('compat_grab_mods', ctypes.c_ubyte),
        ('lookup_mods', ctypes.c_ubyte),
        ('compat_lookup_mods', ctypes.c_ubyte),
        ('ptr_buttons', ctypes.c_ushort),
    ]


class XAnyEvent(ctypes.Structure):
    _fields_ = [
        ('type', ctypes.c_int),
        ('serial', ctypes.c_ulong),
        ('send_event', ctypes.c_int),
        ('display', ctypes.POINTER(Display)),
        ('window', ctypes.c_ulong),
    ]


class XEvent(ctypes.Union):
    _fields_ = [
        ('type', ctypes.c_int),
        ('xany', XAnyEvent),
        ('pad', ctypes.c_long*24),
    ]


class KeyboardIcon(object):
    def __init__(self):
        signal.signal(signal.SIGINT, gtk.main_quit)
        self.icon = gtk.StatusIcon()
        self.draw_langs()
        self.init_x11lib()
        self.icon.connect('activate', self.toggle_layout)
        self.update_icon()
        self.icon.set_visible(True)

    def init_x11lib(self):
        x_library_location = ctypes.util.find_library('X11')
        self.libX11 = ctypes.CDLL(x_library_location)
        self.libX11.XOpenDisplay.restype = ctypes.POINTER(Display)
        self.xkb_use_core_kbd = ctypes.c_uint(0x0100)
        mask = ctypes.c_uint(1 << 11)
        self.display = self.libX11.XOpenDisplay(None)
        self.xkb_event_number = ctypes.c_int()
        self.libX11.XkbQueryExtension(
            self.display, None,
            ctypes.byref(self.xkb_event_number),
            None, None, None
        )
        self.libX11.XkbSelectEvents(
            self.display,
            self.xkb_use_core_kbd,
            mask,
            mask,
        )
        self.x_event = XEvent()
        self.x_event_ref = ctypes.byref(self.x_event)
        gobject.timeout_add(POLL_TIMEOUT,
                            self.poll)

    def poll(self):
        if self.libX11.XCheckTypedEvent(
            self.display, self.xkb_event_number, self.x_event_ref
        ):
            gobject.idle_add(
                self.update_icon
            )
        return True

    def get_xkb_group(self):
        state = XkbStateRec()
        state_ref = ctypes.byref(state)
        self.libX11.XkbGetState(
            self.display,
            self.xkb_use_core_kbd,
            state_ref
        )
        return state.group

    def set_xkb_group(self, group_idx):
        res = self.libX11.XkbLockGroup(
            self.display,
            self.xkb_use_core_kbd,
            ctypes.c_uint(group_idx)
        )

    def toggle_layout(self, widget):
        self.set_xkb_group(
            int(not self.get_xkb_group())
        )
        self.update_icon()

    def update_icon(self):
        if self.get_xkb_group():
            self.icon.set_from_pixbuf(self.lang_foreign)
        else:
            self.icon.set_from_pixbuf(self.lang_native)

    def draw_langs(self):
        self.lang_foreign = self.draw_text(FOREIGN_LANG_TEXT)
        self.lang_native = self.draw_text(NATIVE_LANG_TEXT)

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
        pixbuf.get_from_drawable(
            pixmap, pixmap.get_colormap(),
            0, 0, 0, 0, ICON_SIZE, ICON_SIZE
        )
        pixbuf = pixbuf.add_alpha(True, 0x00, 0x00, 0x00)
        return pixbuf


if __name__ == '__main__':
    pygtk.require("2.0")
    gdk.threads_init()
    KeyboardIcon()
    gtk.main()
