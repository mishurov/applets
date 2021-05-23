import time
import subprocess
import threading
import dbus  # python3-dbus

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('Keybinder', '3.0')  # gir1.2-keybinder-3.0
gi.require_version('Notify', '0.7')  # gir1.2-notify-0.7

from gi.repository import GObject
from gi.repository import GLib
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import Keybinder
from gi.repository import Notify

# pulsectl 20.5.1
from pulsectl import Pulse, PulseDisconnected


# relative units
VOLUME_WIDTH = 2.1
VOLUME_HEIGHT = 0.52

ICON_SIZE = 24

SCROLL_BY = 1
MEDIA_KEY_STEP = 5

LABEL_MIXER = "Pulseaudio..."
LABEL_EXIT = "Exit"

CMD_MIXER = "pavucontrol"

# Adjust sizes to absolute units
DPI = Gdk.Screen.get_default().get_resolution()
VOLUME_WIDTH *= DPI
VOLUME_HEIGHT *= DPI

PROFILE_ANALOG = "output:analog-stereo+input:analog-stereo"
#PROFILE_ANALOG_PRO = "pro-audio"
PROFILE_HSP = "headset_head_unit"
PROFILE_HSP_CVSD = "headset-head-unit-cvsd"
PROFILE_HSP_MSBC = "headset-head-unit-msbc"
PROFILE_A2DP = "a2dp_sink"
PROFILE_A2DP_XQ = "a2dp-sink-sbc_xq"
PROFILE_A2DP_AAC = "a2dp-sink-aac"
PROFILE_A2DP_APTX = "a2dp-sink-aptx"
PROFILE_OFF = "off"

PROFILE_MAP = {
    PROFILE_ANALOG: "Analog Duplex",
    #PROFILE_ANALOG_PRO: "Analog Pro",
    PROFILE_A2DP: "A2DP SBC",
    PROFILE_A2DP_XQ: "A2DP SBC XQ",
    PROFILE_A2DP_AAC: "A2DP AAC",
    PROFILE_A2DP_APTX: "A2DP AptX",
    PROFILE_HSP: "HFP CVSD",
    PROFILE_HSP_CVSD: "HFP CVSD",
    PROFILE_HSP_MSBC: "HFP mSBC"
}

PROF_ATTRS = list(PROFILE_MAP.values())

bus = dbus.SystemBus()
dev_obj = bus.get_object('org.bluez', '/')
dev_interface = dbus.Interface(dev_obj, 'org.freedesktop.DBus.ObjectManager')


