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


from gi.repository import Gio
from gi.repository import Gdk
from gi.repository import Gtk


ICON_NAME = 'gtk-help'
ICON_SIZE = 16


class Calendar(Gtk.Application):
    def __init__(self):
        Gtk.Application.__init__(
            self, 
            flags=Gio.ApplicationFlags.FLAGS_NONE
        )

    def do_activate(self):
        window = Gtk.Window(Gtk.WindowType.TOPLEVEL)
        window.set_type_hint(Gdk.WindowTypeHint.DIALOG)
        window.set_wmclass("py_gi_gtk_calendar", "PythonGIGTKCalendar")
        window.set_title("Calendar")
        icon_theme = Gtk.IconTheme.get_default()
        if icon_theme.has_icon(ICON_NAME):
            pixbuf = icon_theme.load_icon(ICON_NAME , ICON_SIZE, 0)
            window.set_default_icon(pixbuf)
        cal = Gtk.Calendar()
        window.add(cal)
        window.show_all()
        self.add_window(window)

    def do_startup(self):
        Gtk.Application.do_startup(self)

    def do_shutdown(self):
        Gtk.Application.do_shutdown(self)

    def on_quit(self, widget, data):
        self.quit()


if __name__ == '__main__':
    calendar = Calendar()
    calendar.run(None)

