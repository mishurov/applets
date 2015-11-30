#!/usr/bin/python2

# Copyright (c) 2015 Alexander Mishurov. All rights reserved.
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


import pygtk
import gtk
import wnck


FEH_ICON_PATH="/home/username/.config/feh/icon.png"


def maximus(window, changed_mask, new_state):
    mask_h = wnck.WINDOW_STATE_MAXIMIZED_HORIZONTALLY
    mask_v = wnck.WINDOW_STATE_MAXIMIZED_VERTICALLY
    mask_all = mask_h | mask_v

    if changed_mask in (mask_all, mask_h, mask_v):
        gdk_window = gtk.gdk.window_foreign_new(
            window.get_xid()
        )
        # decorations = gdk_window.get_decorations()
        if new_state == changed_mask:
            gdk_window.set_decorations(0)
        elif new_state == 0:
            gdk_window.set_decorations(gtk.gdk.DECOR_ALL)


def set_feh_icon(window):
    pixbuf = gtk.gdk.pixbuf_new_from_file(FEH_ICON_PATH)
    gdk_window = gtk.gdk.window_foreign_new(
        window.get_xid()
    )
    gdk_window.set_icon_list([pixbuf])


def on_window_opened(screen, window):
    window.connect('state-changed', maximus)
    if window.get_class_group().get_res_class() == "feh":
        set_feh_icon(window)

if __name__ == "__main__":
    pygtk.require('2.0')
    screen = wnck.screen_get_default()
    screen.connect("window_opened", on_window_opened)
    gtk.main()

