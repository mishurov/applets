import sys
import inspect
import subprocess
import threading

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')

from gi.repository import GObject
from gi.repository import GLib
from gi.repository import Gtk
from gi.repository import Gdk

# pulsectl 17.1.3
from pulsectl import Pulse


VOLUME_WIDTH = 200
VOLUME_HEIGHT = 50
SCROLL_BY = 1
MIXER_LABEL = "Pulseaudio..."
EXIT_LABEL = "Exit"
MIXER_CMD = "pavucontrol"
ICON_SIZE = 16


# Mixer

class PulseMixer(object):
    def __init__(self):
        self.pulse = Pulse('volume-control')

    def get_volume(self):
        ret = 0
        sinks = self.pulse.sink_list()
        if sinks:
            sink = sinks[0]
            ret = self.pulse.volume_get_all_chans(sink)
            ret = min(max(ret, 0), 1) * 100
        return ret

    def set_volume(self, value):
        sinks = self.pulse.sink_list()
        if sinks:
            sink = sinks[0]
            value /= 100.0
            self.pulse.volume_set_all_chans(sink, value)

    def change_volume(self, value):
        ret = 0
        sinks = self.pulse.sink_list()
        if sinks:
            sink = sinks[0]
            volume = self.pulse.volume_get_all_chans(sink)
            volume += value / 100.0
            volume = min(max(volume, 0), 1)
            self.pulse.volume_set_all_chans(sink, volume)

    def get_mute(self):
        ret = True
        sinks = self.pulse.sink_list()
        if sinks:
            sink = sinks[0]
            ret = sink.mute
        return ret

    def toggle_mute(self):
        sinks = self.pulse.sink_list()
        if sinks:
            sink = sinks[0]
            self.pulse.mute(sink, not sink.mute)

    def start_listener(self, func):
        self.callback = func
        self.thread = threading.Thread(
            target=self.async_listener
        )
        self.thread.daemon = True
        self.thread.start()

    def async_listener(self):
        self.pulse_d = Pulse('volume-daemon')
        self.pulse_d.event_mask_set('sink')

        # Glib.idle_add is to run the callback in the UI thread
        self.pulse_d.event_callback_set(
            lambda e: GLib.idle_add(self.callback)
        )
        self.pulse_d.event_listen()


# GUI

class SliderItem(Gtk.ImageMenuItem):
    def __init__(self, *args, **kwargs):
        Gtk.ImageMenuItem.__init__(self, *args, **kwargs)
        GObject.signal_new(
            'value-changed',
            self,
            GObject.SIGNAL_RUN_LAST,
            GObject.TYPE_PYOBJECT,
            (
                GObject.TYPE_PYOBJECT,
            ),
        )
        self.attach_slider()

    def create_slider(self):
        slider = Gtk.HScale()
        slider.set_inverted(False)
        slider.set_range(0, 100)
        slider.set_increments(1, 10)
        slider.set_digits(0)
        slider.set_size_request(VOLUME_WIDTH, VOLUME_HEIGHT)
        slider.connect('value-changed',
                       self.on_value_changed,
                       slider)
        return slider

    def attach_slider(self):
        slider = self.create_slider()
        self.add(slider)
        self.slider_grabbed = False
        self.connect('motion-notify-event',
                     self.motion_notify,
                     slider)
        self.connect('button-press-event',
                     self.button_press,
                     slider)
        self.connect('button-release-event',
                     self.button_release,
                     slider)
        self._slider = slider

    def button_press(self, parent, event, child):
        alloc = child.get_allocation()
        x, y = parent.translate_coordinates(child, event.x, event.y)
        if x > 0 and x < alloc.width and y > 0 and y < alloc.height:
            child.event(event)
        if not self.slider_grabbed:
            self.slider_grabbed = True
        return True

    def button_release(self, parent, event, child):
        self.slider_grabbed = False
        child.event(event)
        return True

    def motion_notify(self, parent, event, child):
        alloc = child.get_allocation()
        x, y = parent.translate_coordinates(child, event.x, event.y)
        if not self.slider_grabbed:
            event.x = x
            event.y = y
        if (self.slider_grabbed or
            x > 0 and x < alloc.width
            and y > 0 and y < alloc.height):
            child.event(event)
        return True

    def set_value(self, value):
        self._slider.set_value(value)

    def on_value_changed(self, widget, slider):
        self.emit('value-changed', slider)


class SoundIcon(object):
    def __init__(self):
        self.mixer = PulseMixer()
        self.mixer.start_listener(self.update_icon)
        self.create_icon()
        self.create_menu()
        self.run()

    def create_icon(self):
        self.icon_name = ''
        self.icon = Gtk.StatusIcon()
        self.icon_theme = Gtk.IconTheme.get_default()
        self.icon.connect('activate', self.activate)
        self.icon.connect('popup-menu', self.popup_menu)
        self.icon.connect('scroll-event', self.on_scroll)
        self.update_icon()

    def update_icon(self):
        volume = self.mixer.get_volume()
        mute = self.mixer.get_mute()
        if mute:
            icon_name = 'audio-volume-muted-panel'
        elif volume < 25:
            icon_name = 'audio-volume-low-panel'
        elif volume > 75:
            icon_name = 'audio-volume-high-panel'
        else:
            icon_name = 'audio-volume-medium-panel'
        if icon_name != self.icon_name:
            self.icon_name = icon_name
            icon = self.icon_theme.load_icon(icon_name, ICON_SIZE, 0)
            self.icon.set_from_pixbuf(icon)

    def create_mixer(self):
        item = Gtk.MenuItem(MIXER_LABEL)
        item.connect('activate', self.activate_mixer)
        return item

    def activate_mixer(self, *args):
        subprocess.Popen(
            [MIXER_CMD], shell=True, stdin=None,
            stdout=None, stderr=None, close_fds=True
        )
        return True

    def create_exit(self):
        item = Gtk.MenuItem(EXIT_LABEL)
        item.connect('activate', self.activate_exit)
        return item

    def activate_exit(self, *args):
        self.loop.quit()
        return True

    def create_menu(self):
        self.menu = Gtk.Menu()
        self.slider_item = SliderItem()
        self.slider_item.connect('value-changed', self.on_value_changed)
        mixer_item = self.create_mixer()
        exit_item = self.create_exit()
        self.menu.append(self.slider_item)
        self.menu.append(mixer_item)
        self.menu.append(exit_item)
        self.menu.show_all()

    def activate(self, widget):
        volume = self.mixer.get_volume()
        self.slider_item.set_value(volume)
        mute = self.mixer.get_mute()
        self.slider_item.set_sensitive(not mute)
        current_time = Gtk.get_current_event_time()
        self.menu.popup(None, None, None, None, 0, current_time)
        return True

    def popup_menu(self, widget, button, time):
        self.mixer.toggle_mute()
        return True

    def on_value_changed(self, widget, slider):
        value = int(slider.get_value())
        self.mixer.set_volume(value)
        return True

    def on_scroll(self, widget, event):
        drct = event.direction
        delta = event.delta_y
        if drct == Gdk.ScrollDirection.UP:
            self.mixer.change_volume(SCROLL_BY)
        elif drct == Gdk.ScrollDirection.DOWN:
            self.mixer.change_volume(-SCROLL_BY)
        return True

    def run(self):
        GObject.threads_init()
        self.loop = GLib.MainLoop()
        self.loop.run()


# Run application

if __name__ == '__main__':
    SoundIcon()


