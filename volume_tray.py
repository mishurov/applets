import subprocess
import threading

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')

from gi.repository import GObject
from gi.repository import GLib
from gi.repository import Gtk
from gi.repository import Gdk

# pulsectl 18.12.5
from pulsectl import Pulse


# relative units
VOLUME_WIDTH = 2.1
VOLUME_HEIGHT = 0.52
ICON_SIZE = 0.17

SCROLL_BY = 1

LABEL_MIXER = "Pulseaudio..."
LABEL_ANALOG = "Analog Stereo"
LABEL_HSP = "Headset Head Unit"
LABEL_A2DP = "High Fidelity Playback"
LABEL_EXIT = "Exit"

CMD_MIXER = "pavucontrol"

# Adjust sizes to absolute units
DPI = Gdk.Screen.get_default().get_resolution()
VOLUME_WIDTH *= DPI
VOLUME_HEIGHT *= DPI
ICON_SIZE *= DPI

PREFIX_ANALOG = "alsa"
PREFIX_BT = "bluez"
PROFILE_ANALOG = "output:analog-stereo+input:analog-stereo"
PROFILE_HSP = "headset_head_unit"
PROFILE_A2DP = "a2dp_sink"
PROFILE_OFF = "off"

PROFILE_MAP = {
    PROFILE_ANALOG: "analog",
    PROFILE_A2DP: "a2dp",
    PROFILE_HSP: "hsp",
}


# Mixer
class PulseMixer(object):
    profiles = {
        "analog": None,
        "a2dp": None,
        "hsp": None,
    }
    current_profile = None
    active_sink = None

    def __init__(self):
        self.pulse = Pulse('volume-control')

    def introspect(self):
        for k in self.profiles.keys():
           self.profiles[k] = None
        self.current_profile = None

        for k in self.profiles.keys():
            self.profiles[k] = None

        self.cards = self.pulse.card_list()
        self.get_active_sink()
        for card in self.cards:
            for profile in card.profile_list:
                if (card.profile_active.name == profile.name
                    and card.name[:4] == self.active_sink.name[:4]):
                    self.current_profile = profile
                key = PROFILE_MAP.get(profile.name, None)
                if key:
                    self.profiles[key] = profile

    def set_profile(self, key):
        # traverse through cards to determine which ones to turn on/off
        next_profile = self.profiles[key]
        next_card = None
        for card in self.cards:
            for profile in card.profile_list:
                if profile == next_profile:
                    next_card = card
                    break
        off_card = None
        off_profile = None
        for card in self.cards:
            if card == next_card:
                continue
            for profile in card.profile_list:
                if profile.name == PROFILE_OFF:
                    off_card = card
                    off_profile = profile
        if not next_card or not next_profile:
            return
        self.pulse.card_profile_set(next_card, next_profile)
        if off_card and off_profile:
            self.pulse.card_profile_set(off_card, off_profile)

    def get_active_sink(self):
        sink = None
        sink_inputs = self.pulse.sink_input_list()
        # check if a sink input is connected to a sink, if no, use default
        if len(sink_inputs):
            sink_id = sink_inputs[0].sink
            sinks = self.pulse.sink_list()
            sink = next((s for s in sinks if s.index == sink_id), None)
        if sink is None:
            info = self.pulse.server_info()
            sink = self.pulse.get_sink_by_name(info.default_sink_name)
        self.active_sink = sink
        return self.active_sink

    def get_sink_volume_and_mute(self):
        mute = True
        volume = 0
        if self.active_sink:
            volume = self.pulse.volume_get_all_chans(self.active_sink)
            volume = min(max(volume, 0), 1) * 100
            mute = self.active_sink.mute
        return volume, mute

    def set_volume(self, value):
        if self.active_sink:
            self.pulse.volume_set_all_chans(self.active_sink, value / 100.0)

    def change_volume(self, value):
        if self.active_sink:
            volume = self.pulse.volume_get_all_chans(self.active_sink)
            volume += value / 100.0
            volume = min(max(volume, 0), 1)
            self.pulse.volume_set_all_chans(self.active_sink, volume)

    def toggle_mute(self):
        sink = self.active_sink
        sink and self.pulse.mute(sink, not sink.mute)

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
            GObject.SignalFlags.RUN_LAST,
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
        if (self.slider_grabbed
            or x > 0 and x < alloc.width and y > 0 and y < alloc.height):
            child.event(event)
        return True

    def set_value(self, value):
        self._slider.set_value(value)

    def on_value_changed(self, widget, slider):
        self.emit('value-changed', slider)


