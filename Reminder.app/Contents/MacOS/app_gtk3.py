#!/usr/bin/env python3
import os

import gi
gi.require_version('Gdk', '3.0')
gi.require_version('Gtk', '3.0')
from gi.repository import Gio, Gtk, Gdk, GLib, GdkPixbuf

from core import (
    TimerMixin,
    ALERT_TEXT,
    BUTTON_LABEL,
    EXIT_LABEL,
    ALARM_PATH,
    ALARM_URGENT_PATH,
    ALARM_ACTIVE_PATH,
    SPINBOX_WINDOW_TITLE,
)


ICON_SIZE = 24
SCALE_FACTOR = Gdk.Display.get_default().get_monitor(0).get_scale_factor()


class Reminder(TimerMixin):
    def __init__(self):
        Gdk.set_program_class(SPINBOX_WINDOW_TITLE)
        self.setup_icon()
        self.setup_menu()
        self.setup_popup()
        self.setup_window()
        self.init_saved_alarm()
        self.idle()
        self.run()

    def on_button_clicked(self, *args):
        self.window.hide()
        h = self.spins[0].get_value_as_int()
        m = self.spins[1].get_value_as_int()
        s = self.spins[2].get_value_as_int()
        self.start_timer(h, m, s)

    def setup_window(self):
        self.window = Gtk.Window()
        self.window.set_type_hint(Gdk.WindowTypeHint.DIALOG)
        self.window.set_position(Gtk.WindowPosition.CENTER)
        self.window.set_title(SPINBOX_WINDOW_TITLE)

        vbox = Gtk.Box()
        vbox.set_orientation(Gtk.Orientation.VERTICAL)

        hbox = Gtk.Box()
        hbox.set_orientation(Gtk.Orientation.HORIZONTAL)

        self.spins = []

        for label in ['h', 'm', 's']:
            spin = Gtk.SpinButton()
            spin.set_numeric(True)
            spin.set_snap_to_ticks(True)
            spin.set_wrap(True)
            spin.set_increments(1, 0)
            spin.set_range(0, 23 if label == 'h' else 59)

            self.spins.append(spin)
            label = Gtk.Label.new(label)
            label.set_margin_start(5)
            label.set_margin_end(5)
            hbox.add(label)
            hbox.add(spin)

        button = Gtk.Button.new_with_label(BUTTON_LABEL)
        button.connect('clicked', self.on_button_clicked)

        vbox.add(hbox)
        vbox.add(button)

        self.window.add(vbox)
        self.window.set_border_width(15)
        self.window.connect('delete-event', self.on_window_close)
        self.window.connect('destroy-event', self.on_window_close)

    def on_window_close(self, *args):
        self.window.hide()
        return True

    def get_scaled_icon(self, path):
        # make QT and GTK icon sizes identical
        scale_factor = 0.92
        size = ICON_SIZE * SCALE_FACTOR
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
            path, size, size, True
        )
        wo = pixbuf.get_width()
        ho = pixbuf.get_height()
        bg = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, True, 8, wo, ho)
        ws = wo * scale_factor
        hs = ho * scale_factor
        ox = (wo - ws) / 2
        oy = (ho - hs) / 2
        pixbuf = pixbuf.scale_simple(ws, ws, GdkPixbuf.InterpType.BILINEAR)
        pixbuf.copy_area(0, 0, ws, ws, bg, ox, oy)
        return bg

    def setup_icon(self):
        self.icon = Gtk.StatusIcon()
        icon_theme = Gtk.IconTheme.get_default()
        self.icon_normal = self.get_scaled_icon(ALARM_PATH)
        self.icon_urgent = self.get_scaled_icon(ALARM_URGENT_PATH)
        self.icon_active = self.get_scaled_icon(ALARM_ACTIVE_PATH)
        self.set_icon(self.icon_normal)
        self.icon.connect('activate', self.activate_menu)

    def setup_menu(self):
        self.menu = Gtk.Menu()

        item = Gtk.ImageMenuItem()
        self.clock = Gtk.Label()
        self.clock.set_margin_top(12)
        self.clock.set_margin_bottom(15)
        item.add(self.clock)
        item.connect('activate', self.activate_window)

        separator = Gtk.SeparatorMenuItem()
        exit = Gtk.ImageMenuItem()
        label = Gtk.Label.new(EXIT_LABEL)
        label.set_halign(Gtk.Align.END)
        exit.add(label)
        exit.connect('activate', self.activate_exit)

        self.menu.append(item)
        self.menu.append(separator)
        self.menu.append(exit)
        self.menu.show_all()

    def setup_popup(self):
        self.popup = Gtk.Window.new(Gtk.WindowType.POPUP)
        self.popup.set_position(Gtk.WindowPosition.CENTER)
        self.popup.connect('button-release-event', self.on_popup_release)
        label = Gtk.Label()
        label.set_markup("<span font='55'>%s</span>" % ALERT_TEXT)
        self.popup.set_border_width(15)
        self.popup.add(label)

    def on_popup_release(self, *args):
        self.popup.hide()

    def activate_menu(self, widget):
        if self.icon.get_property("gicon") == self.icon_urgent:
            self.clear_alarm()
            self.set_icon(self.icon_normal)
        self.update_clock()
        current_time = Gtk.get_current_event_time()
        self.menu.popup(None, None, self.icon.position_menu,
            self.icon, 0, current_time)

    def activate_window(self, *args):
        self.window.show_all()

    def activate_exit(self, *args):
        self.loop.quit()
        return True

    def set_icon(self, icon):
        self.icon.set_property("gicon", icon)

    def update_clock_text(self, text):
        t_span = '<span font="25">{}</span>'
        self.clock.set_markup(t_span.format(text))

    def show_popup(self):
        self.popup.show_all()

    def is_menu_visible(self):
        return self.menu.get_visible()

    def run(self):
        GLib.timeout_add_seconds(1, self.idle)
        self.loop = GLib.MainLoop()
        self.loop.run()


if __name__ == '__main__':
    Reminder()
