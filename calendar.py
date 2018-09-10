import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')

from gi.repository import Gio
from gi.repository import Gdk
from gi.repository import Gtk


ICON_NAME = 'clipboard'
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
        window.set_title("GTKCalendar")
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

