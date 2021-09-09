import os
import sys

import cairo
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import GLib
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GdkPixbuf

from core import XKBMixin, EXIT_LABEL, ICON_SIZE, FONT_FACE, FONT_COLOR


FONT_SIZE = 15

SCALE_FACTOR = Gdk.Display.get_default().get_monitor(0).get_scale_factor()


class KeyboardIcon(XKBMixin):
    def __init__(self):
        # start class name with underscore so i3bar puts the icon first
        Gdk.set_program_class('_ input sources')
        self._init_menu()
        self._init_xcb_xkb()
        #self._init_xkb_groups()
        self._init_xkb_groups_simple()
        #self._draw_langs_icon_theme()
        self._draw_langs_renderer()
        self.icon = Gtk.StatusIcon()
        self.icon.connect('activate', self.activate_icon)
        self.icon.connect('popup-menu', self.popup_menu_icon)
        self._init_xkb_handler()
        self.update_icon()

    def _init_menu(self):
        self.menu = Gtk.Menu()
        close_item = Gtk.MenuItem(label=EXIT_LABEL)
        close_item.connect('activate', self._exit)
        self.menu.append(close_item)
        self.menu.show_all()

    def _draw_text(self, text):
        pix_size = ICON_SIZE * SCALE_FACTOR
        pixbuf = GdkPixbuf.Pixbuf.new(
            GdkPixbuf.Colorspace.RGB, True, 8, pix_size, pix_size
        )
        pixbuf.fill(0x00000000)
        surface = cairo.ImageSurface(
            cairo.FORMAT_RGB24,
            pixbuf.get_width(),
            pixbuf.get_height()
        )
        surface.flush()
        context = cairo.Context(surface)
        Gdk.cairo_set_source_pixbuf(context, pixbuf, 0, 0)
        context.paint()

        context.select_font_face(
            FONT_FACE,
            cairo.FONT_SLANT_NORMAL,
            cairo.FONT_WEIGHT_BOLD
        )
        context.set_font_size(FONT_SIZE * SCALE_FACTOR)
        e = context.text_extents(text)

        x_offset = (pix_size - e.width) / 2 - e.x_bearing;
        y_offset = (pix_size - e.height) / 2 - e.y_bearing;
        context.set_source_rgba(*FONT_COLOR)
        context.move_to(x_offset, y_offset)
        context.show_text(text)

        surface = context.get_target()
        pixbuf = Gdk.pixbuf_get_from_surface(
            surface, 0, 0, surface.get_width(), surface.get_height())

        return pixbuf

    def _get_theme_icon(self, icon_name):
        icon_theme = Gtk.IconTheme.get_default()
        return icon_theme.load_icon_for_scale(
            icon_name, ICON_SIZE, SCALE_FACTOR, 0)

    def popup_menu_icon(self, widget, event_button, event_time):
        self.menu.popup(None, None, widget.position_menu,
            widget, event_button, event_time)

    def activate_icon(self, widget):
        self.set_next_group()
        self.update_icon()

    def update_icon(self):
        group = self.get_xkb_group()
        self.icon.set_property('pixbuf', self.langs[group])

    def async_listener(self):
        while True:
            e = self.xcb.xcb_wait_for_event(self.conn)
            if e:
                self.xcb.free(e)
                GLib.idle_add(self.update_icon)

    def _exit(self, *args):
        self.xcb.xcb_disconnect(self.conn)
        self.loop.quit()
        return True

    def run(self):
        self.loop = GLib.MainLoop()
        self.loop.run()

if __name__ == '__main__':
    keyboard_icon = KeyboardIcon()
    keyboard_icon.run()
