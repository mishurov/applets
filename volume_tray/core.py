import time
import subprocess
import threading
from datetime import datetime, timedelta

# sudo apt install python3-dbus
import dbus
# pulsectl 21.9.1 / https://pypi.org/project/pulsectl/#files
from pulsectl import Pulse, PulseDisconnected

from x11_global_key_listener import X11GlobalKeyListener

APP_NAME = 'Volume Tray'

LABEL_MIXER = 'Pulseaudio...'
LABEL_EXIT = 'Exit'
CMD_MIXER = 'pavucontrol'
SCROLL_BY = 1
MEDIA_KEY_STEP = 5

VOLUME_WIDTH = 200
VOLUME_HEIGHT = 50

PROFILE_ANALOG = "output:analog-stereo+input:analog-stereo"
#PROFILE_ANALOG_PRO = "pro-audio"
PROFILE_HSP = "headset_head_unit"
PROFILE_HSP_CVSD = "headset-head-unit-cvsd"
PROFILE_HSP_MSBC = "headset-head-unit-msbc"
PROFILE_A2DP = "a2dp_sink"
#PROFILE_A2DP_SBC = "a2dp-sink-sbc"
PROFILE_A2DP_XQ = "a2dp-sink-sbc_xq"
PROFILE_A2DP_AAC = "a2dp-sink-aac"
PROFILE_A2DP_APTX = "a2dp-sink-aptx"
PROFILE_OFF = "off"

PROFILE_MAP = {
    PROFILE_ANALOG: "Analog Duplex",
    #PROFILE_ANALOG_PRO: "Analog Pro",
    PROFILE_A2DP: "A2DP SBC",
    #PROFILE_A2DP_SBC: "A2DP SBC",
    PROFILE_A2DP_XQ: "A2DP SBC XQ",
    PROFILE_A2DP_AAC: "A2DP AAC",
    PROFILE_A2DP_APTX: "A2DP AptX",
    PROFILE_HSP: "HFP CVSD",
    PROFILE_HSP_CVSD: "HFP CVSD",
    PROFILE_HSP_MSBC: "HFP mSBC"
}

PROF_ATTRS = list(PROFILE_MAP.values())


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

    def get_mute(self):
        return self.active_sink.mute

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
        self.pulse_d.event_mask_set('sink', 'card')

        # Glib.idle_add is to run the callback in the UI thread
        self.pulse_d.event_callback_set(self.callback())
        try:
            self.pulse_d.event_listen()
        except PulseDisconnected:
            time.sleep(3)
            self.pulse = Pulse('volume-control')
            self.async_listener()


class VolumeMixin(object):
    profile_items = []

    def init_dbus(self):
        bus = dbus.SystemBus()
        dev_obj = bus.get_object('org.bluez', '/')
        self.dev_interface = dbus.Interface(
            dev_obj,
            'org.freedesktop.DBus.ObjectManager')

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

    def update_icon(self, *args):
        if len(args):
            e = args[0]
            if e.facility == 'card':
                if e.t == 'remove':
                    self.mixer.introspect()
                    keys = list(self.mixer.all_profiles.keys())
                    if len(keys):
                        self.mixer.set_profile(keys[0])
                return

        if not self.is_menu_visible():
            self.mixer.get_active_sink()
        volume, mute = self.mixer.get_sink_volume_and_mute()
        icon_name = self.compute_icon_name(volume, mute)
        if icon_name != self.icon_name:
            self.icon_name = icon_name + '-panel'
            self.set_theme_icon(icon_name)

    def activate_mixer(self, *args):
        subprocess.Popen(
            [CMD_MIXER], shell=True, stdin=None,
            stdout=None, stderr=None, close_fds=True
        )
        return True

    def get_batt_levels(self):
        try:
            objects = self.dev_interface.GetManagedObjects()
        except dbus.exceptions.DBusException:
            self.init_dbus()
            objects = self.dev_interface.GetManagedObjects()

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
            self.destroy_item(m)
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
            self.insert_label_item(label, pos)
            pos += 1
            for i, profile in enumerate(device['profiles']):
                link = device['links'][i]
                self.insert_subaction_item(profile, link, pos)
                pos += 1


class MediaKeysMixin(object):
    VOLUME_UP_KEYSYM = 0x1008ff13
    VOLUME_DOWN_KEYSYM = 0x1008ff11
    VOLUME_MUTE_KEYSYM = 0x1008ff12
    KEYSYMS = [VOLUME_UP_KEYSYM, VOLUME_DOWN_KEYSYM, VOLUME_MUTE_KEYSYM]

    NOTIFY_EXPIRE_SEC = 3
    prev_notification = {
        'id': None,
        'time': None,
    }

    def on_media_key_pressed(self, args):
        keysym, event_type = args
        prev_mute = self.mixer.get_mute()
        if keysym == self.VOLUME_MUTE_KEYSYM:
            self.mixer.toggle_mute()
        elif not prev_mute and keysym == self.VOLUME_UP_KEYSYM:
            self.mixer.change_volume(MEDIA_KEY_STEP)
        elif not prev_mute and keysym == self.VOLUME_DOWN_KEYSYM:
            self.mixer.change_volume(-MEDIA_KEY_STEP)
        volume, mute = self.mixer.get_sink_volume_and_mute()
        icon_name = self.compute_icon_name(volume, mute)
        if keysym == self.VOLUME_MUTE_KEYSYM:
            summary = 'Mute' if mute else 'Unmute'
        elif prev_mute:
            summary = 'Muted'
        else:
            summary = 'Volume {}%'.format(int(volume))
        self.send_notification(summary)

    def send_notification(self, summary):
        now = datetime.now()
        prev_time = self.prev_notification['time']
        notification_id = 0
        if prev_time and (now - prev_time).total_seconds() < self.NOTIFY_EXPIRE_SEC:
            notification_id = self.prev_notification['id']
        new_id = self.notfy_intf.Notify('', notification_id, '', summary, '',
                                        [], {}, self.NOTIFY_EXPIRE_SEC * 1000)
        self.prev_notification['time'] = now
        self.prev_notification['id'] = new_id

    def init_notifications(self):
        item = 'org.freedesktop.Notifications'
        self.notfy_intf = dbus.Interface(
            dbus.SessionBus().get_object(item, '/' + item.replace('.', '/')),
            item
        )

    def init_keys(self):
        X11GlobalKeyListener(self.KEYSYMS, self.get_notify_callback())
        self.init_notifications()

