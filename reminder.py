#!/usr/bin/env python3
from datetime import datetime, timedelta

import gi
gi.require_version('Gdk', '3.0')
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib


ICON_SIZE = 0.15
ICON_NAME = 'alarm-clock'
ICON_NAME_URGENT = 'alarm-clock-urgent'
POPUP_TEXT = 'Alarm'
BUTTON_LABEL = 'Start'
EXIT_LABEL = 'Quit'


class Reminder(object):
    start = None
    timedelta = None
    discount = {'hours': 0, 'minutes': 0, 'seconds': 0}

    def __init__(self):
        self.setup_icon()
        self.setup_menu()
        self.setup_popup()
        self.setup_window()
        self.update_clock()
        self.run()

    def on_button_clicked(self, *args):
        self.window.hide()
        h = self.spins[0].get_value_as_int()
        m = self.spins[1].get_value_as_int()
        s = self.spins[2].get_value_as_int()
        self.timedelta = timedelta(hours=h, minutes=m, seconds=s)
        self.start = datetime.now()

    def setup_window(self):
        self.window = Gtk.Window()
        self.window.set_type_hint(Gdk.WindowTypeHint.DIALOG)
        self.window.set_position(Gtk.WindowPosition.CENTER)
        self.window.set_title("Reminder")

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
            label = Gtk.Label(label)
            label.set_margin_left(5)
            label.set_margin_right(5)
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
        self.window.show_all()

    def on_window_close(self, *args):
        self.window.hide()
        return True

    def setup_icon(self):
        self.icon = Gtk.StatusIcon()
        icon_theme = Gtk.IconTheme.get_default()
        self.gicon = icon_theme.load_icon(ICON_NAME, ICON_SIZE, 0)
        self.gicon_urgent = icon_theme.load_icon(ICON_NAME_URGENT, ICON_SIZE, 0)
        self.icon.set_property("gicon", self.gicon)
        self.icon.connect('activate', self.activate_menu)

    def update_clock(self):
        markup = '<span font="25">{hours:2d}:{minutes:02d}:{seconds:02d}</span>'
        self.clock.set_markup(markup.format(**self.discount))

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
        label.set_markup("<span font='50'>%s</span>" % POPUP_TEXT)
        self.popup.set_border_width(15)
        self.popup.add(label)

    def on_popup_release(self, *args):
        self.popup.hide()

    def activate_menu(self, widget):
        if self.icon.get_property("gicon") == self.gicon_urgent:
            self.icon.set_property("gicon", self.gicon)
        self.update_clock()
        current_time = Gtk.get_current_event_time()
        self.menu.popup(None, None, None, None, 0, current_time)

    def activate_window(self, *args):
        self.window.show_all()

    def activate_exit(self, *args):
        self.loop.quit()
        return True

    def idle(self):
        if self.start is not None and self.timedelta is not None:
            td = datetime.now() - self.start
            if self.timedelta > td:
                td = self.timedelta - td
                self.discount.update({
                    'hours': int(td.seconds / 3600) % 24,
                    'minutes': int(td.seconds / 60) % 60,
                    'seconds': td.seconds % 60,
                })
            else:
                self.start = None
                self.timedelta = None
                self.discount.update({'hours': 0, 'minutes': 0, 'seconds': 0})
                self.icon.set_property("gicon", self.gicon_urgent)
                self.popup.show_all()

            if self.menu.get_visible():
                self.update_clock()

        return True

    def run(self):
        GLib.timeout_add_seconds(1, self.idle)
        self.loop = GLib.MainLoop()
        self.loop.run()


if __name__ == '__main__':
    Reminder()