class SoundIcon(object):
    def __init__(self):
        self.mixer = PulseMixer()
        self.create_icon()
        self.mixer.start_listener(self.update_icon)
        self.create_menu()
        self.update_icon()
        self.run()

    def create_icon(self):
        self.icon_name = ''
        self.icon = Gtk.StatusIcon()
        self.icon_theme = Gtk.IconTheme.get_default()
        self.icon.connect('activate', self.activate)
        self.icon.connect('popup-menu', self.popup_menu)
        self.icon.connect('scroll-event', self.on_scroll)

    def update_menu(self):
        self.mixer.introspect()
        ps = self.mixer.profiles
        attrs = ["analog", "hsp", "a2dp"]
        for a in attrs:
            item = getattr(self, a)
            visible = ps[a] is not None
            item.set_visible(visible)
            if visible:
                item.set_sensitive(ps[a] != self.mixer.current_profile)

    def update_icon(self):
        if not self.menu.get_visible():
            self.mixer.get_active_sink()
        volume, mute = self.mixer.get_sink_volume_and_mute()
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
            self.icon.set_property("pixbuf", icon)

    def create_mixer(self):
        item = Gtk.MenuItem(label=LABEL_MIXER)
        item.connect('activate', self.activate_mixer)
        return item

    def activate_mixer(self, *args):
        subprocess.Popen(
            [CMD_MIXER], shell=True, stdin=None,
            stdout=None, stderr=None, close_fds=True
        )
        return True

    def create_exit(self):
        item = Gtk.MenuItem(label=LABEL_EXIT)
        item.connect('activate', self.activate_exit)
        return item

    def activate_exit(self, *args):
        self.loop.quit()
        return True

    def create_profiles(self):
        self.analog = Gtk.MenuItem(label=LABEL_ANALOG)
        self.a2dp = Gtk.MenuItem(label=LABEL_A2DP)
        self.hsp = Gtk.MenuItem(label=LABEL_HSP)
        attrs = ["analog", "hsp", "a2dp"]
        for attr in attrs:
            item = getattr(self, attr)
            item.connect(
                'activate',
                lambda s, m: self.mixer.set_profile(m),
                attr
            )
        sep = Gtk.SeparatorMenuItem()
        self.menu.append(sep)
        self.menu.append(self.analog)
        self.menu.append(self.hsp)
        self.menu.append(self.a2dp)
        sep = Gtk.SeparatorMenuItem()
        self.menu.append(sep)

    def create_menu(self):
        self.menu = Gtk.Menu()
        self.slider_item = SliderItem()
        self.slider_item.connect('value-changed', self.on_value_changed)
        mixer_item = self.create_mixer()
        exit_item = self.create_exit()
        self.menu.append(self.slider_item)
        self.menu.append(mixer_item)
        self.create_profiles()
        self.menu.append(exit_item)
        self.menu.show_all()

    def activate(self, widget):
        self.update_menu()
        volume, mute = self.mixer.get_sink_volume_and_mute()
        self.slider_item.set_value(volume)
        self.slider_item.set_sensitive(not mute)
        current_time = Gtk.get_current_event_time()
        self.menu.popup(None, None, None, None, 0, current_time)
        return True

    def popup_menu(self, widget, button, time):
        self.mixer.toggle_mute()
        return True

    def on_value_changed(self, widget, slider):
        value = slider.get_value()
        self.mixer.set_volume(value)
        return True

    def on_scroll(self, widget, event):
        drct = event.direction
        if drct == Gdk.ScrollDirection.UP:
            self.mixer.change_volume(SCROLL_BY)
        elif drct == Gdk.ScrollDirection.DOWN:
            self.mixer.change_volume(-SCROLL_BY)
        return True

    def run(self):
        self.loop = GLib.MainLoop()
        self.loop.run()


# Run application
if __name__ == '__main__':
    SoundIcon()