# Mixer
class PulseMixer(object):
    all_profiles = {}
    current_profile = None
    active_sink = None

    def __init__(self):
        self.pulse = Pulse('volume-control')

    def introspect(self):
        self.all_profiles = {}
        self.current_profile = None
        self.cards = self.pulse.card_list()

        for card in self.cards:
            description = card.proplist.get('device.description')
            for profile in card.profile_list:
                #print(profile)
                prof_key = PROFILE_MAP.get(profile.name, None)
                if prof_key and profile.available:
                    key = description + '__' + prof_key
                    self.all_profiles[key] = [card, profile]
                    if (card.profile_active.name == profile.name
                        and self.active_sink
                        and card.name[:4] == self.active_sink.name[:4]):
                        self.current_profile = key

    def set_profile(self, key):
        prof = self.all_profiles[key]
        if not prof:
            return
        card, profile = prof
        for c, p in self.all_profiles.values():
            if c != card:
                self.pulse.card_profile_set(c, PROFILE_OFF)
            elif p == profile:
                self.pulse.card_profile_set(card, profile)

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
            if info.default_sink_name == '@DEFAULT_SINK@':
                return None
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
        try:
            self.pulse_d.event_listen()
        except PulseDisconnected:
            time.sleep(3)
            self.pulse = Pulse('volume-control')
            self.async_listener()


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
    profile_items = []

    def __init__(self):
        self.mixer = PulseMixer()
        self.create_icon()
        self.mixer.start_listener(self.update_icon)
        self.create_menu()
        self.update_icon()
        self.init_keys()
        self.create_styles()
        self.run()

    def create_styles(self):
        css = (
            '.strong > * { font-weight: bold; }'
            '.subtitle > *:disabled { font-weight: bold; font-size: small; }'
            '.submenu { padding-left: 12px; }'
        )
        style_provider = Gtk.CssProvider()
        style_provider.load_from_data(css.encode('utf-8'))
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            style_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def change_vol_notify(self, key):
        if key == 'XF86AudioMute':
            self.mixer.toggle_mute()
        elif key == 'XF86AudioRaiseVolume':
            self.mixer.change_volume(MEDIA_KEY_STEP)
        elif key == 'XF86AudioLowerVolume':
            self.mixer.change_volume(-MEDIA_KEY_STEP)
        volume, mute = self.mixer.get_sink_volume_and_mute()
        icon_name = self.compute_icon_name(volume, mute)
        if key == 'XF86AudioMute':
            summary = 'Mute' if mute else 'Unmute'
        else:
            summary = 'Volume {}%'.format(int(volume))
        self.notification.update(summary, '', icon_name)
        self.notification.show()

    def init_keys(self):
        Keybinder.init()
        Notify.init('Volume Tray')
        self.notification = Notify.Notification.new('', '', 'volume')
        Keybinder.bind('XF86AudioRaiseVolume', self.change_vol_notify)
        Keybinder.bind('XF86AudioLowerVolume', self.change_vol_notify)
        Keybinder.bind('XF86AudioMute', self.change_vol_notify)

    def compute_icon_name(self, volume, mute):
        if mute:
            icon_name = 'audio-volume-muted'
        elif volume < 25:
            icon_name = 'audio-volume-low'
        elif volume > 75:
            icon_name = 'audio-volume-high'
        else:
            icon_name = 'audio-volume-medium'
        return icon_name

    def create_icon(self):
        self.icon_name = ''
        self.icon = Gtk.StatusIcon()
        self.icon_theme = Gtk.IconTheme.get_default()
        self.icon.connect('activate', self.activate)
        self.icon.connect('popup-menu', self.popup_menu)
        self.icon.connect('scroll-event', self.on_scroll)

    def get_batt_levels(self):
        objects = dev_interface.GetManagedObjects()
        ret = {}
        for path, interfaces in objects.items():
            if "org.bluez.Battery1" in interfaces:
                dev = interfaces['org.bluez.Device1']
                if not dev['Paired']:
                    continue
                name = dev['Name']
                batt = interfaces['org.bluez.Battery1']
                perc_bytes = bytes([batt['Percentage']])
                perc_int = int.from_bytes(perc_bytes, 'little')
                ret[name] = ' ∙ ' + str(perc_int) + '%'
        return ret

    def update_menu(self):
        self.mixer.introspect()

        for m in self.profile_items:
            m.destroy()
        self.profile_items = []

        devices = {}
        for k, v in self.mixer.all_profiles.items():
            dev, prof = k.split('__')
            key = dev.replace(' ', '_')
            device = devices.get(key)
            if not device:
                devices[key] = {
                    'name': dev,
                    'profiles': [prof],
                    'links': [k]
                }
            else:
                device['profiles'].append(prof)
                device['links'].append(k)

        pos = 3
        batt_levels = self.get_batt_levels()

        for device in devices.values():
            name = device['name']
            perc = batt_levels.get(name, '')
            label = name + perc
            item = Gtk.MenuItem(label=label)
            style_context = item.get_style_context()
            style_context.add_class('subtitle')
            self.menu.insert(item, pos)
            pos += 1
            item.set_sensitive(False)
            item.set_visible(True)
            self.profile_items.append(item)
            for i, profile in enumerate(device['profiles']):
                link = device['links'][i]
                item = Gtk.MenuItem(label=profile)
                style_context = item.get_style_context()
                style_context.add_class('submenu')
                item.connect(
                    'activate',
                    lambda s, m: self.mixer.set_profile(m),
                    link
                )
                self.menu.insert(item, pos)
                pos += 1
                item.set_visible(True)
                if link == self.mixer.current_profile:
                    item.set_sensitive(False)
                self.profile_items.append(item)

    def update_icon(self):
        if not self.menu.get_visible():
            self.mixer.get_active_sink()
        volume, mute = self.mixer.get_sink_volume_and_mute()
        icon_name = self.compute_icon_name(volume, mute)
        if icon_name != self.icon_name:
            self.icon_name = icon_name + '-panel'
            gicon = self.icon_theme.load_icon(icon_name, ICON_SIZE, 0)
            self.icon.set_property("gicon", gicon)

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

    def create_menu(self):
        self.menu = Gtk.Menu()
        self.slider_item = SliderItem()
        self.slider_item.connect('value-changed', self.on_value_changed)
        mixer_item = self.create_mixer()
        exit_item = self.create_exit()
        for item in [mixer_item, exit_item]:
            style_context = item.get_style_context()
            style_context.add_class('strong')
        self.menu.append(self.slider_item)
        self.menu.append(mixer_item)
        self.menu.append(Gtk.SeparatorMenuItem())
        self.menu.append(Gtk.SeparatorMenuItem())
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
