import inspect
import subprocess

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')

from gi.repository import GObject
from gi.repository import GLib
from gi.repository import Gtk
from gi.repository import Gdk


VOLUME_WIDTH = 200
VOLUME_HEIGHT = 50
SCROLL_BY = 1
MIXER_LABEL = "Pulseaudio..."
EXIT_LABEL = "Exit"
MIXER_CMD = "pavucontrol"
POLL_TIMEOUT = 100
ICON_SIZE = 16

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
        self.mixer = SimplifiedPulseMixer()
        self.create_icon()
        self.create_menu()
        self.timeout_id = GObject.timeout_add(
            POLL_TIMEOUT, self.poll_data, None
        )
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

    def poll_data(self, user_data):
        self.mixer.refresh()
        self.update_icon()
        return True

    def activate(self, widget):
        self.mixer.refresh()
        volume = self.mixer.get_volume()
        self.slider_item.set_value(volume)
        mute = self.mixer.get_mute()
        self.slider_item.set_sensitive(not mute)
        current_time = Gtk.get_current_event_time()
        self.menu.popup(None, None, None, None, 0, current_time)
        return True

    def popup_menu(self, widget, button, time):
        self.mixer.refresh()
        self.mixer.toggle_mute()
        self.update_icon()
        return True

    def on_value_changed(self, widget, slider):
        value = int(slider.get_value())
        self.mixer.set_volume(value)
        self.update_icon()
        return True

    def on_scroll(self, widget, event):
        drct = event.direction
        delta = event.delta_y
        if drct == Gdk.ScrollDirection.UP:
            self.mixer.change_volume(SCROLL_BY)
        elif drct == Gdk.ScrollDirection.DOWN:
            self.mixer.change_volume(-SCROLL_BY)
        self.update_icon()
        return True

    def run(self):
        self.loop = GLib.MainLoop()
        self.loop.run()


class SimplifiedPulseMixer(object):
    def __init__(self):
        self.pulse = Pulse('pulsemixer', None)
        self.refresh()

    def refresh(self):
        sinks = self.pulse.sink_list()
        sink_inputs = self.pulse.sink_input_list()
        sources = self.pulse.source_list()
        source_outputs = self.pulse.source_output_list()
        server_info = self.pulse.get_server_info()
        index = [s.index for s in sinks if s.name == server_info.default_sink_name][0]
        streams = {}
        for i in source_outputs + sources + sink_inputs + sinks:
            streams[i.index] = i
        check_id = lambda x: x in streams or sys.exit('ERR: No such ID: ' + str(x))
        check_id(index)
        self.streams = streams
        self.index = index

    def get_volume(self):
        values = self.streams[self.index].volume.values
        return int(sum(values)/len(values))

    def get_mute(self):
        return self.streams[self.index].mute

    def toggle_mute(self):
        if self.streams[self.index].mute:
            self.pulse.unmute_stream(self.streams[self.index])
        else:
            self.pulse.mute_stream(self.streams[self.index])

    def set_volume(self, value):
        vol = self.streams[self.index].volume
        for i, _ in enumerate(vol.values):
            vol.values[i] = int(value)
        self.pulse.set_volume(self.streams[self.index], vol)

    def change_volume(self, value):
        vol = self.streams[self.index].volume
        for i, _ in enumerate(vol.values):
            vol.values[i] += int(value)
        self.pulse.set_volume(self.streams[self.index], vol)


# Pulse bindings, a modified code from
# https://github.com/GeorgeFilipkin/pulsemixer/


from ctypes import *

try:
    p = CDLL("libpulse.so.0")
except Exception as err:
    sys.exit(err)

PA_VOLUME_NORM = 65536
PA_CHANNELS_MAX = 32
PA_USEC_T = c_uint64


class PA_MAINLOOP(Structure):
    pass


class PA_MAINLOOP_API(Structure):
    pass


class PA_CONTEXT(Structure):
    pass


class PA_OPERATION(Structure):
    pass


class PA_PROPLIST(Structure):
    pass


class PA_SAMPLE_SPEC(Structure):
    _fields_ = [
        ("format", c_int),
        ("rate", c_uint32),
        ("channels", c_uint32)
    ]


class PA_CHANNEL_MAP(Structure):
    _fields_ = [
        ("channels", c_uint8),
        ("map", c_int * PA_CHANNELS_MAX)
    ]


class PA_CVOLUME(Structure):
    _fields_ = [
        ("channels", c_uint8),
        ("values", c_uint32 * PA_CHANNELS_MAX)
    ]


class PA_PORT_INFO(Structure):
    _fields_ = [
        ('name', c_char_p),
        ('description', c_char_p),
        ('priority', c_uint32),
    ]


class PA_SINK_INPUT_INFO(Structure):
    _fields_ = [
        ("index",           c_uint32),
        ("name",            c_char_p),
        ("owner_module",    c_uint32),
        ("client",          c_uint32),
        ("sink",            c_uint32),
        ("sample_spec",     PA_SAMPLE_SPEC),
        ("channel_map",     PA_CHANNEL_MAP),
        ("volume",          PA_CVOLUME),
        ("buffer_usec",     PA_USEC_T),
        ("sink_usec",       PA_USEC_T),
        ("resample_method", c_char_p),
        ("driver",          c_char_p),
        ("mute",            c_int)
    ]


class PA_SINK_INFO(Structure):
    _fields_ = [
        ("name",                c_char_p),
        ("index",               c_uint32),
        ("description",         c_char_p),
        ("sample_spec",         PA_SAMPLE_SPEC),
        ("channel_map",         PA_CHANNEL_MAP),
        ("owner_module",        c_uint32),
        ("volume",              PA_CVOLUME),
        ("mute",                c_int),
        ("monitor_source",      c_uint32),
        ("monitor_source_name", c_char_p),
        ("latency",             PA_USEC_T),
        ("driver",              c_char_p),
        ("flags",               c_int),
        ("proplist",            POINTER(PA_PROPLIST)),
        ("configured_latency",  PA_USEC_T),
        ('base_volume',         c_int),
        ('state',               c_int),
        ('n_volume_steps',      c_int),
        ('card',                c_uint32),
        ('n_ports',             c_uint32),
        ('ports',               POINTER(POINTER(PA_PORT_INFO))),
        ('active_port',         POINTER(PA_PORT_INFO))
    ]


class PA_SOURCE_OUTPUT_INFO(Structure):
    _fields_ = [
        ("index",           c_uint32),
        ("name",            c_char_p),
        ("owner_module",    c_uint32),
        ("client",          c_uint32),
        ("source",          c_uint32),
        ("sample_spec",     PA_SAMPLE_SPEC),
        ("channel_map",     PA_CHANNEL_MAP),
        ("buffer_usec",     PA_USEC_T),
        ("source_usec",     PA_USEC_T),
        ("resample_method", c_char_p),
        ("driver",          c_char_p),
        ("proplist",        POINTER(PA_PROPLIST)),
        ("corked",          c_int),
        ("volume",          PA_CVOLUME),
        ("mute",            c_int),
    ]


class PA_SOURCE_INFO(Structure):
    _fields_ = [
        ("name",                 c_char_p),
        ("index",                c_uint32),
        ("description",          c_char_p),
        ("sample_spec",          PA_SAMPLE_SPEC),
        ("channel_map",          PA_CHANNEL_MAP),
        ("owner_module",         c_uint32),
        ("volume",               PA_CVOLUME),
        ("mute",                 c_int),
        ("monitor_of_sink",      c_uint32),
        ("monitor_of_sink_name", c_char_p),
        ("latency",              PA_USEC_T),
        ("driver",               c_char_p),
        ("flags",                c_int),
        ("proplist",             POINTER(PA_PROPLIST)),
        ("configured_latency",   PA_USEC_T),
        ('base_volume',          c_int),
        ('state',                c_int),
        ('n_volume_steps',       c_int),
        ('card',                 c_uint32),
        ('n_ports',              c_uint32),
        ('ports',                POINTER(POINTER(PA_PORT_INFO))),
        ('active_port',          POINTER(PA_PORT_INFO))
    ]


class PA_CLIENT_INFO(Structure):
    _fields_ = [
        ("index",        c_uint32),
        ("name",         c_char_p),
        ("owner_module", c_uint32),
        ("driver",       c_char_p)
    ]


class PA_CARD_PROFILE_INFO(Structure):
    _fields_ = [
        ('name', c_char_p),
        ('description', c_char_p),
        ('n_sinks', c_uint32),
        ('n_sources', c_uint32),
        ('priority', c_uint32),
    ]


class PA_CARD_INFO(Structure):
    _fields_ = [
        ('index', c_uint32),
        ('name', c_char_p),
        ('owner_module', c_uint32),
        ('driver', c_char_p),
        ('n_profiles', c_uint32),
        ('profiles', POINTER(PA_CARD_PROFILE_INFO)),
        ('active_profile', POINTER(PA_CARD_PROFILE_INFO)),
        ('proplist', POINTER(PA_PROPLIST)),
    ]


class PA_SERVER_INFO(Structure):
    _fields_ = [
        ('user_name', c_char_p),
        ('host_name', c_char_p),
        ('server_version', c_char_p),
        ('server_name', c_char_p),
        ('sample_spec', PA_SAMPLE_SPEC),
        ('default_sink_name', c_char_p),
        ('default_source_name', c_char_p),
    ]

PA_STATE_CB_T = CFUNCTYPE(c_int, POINTER(PA_CONTEXT), c_void_p)

PA_SIGNAL_CB_T = CFUNCTYPE(c_void_p,
                           POINTER(PA_MAINLOOP_API),
                           POINTER(c_int),
                           c_int,
                           c_void_p)

PA_CLIENT_INFO_CB_T = CFUNCTYPE(c_void_p,
                                POINTER(PA_CONTEXT),
                                POINTER(PA_CLIENT_INFO),
                                c_int,
                                c_void_p)

PA_SINK_INPUT_INFO_CB_T = CFUNCTYPE(c_int,
                                    POINTER(PA_CONTEXT),
                                    POINTER(PA_SINK_INPUT_INFO),
                                    c_int,
                                    c_void_p)

PA_SINK_INFO_CB_T = CFUNCTYPE(c_int,
                              POINTER(PA_CONTEXT),
                              POINTER(PA_SINK_INFO),
                              c_int,
                              c_void_p)

PA_SOURCE_OUTPUT_INFO_CB_T = CFUNCTYPE(c_int,
                                       POINTER(PA_CONTEXT),
                                       POINTER(PA_SOURCE_OUTPUT_INFO),
                                       c_int,
                                       c_void_p)

PA_SOURCE_INFO_CB_T = CFUNCTYPE(c_int,
                                POINTER(PA_CONTEXT),
                                POINTER(PA_SOURCE_INFO),
                                c_int,
                                c_void_p)

PA_CONTEXT_SUCCESS_CB_T = CFUNCTYPE(c_void_p,
                                    POINTER(PA_CONTEXT),
                                    c_int,
                                    c_void_p)

PA_CARD_INFO_CB_T = CFUNCTYPE(None,
                              POINTER(PA_CONTEXT),
                              POINTER(PA_CARD_INFO),
                              c_int,
                              c_void_p)

PA_SERVER_INFO_CB_T = CFUNCTYPE(None,
                                POINTER(PA_CONTEXT),
                                POINTER(PA_SERVER_INFO),
                                c_void_p)

pa_mainloop_new = p.pa_mainloop_new
pa_mainloop_new.restype = POINTER(PA_MAINLOOP)
pa_mainloop_new.argtypes = []

pa_mainloop_get_api = p.pa_mainloop_get_api
pa_mainloop_get_api.restype = POINTER(PA_MAINLOOP_API)
pa_mainloop_get_api.argtypes = [POINTER(PA_MAINLOOP)]

pa_mainloop_run = p.pa_mainloop_run
pa_mainloop_run.restype = c_int
pa_mainloop_run.argtypes = [POINTER(PA_MAINLOOP), POINTER(c_int)]

pa_mainloop_iterate = p.pa_mainloop_iterate
pa_mainloop_iterate.restype = c_int
pa_mainloop_iterate.argtypes = [POINTER(PA_MAINLOOP), c_int, POINTER(c_int)]

pa_mainloop_free = p.pa_mainloop_free
pa_mainloop_free.restype = c_int
pa_mainloop_free.argtypes = [POINTER(PA_MAINLOOP)]

pa_signal_init = p.pa_signal_init
pa_signal_init.restype = c_int
pa_signal_init.argtypes = [POINTER(PA_MAINLOOP_API)]

pa_signal_new = p.pa_signal_new
pa_signal_new.restype = None
pa_signal_new.argtypes = [c_int, PA_SIGNAL_CB_T, POINTER(c_int)]

pa_context_errno = p.pa_context_errno
pa_context_errno.restype = c_int
pa_context_errno.argtypes = [POINTER(PA_CONTEXT)]

pa_context_new = p.pa_context_new
pa_context_new.restype = POINTER(PA_CONTEXT)
pa_context_new.argtypes = [POINTER(PA_MAINLOOP_API), c_char_p]

pa_context_set_state_callback = p.pa_context_set_state_callback
pa_context_set_state_callback.restype = None
pa_context_set_state_callback.argtypes = [
    POINTER(PA_CONTEXT),
    PA_STATE_CB_T,
    c_void_p
]

pa_context_connect = p.pa_context_connect
pa_context_connect.restype = c_int
pa_context_connect.argtypes = [
    POINTER(PA_CONTEXT),
    c_char_p,
    c_int,
    POINTER(c_int)
]

pa_context_get_state = p.pa_context_get_state
pa_context_get_state.restype = c_int
pa_context_get_state.argtypes = [POINTER(PA_CONTEXT)]

pa_context_disconnect = p.pa_context_disconnect
pa_context_disconnect.restype = c_int
pa_context_disconnect.argtypes = [POINTER(PA_CONTEXT)]

pa_proplist_gets = p.pa_proplist_gets
pa_proplist_gets.restype = c_char_p
pa_proplist_gets.argtypes = [POINTER(PA_PROPLIST), c_char_p]

pa_context_get_sink_input_info_list = p.pa_context_get_sink_input_info_list
pa_context_get_sink_input_info_list.restype = POINTER(c_int)
pa_context_get_sink_input_info_list.argtypes = [
    POINTER(PA_CONTEXT),
    PA_SINK_INPUT_INFO_CB_T,
    c_void_p
]

pa_context_get_sink_info_list = p.pa_context_get_sink_info_list
pa_context_get_sink_info_list.restype = POINTER(c_int)
pa_context_get_sink_info_list.argtypes = [
    POINTER(PA_CONTEXT),
    PA_SINK_INFO_CB_T,
    c_void_p
]

pa_context_set_sink_mute_by_index = p.pa_context_set_sink_mute_by_index
pa_context_set_sink_mute_by_index.restype = POINTER(c_int)
pa_context_set_sink_mute_by_index.argtypes = [
    POINTER(PA_CONTEXT),
    c_uint32,
    c_int,
    PA_CONTEXT_SUCCESS_CB_T,
    c_void_p
]

pa_context_suspend_sink_by_index = p.pa_context_suspend_sink_by_index
pa_context_suspend_sink_by_index.restype = POINTER(c_int)
pa_context_suspend_sink_by_index.argtypes = [
    POINTER(PA_CONTEXT),
    c_uint32,
    c_int,
    PA_CONTEXT_SUCCESS_CB_T,
    c_void_p
]

pa_context_set_sink_port_by_index = p.pa_context_set_sink_port_by_index
pa_context_set_sink_port_by_index.restype = POINTER(c_int)
pa_context_set_sink_port_by_index.argtypes = [
    POINTER(PA_CONTEXT),
    c_uint32,
    c_char_p,
    PA_CONTEXT_SUCCESS_CB_T,
    c_void_p
]

pa_context_set_sink_input_mute = p.pa_context_set_sink_input_mute
pa_context_set_sink_input_mute.restype = POINTER(c_int)
pa_context_set_sink_input_mute.argtypes = [
    POINTER(PA_CONTEXT),
    c_uint32,
    c_int,
    PA_CONTEXT_SUCCESS_CB_T,
    c_void_p
]

pa_context_set_sink_volume_by_index = p.pa_context_set_sink_volume_by_index
pa_context_set_sink_volume_by_index.restype = POINTER(c_int)
pa_context_set_sink_volume_by_index.argtypes = [
    POINTER(PA_CONTEXT),
    c_uint32,
    POINTER(PA_CVOLUME),
    PA_CONTEXT_SUCCESS_CB_T,
    c_void_p
]

pa_context_set_sink_input_volume = p.pa_context_set_sink_input_volume
pa_context_set_sink_input_volume.restype = POINTER(c_int)
pa_context_set_sink_input_volume.argtypes = [
    POINTER(PA_CONTEXT),
    c_uint32,
    POINTER(PA_CVOLUME),
    PA_CONTEXT_SUCCESS_CB_T,
    c_void_p
]

pa_context_move_sink_input_by_index = p.pa_context_move_sink_input_by_index
pa_context_move_sink_input_by_index.restype = POINTER(c_int)
pa_context_move_sink_input_by_index.argtypes = [
    POINTER(PA_CONTEXT),
    c_uint32,
    c_uint32,
    PA_CONTEXT_SUCCESS_CB_T,
    c_void_p
]

pa_context_set_default_sink = p.pa_context_set_default_sink
pa_context_set_default_sink.restype = POINTER(PA_OPERATION)
pa_context_set_default_sink.argtypes = [
    POINTER(PA_CONTEXT),
    c_char_p,
    PA_CONTEXT_SUCCESS_CB_T,
    c_void_p
]

pa_context_kill_sink_input = p.pa_context_kill_sink_input
pa_context_kill_sink_input.restype = POINTER(PA_OPERATION)
pa_context_kill_sink_input.argtypes = [
    POINTER(PA_CONTEXT),
    c_uint32,
    PA_CONTEXT_SUCCESS_CB_T,
    c_void_p
]

pa_context_kill_client = p.pa_context_kill_client
pa_context_kill_client.restype = POINTER(PA_OPERATION)
pa_context_kill_client.argtypes = [
    POINTER(PA_CONTEXT),
    c_uint32,
    PA_CONTEXT_SUCCESS_CB_T,
    c_void_p
]

pa_context_get_source_output_info = p.pa_context_get_source_output_info
pa_context_get_source_output_info.restype = POINTER(c_int)
pa_context_get_source_output_info.argtypes = [
    POINTER(PA_CONTEXT),
    c_uint32,
    PA_SOURCE_OUTPUT_INFO_CB_T,
    c_void_p
]

pa_context_get_source_output_info_list = p.pa_context_get_source_output_info_list
pa_context_get_source_output_info_list.restype = POINTER(c_int)
pa_context_get_source_output_info_list.argtypes = [
    POINTER(PA_CONTEXT),
    PA_SOURCE_OUTPUT_INFO_CB_T,
    c_void_p
]

pa_context_move_source_output_by_index = p.pa_context_move_source_output_by_index
pa_context_move_source_output_by_index.restype = POINTER(c_int)
pa_context_move_source_output_by_index.argtypes = [
    POINTER(PA_CONTEXT),
    c_uint32,
    c_uint32,
    PA_CONTEXT_SUCCESS_CB_T,
    c_void_p
]

pa_context_set_source_output_volume = p.pa_context_set_source_output_volume
pa_context_set_source_output_volume.restype = POINTER(c_int)
pa_context_set_source_output_volume.argtypes = [
    POINTER(PA_CONTEXT),
    c_uint32,
    POINTER(PA_CVOLUME),
    PA_CONTEXT_SUCCESS_CB_T,
    c_void_p
]

pa_context_set_source_output_mute = p.pa_context_set_source_output_mute
pa_context_set_source_output_mute.restype = POINTER(c_int)
pa_context_set_source_output_mute.argtypes = [
    POINTER(PA_CONTEXT),
    c_uint32,
    c_int,
    PA_CONTEXT_SUCCESS_CB_T,
    c_void_p
]

pa_context_get_source_info_by_index = p.pa_context_get_source_info_by_index
pa_context_get_source_info_by_index.restype = POINTER(c_int)
pa_context_get_source_info_by_index.argtypes = [
    POINTER(PA_CONTEXT),
    PA_SOURCE_INFO_CB_T,
    c_void_p
]

pa_context_get_source_info_list = p.pa_context_get_source_info_list
pa_context_get_source_info_list.restype = POINTER(c_int)
pa_context_get_source_info_list.argtypes = [
    POINTER(PA_CONTEXT),
    PA_SOURCE_INFO_CB_T,
    c_void_p
]

pa_context_set_source_volume_by_index = p.pa_context_set_source_volume_by_index
pa_context_set_source_volume_by_index.restype = POINTER(c_int)
pa_context_set_source_volume_by_index.argtypes = [
    POINTER(PA_CONTEXT),
    c_uint32,
    POINTER(PA_CVOLUME),
    PA_CONTEXT_SUCCESS_CB_T,
    c_void_p
]

pa_context_set_source_volume_by_index = p.pa_context_set_source_volume_by_index
pa_context_set_source_volume_by_index.restype = POINTER(c_int)
pa_context_set_source_volume_by_index.argtypes = [
    POINTER(PA_CONTEXT),
    c_uint32,
    POINTER(PA_CVOLUME),
    PA_CONTEXT_SUCCESS_CB_T,
    c_void_p
]

pa_context_set_source_mute_by_index = p.pa_context_set_source_mute_by_index
pa_context_set_source_mute_by_index.restype = POINTER(c_int)
pa_context_set_source_mute_by_index.argtypes = [
    POINTER(PA_CONTEXT),
    c_uint32,
    c_int,
    PA_CONTEXT_SUCCESS_CB_T,
    c_void_p
]

pa_context_suspend_source_by_index = p.pa_context_suspend_source_by_index
pa_context_suspend_source_by_index.restype = POINTER(c_int)
pa_context_suspend_source_by_index.argtypes = [
    POINTER(PA_CONTEXT),
    c_uint32,
    c_int,
    PA_CONTEXT_SUCCESS_CB_T,
    c_void_p
]

pa_context_set_source_port_by_index = p.pa_context_set_source_port_by_index
pa_context_set_source_port_by_index.restype = POINTER(c_int)
pa_context_set_source_port_by_index.argtypes = [
    POINTER(PA_CONTEXT),
    c_uint32,
    c_char_p,
    PA_CONTEXT_SUCCESS_CB_T,
    c_void_p
]

pa_context_set_default_source = p.pa_context_set_default_source
pa_context_set_default_source.restype = POINTER(PA_OPERATION)
pa_context_set_default_source.argtypes = [
    POINTER(PA_CONTEXT),
    c_char_p,
    PA_CONTEXT_SUCCESS_CB_T,
    c_void_p
]

pa_context_kill_source_output = p.pa_context_kill_source_output
pa_context_kill_source_output.restype = POINTER(PA_OPERATION)
pa_context_kill_source_output.argtypes = [
    POINTER(PA_CONTEXT),
    c_uint32,
    PA_CONTEXT_SUCCESS_CB_T,
    c_void_p
]

pa_context_get_client_info_list = p.pa_context_get_client_info_list
pa_context_get_client_info_list.restype = POINTER(c_int)
pa_context_get_client_info_list.argtypes = [
    POINTER(PA_CONTEXT),
    PA_CLIENT_INFO_CB_T,
    c_void_p
]

pa_context_get_card_info_by_index = p.pa_context_get_card_info_by_index
pa_context_get_card_info_by_index.restype = POINTER(PA_OPERATION)
pa_context_get_card_info_by_index.argtypes = [
    POINTER(PA_CONTEXT),
    c_uint32,
    PA_CARD_INFO_CB_T,
    c_void_p
]

pa_context_get_card_info_list = p.pa_context_get_card_info_list
pa_context_get_card_info_list.restype = POINTER(PA_OPERATION)
pa_context_get_card_info_list.argtypes = [
    POINTER(PA_CONTEXT),
    PA_CARD_INFO_CB_T,
    c_void_p
]

pa_context_set_card_profile_by_index = p.pa_context_set_card_profile_by_index
pa_context_set_card_profile_by_index.restype = POINTER(c_int)
pa_context_set_card_profile_by_index.argtypes = [
    POINTER(PA_CONTEXT),
    c_uint32,
    c_char_p,
    PA_CONTEXT_SUCCESS_CB_T,
    c_void_p
]

pa_context_get_server_info = p.pa_context_get_server_info
pa_context_get_server_info.restype = POINTER(PA_OPERATION)
pa_context_get_server_info.argtypes = [
    POINTER(PA_CONTEXT),
    PA_SERVER_INFO_CB_T,
    c_void_p
]

class PulsePort(object):

    def __init__(self, pa_port):
        self.name = pa_port.name
        self.description = pa_port.description
        self.priority = pa_port.priority

    def debug(self):
        pprint(vars(self))


class PulseServer(object):

    def __init__(self, pa_server):
        self.default_sink_name = pa_server.default_sink_name
        self.default_source_name = pa_server.default_source_name
        self.server_version = pa_server.server_version

    def debug(self):
        pprint(vars(self))


class PulseCardProfile(object):

    def __init__(self, pa_profile):
        self.name = pa_profile.name
        self.description = pa_profile.description

    def debug(self):
        pprint(vars(self))


class PulseCard(object):

    def __init__(self, pa_card):
        self.name = pa_card.name
        self.description = pa_proplist_gets(pa_card.proplist, b'device.description')
        self.index = pa_card.index
        self.driver = pa_card.driver
        self.owner_module = pa_card.owner_module
        self.n_profiles = pa_card.n_profiles
        self.profiles = [PulseCardProfile(pa_card.profiles[n]) for n in range(self.n_profiles)]
        self.active_profile = PulseCardProfile(pa_card.active_profile[0])
        self.volume = type('volume', (object,), {'channels': 1, 'values': [0, 0]})

    def debug(self):
        pprint(vars(self))

    def __str__(self):
        return "Card-ID: {}, Name: {}".format(self.index, self.name.decode())


class PulseClient(object):

    def __init__(self, pa_client):
        self.index = getattr(pa_client, "index", 0)
        self.name = getattr(pa_client, "name", pa_client)
        self.driver = getattr(pa_client, "driver", "default driver")
        self.owner_module = getattr(pa_client, "owner_module", -1)

    def debug(self):
        pprint(vars(self))

    def __str__(self):
        return "Client-name: {}".format(self.name.decode())


class Pulse(object):

    def __init__(self, client_name='libpulse', server=None):
        self.ret = None
        self.operation = None
        self.action_done = False
        self.data = []
        self.client_name = client_name.encode()

        self.pa_signal_cb = PA_SIGNAL_CB_T(self.signal_cb)
        self.pa_state_cb = PA_STATE_CB_T(self.state_cb)

        self.mainloop = pa_mainloop_new()
        self.mainloop_api = pa_mainloop_get_api(self.mainloop)

        assert pa_signal_init(self.mainloop_api) == 0, "pa_signal_init failed"

        pa_signal_new(2, self.pa_signal_cb, None)
        pa_signal_new(15, self.pa_signal_cb, None)

        self.context = pa_context_new(self.mainloop_api, self.client_name)
        pa_context_set_state_callback(self.context, self.pa_state_cb, None)

        if pa_context_connect(self.context, server, 0, None) < 0:
            self.disconnect()
            sys.exit("Failed to connect to pulseaudio daemon: Connection refused")
        self.iterate()

    def unmute_stream(self, obj):
        if type(obj) is PulseSinkInfo:
            self.sink_mute(obj.index, 0)
        elif type(obj) is PulseSinkInputInfo:
            self.sink_input_mute(obj.index, 0)
        elif type(obj) is PulseSourceInfo:
            self.source_mute(obj.index, 0)
        elif type(obj) is PulseSourceOutputInfo:
            self.source_output_mute(obj.index, 0)
        obj.mute = 0

    def mute_stream(self, obj):
        if type(obj) is PulseSinkInfo:
            self.sink_mute(obj.index, 1)
        elif type(obj) is PulseSinkInputInfo:
            self.sink_input_mute(obj.index, 1)
        elif type(obj) is PulseSourceInfo:
            self.source_mute(obj.index, 1)
        elif type(obj) is PulseSourceOutputInfo:
            self.source_output_mute(obj.index, 1)
        obj.mute = 1

    def set_volume(self, obj, volume):
        if type(obj) is PulseSinkInfo:
            self.set_sink_volume(obj.index, volume)
        elif type(obj) is PulseSinkInputInfo:
            self.set_sink_input_volume(obj.index, volume)
        elif type(obj) is PulseSourceInfo:
            self.set_source_volume(obj.index, volume)
        elif type(obj) is PulseSourceOutputInfo:
            self.set_source_output_volume(obj.index, volume)
        obj.volume = volume

    def change_volume_mono(self, obj, inc):
        obj.volume.values = [v + inc for v in obj.volume.values]
        self.set_volume(obj, obj.volume)

    def get_volume_mono(self, obj):
        return int(sum(obj.volume.values) / len(obj.volume.values))

    def fill_clients(self):
        if not self.data:
            return
        data, self.data = self.data, []
        clist = self.client_list()
        for d in data:
            for c in clist:
                if c.index == d.client_id:
                    d.client = c
                    break
        return data

    def signal_cb(self, api, e, sig, userdata):
        if sig == 2 or sig == 15:
            self.disconnect()
        return 0

    def state_cb(self, c, b):
        state = pa_context_get_state(c)
        if state == 4:
            self.complete_action()
        elif state == 5:
            sys.exit("Failed to connect to pulseaudio daemon: Connection refused")
        elif state == 6:
            sys.exit(pa_context_errno(c))
        return 0

    def _action_cb(func):
        def wrapper(self, c, info, eof, userdata):
            if eof:
                self.complete_action()
                return 0
            func(self, c, info, eof, userdata)
            return 0
        return wrapper

    @_action_cb
    def card_cb(self, c, card_info, eof, userdata):
        self.data.append(PulseCard(card_info[0]))

    @_action_cb
    def client_cb(self, c, client_info, eof, userdata):
        self.data.append(PulseClient(client_info[0]))

    @_action_cb
    def sink_input_cb(self, c, sink_input_info, eof, userdata):
        self.data.append(PulseSinkInputInfo(sink_input_info[0]))

    @_action_cb
    def sink_cb(self, c, sink_info, eof, userdata):
        self.data.append(PulseSinkInfo(sink_info[0]))

    @_action_cb
    def source_output_cb(self, c, source_output_info, eof, userdata):
        self.data.append(PulseSourceOutputInfo(source_output_info[0]))

    @_action_cb
    def source_cb(self, c, source_info, eof, userdata):
        self.data.append(PulseSourceInfo(source_info[0]))

    def server_cb(self, c, server_info, eof):
        self.data.append(PulseServer(server_info[0]))
        self.complete_action()

    def context_success(self, c, success, userdata):
        self.complete_action()
        return 0

    def complete_action(self):
        self.action_done = True

    def start_action(self):
        self.action_done = False

    def disconnect(self):
        pa_context_disconnect(self.context)
        pa_mainloop_free(self.mainloop)

    def sink_input_list(self):
        CB = PA_SINK_INPUT_INFO_CB_T(self.sink_input_cb)
        self.operation = pa_context_get_sink_input_info_list(self.context, CB, None)
        self.iterate()
        data, self.data = self.fill_clients(), []
        return data or []

    def sink_list(self):
        CB = PA_SINK_INFO_CB_T(self.sink_cb)
        self.operation = pa_context_get_sink_info_list(self.context, CB, None)
        self.iterate()
        data, self.data = self.data, []
        return data or []

    def source_output_list(self):
        CB = PA_SOURCE_OUTPUT_INFO_CB_T(self.source_output_cb)
        self.operation = pa_context_get_source_output_info_list(self.context, CB, None)
        self.iterate()
        data, self.data = self.fill_clients(), []
        return data or []

    def source_list(self):
        CB = PA_SOURCE_INFO_CB_T(self.source_cb)
        self.operation = pa_context_get_source_info_list(self.context, CB, None)
        self.iterate()
        data, self.data = self.data, []
        return data or []

    def get_server_info(self):
        CB = PA_SERVER_INFO_CB_T(self.server_cb)
        self.operation = pa_context_get_server_info(self.context, CB, None)
        self.iterate()
        data, self.data = self.data, []
        return data[0] or None

    def card_list(self):
        CB = PA_CARD_INFO_CB_T(self.card_cb)
        self.operation = pa_context_get_card_info_list(self.context, CB, None)
        self.iterate()
        data, self.data = self.data, []
        return data or []

    def client_list(self):
        CB = PA_CLIENT_INFO_CB_T(self.client_cb)
        self.operation = pa_context_get_client_info_list(self.context, CB, None)
        self.iterate()
        data, self.data = self.data, []
        return data or []

    def sink_input_mute(self, index, mute):
        CONTEXT = PA_CONTEXT_SUCCESS_CB_T(self.context_success)
        self.operation = pa_context_set_sink_input_mute(self.context, index, mute, CONTEXT, None)
        self.iterate()

    def sink_input_move(self, index, s_index):
        CONTEXT = PA_CONTEXT_SUCCESS_CB_T(self.context_success)
        self.operation = pa_context_move_sink_input_by_index(self.context, index, s_index, CONTEXT, None)
        self.iterate()

    def sink_mute(self, index, mute):
        CONTEXT = PA_CONTEXT_SUCCESS_CB_T(self.context_success)
        self.operation = pa_context_set_sink_mute_by_index(self.context, index, mute, CONTEXT, None)
        self.iterate()

    def set_sink_input_volume(self, index, vol):
        CONTEXT = PA_CONTEXT_SUCCESS_CB_T(self.context_success)
        self.operation = pa_context_set_sink_input_volume(self.context, index, vol.to_c(), CONTEXT, None)
        self.iterate()

    def set_sink_volume(self, index, vol):
        CONTEXT = PA_CONTEXT_SUCCESS_CB_T(self.context_success)
        self.operation = pa_context_set_sink_volume_by_index(self.context, index, vol.to_c(), CONTEXT, None)
        self.iterate()

    def sink_suspend(self, index, suspend):
        CONTEXT = PA_CONTEXT_SUCCESS_CB_T(self.context_success)
        self.operation = pa_context_suspend_sink_by_index(self.context, index, suspend, CONTEXT, None)
        self.iterate()

    def set_default_sink(self, name):
        CONTEXT = PA_CONTEXT_SUCCESS_CB_T(self.context_success)
        self.operation = pa_context_set_default_sink(self.context, name, CONTEXT, None)
        self.iterate()

    def kill_sink(self, index):
        CONTEXT = PA_CONTEXT_SUCCESS_CB_T(self.context_success)
        self.operation = pa_context_kill_sink_input(self.context, index, CONTEXT, None)
        self.iterate()

    def kill_client(self, index):
        CONTEXT = PA_CONTEXT_SUCCESS_CB_T(self.context_success)
        self.operation = pa_context_kill_client(self.context, index, CONTEXT, None)
        self.iterate()

    def set_sink_port(self, index, port):
        CONTEXT = PA_CONTEXT_SUCCESS_CB_T(self.context_success)
        self.operation = pa_context_set_sink_port_by_index(self.context, index, port, CONTEXT, None)
        self.iterate()

    def set_source_output_volume(self, index, vol):
        CONTEXT = PA_CONTEXT_SUCCESS_CB_T(self.context_success)
        self.operation = pa_context_set_source_output_volume(self.context, index, vol.to_c(), CONTEXT, None)
        self.iterate()

    def set_source_volume(self, index, vol):
        CONTEXT = PA_CONTEXT_SUCCESS_CB_T(self.context_success)
        self.operation = pa_context_set_source_volume_by_index(self.context, index, vol.to_c(), CONTEXT, None)
        self.iterate()

    def source_suspend(self, index, suspend):
        CONTEXT = PA_CONTEXT_SUCCESS_CB_T(self.context_success)
        self.operation = pa_context_suspend_source_by_index(self.context, index, suspend, CONTEXT, None)
        self.iterate()

    def set_default_source(self, name):
        CONTEXT = PA_CONTEXT_SUCCESS_CB_T(self.context_success)
        self.operation = pa_context_set_default_source(self.context, name, CONTEXT, None)
        self.iterate()

    def kill_source(self, index):
        CONTEXT = PA_CONTEXT_SUCCESS_CB_T(self.context_success)
        self.operation = pa_context_kill_source_output(self.context, index, CONTEXT, None)
        self.iterate()

    def set_source_port(self, index, port):
        CONTEXT = PA_CONTEXT_SUCCESS_CB_T(self.context_success)
        self.operation = pa_context_set_source_port_by_index(self.context, index, port, CONTEXT, None)
        self.iterate()

    def source_output_mute(self, index, mute):
        CONTEXT = PA_CONTEXT_SUCCESS_CB_T(self.context_success)
        self.operation = pa_context_set_source_output_mute(self.context, index, mute, CONTEXT, None)
        self.iterate()

    def source_mute(self, index, mute):
        CONTEXT = PA_CONTEXT_SUCCESS_CB_T(self.context_success)
        self.operation = pa_context_set_source_mute_by_index(self.context, index, mute, CONTEXT, None)
        self.iterate()

    def source_output_move(self, index, s_index):
        CONTEXT = PA_CONTEXT_SUCCESS_CB_T(self.context_success)
        self.operation = pa_context_move_source_output_by_index(self.context, index, s_index, CONTEXT, None)
        self.iterate()

    def set_card_profile(self, index, p_index):
        CONTEXT = PA_CONTEXT_SUCCESS_CB_T(self.context_success)
        self.operation = pa_context_set_card_profile_by_index(self.context, index, p_index, CONTEXT, None)
        self.iterate()

    def run(self):
        self.ret = pointer(c_int(0))
        pa_mainloop_run(self.mainloop, self.ret)

    def iterate(self, times=1, start=True):
        start and self.start_action()
        self.ret = pointer(c_int())
        pa_mainloop_iterate(self.mainloop, times, self.ret)
        while not self.action_done:
            pa_mainloop_iterate(self.mainloop, times, self.ret)


class PulseSink(object):

    def __init__(self, sink_info):
        self.index = sink_info.index
        self.name = sink_info.name
        self.mute = sink_info.mute
        self.volume = PulseVolume(sink_info.volume)

    def debug(self):
        pprint(vars(self))


class PulseSinkInfo(PulseSink):

    def __init__(self, pa_sink_info):
        PulseSink.__init__(self, pa_sink_info)
        self.description = pa_sink_info.description
        self.owner_module = pa_sink_info.owner_module
        self.driver = pa_sink_info.driver
        self.monitor_source = pa_sink_info.monitor_source
        self.monitor_source_name = pa_sink_info.monitor_source_name
        self.n_ports = pa_sink_info.n_ports
        self.ports = [PulsePort(pa_sink_info.ports[i].contents) for i in range(self.n_ports)]
        self.active_port = None
        if self.n_ports:
            self.active_port = PulsePort(pa_sink_info.active_port.contents)

    def __str__(self):
        return "ID: {}, Name: {}, Mute: {}, {}".format(
            self.index, self.description.decode(), self.mute, self.volume)


class PulseSinkInputInfo(PulseSink):

    def __init__(self, pa_sink_input_info):
        PulseSink.__init__(self, pa_sink_input_info)
        self.owner_module = pa_sink_input_info.owner_module
        self.client = PulseClient(pa_sink_input_info.name)
        self.client_id = pa_sink_input_info.client
        self.sink = self.owner = pa_sink_input_info.sink
        self.driver = pa_sink_input_info.driver

    def __str__(self):
        if self.client:
            return "ID: {}, Name: {}, Mute: {}, {}".format(
                self.index, self.client.name.decode(), self.mute, self.volume)
        return "ID: {}, Name: {}, Mute: {}".format(self.index, self.name.decode(), self.mute)


class PulseSource(object):

    def __init__(self, source_info):
        self.index = source_info.index
        self.name = source_info.name
        self.mute = source_info.mute
        self.volume = PulseVolume(source_info.volume)

    def debug(self):
        pprint(vars(self))


class PulseSourceInfo(PulseSource):

    def __init__(self, pa_source_info):
        PulseSource.__init__(self, pa_source_info)
        self.description = pa_source_info.description
        self.owner_module = pa_source_info.owner_module
        self.monitor_of_sink = pa_source_info.monitor_of_sink
        self.monitor_of_sink_name = pa_source_info.monitor_of_sink_name
        self.driver = pa_source_info.driver
        self.n_ports = pa_source_info.n_ports
        self.ports = [PulsePort(pa_source_info.ports[i].contents) for i in range(self.n_ports)]
        self.active_port = None
        if self.n_ports:
            self.active_port = PulsePort(pa_source_info.active_port.contents)

    def __str__(self):
        return "ID: {}, Name: {}, Mute: {}, {}".format(
            self.index, self.description.decode(), self.mute, self.volume)


class PulseSourceOutputInfo(PulseSource):

    def __init__(self, pa_source_output_info):
        PulseSource.__init__(self, pa_source_output_info)
        self.owner_module = pa_source_output_info.owner_module
        self.client = PulseClient(pa_source_output_info.name)
        self.client_id = pa_source_output_info.client
        self.source = self.owner = pa_source_output_info.source
        self.driver = pa_source_output_info.driver

    def __str__(self):
        if self.client:
            return "ID: {}, Name: {}, Mute: {}, {}".format(
                self.index, self.client.name.decode(), self.mute, self.volume)
        return "ID: {}, Name: {}, Mute: {}".format(self.index, self.name.decode(), self.mute)


class PulseVolume(object):

    def __init__(self, cvolume):
        self.channels = cvolume.channels
        self.values = [int((round(x * 100 / PA_VOLUME_NORM))) for x in cvolume.values[:self.channels]]

    def to_c(self):
        self.values = list(map(lambda x: max(min(x, 150), 0), self.values))
        cvolume = PA_CVOLUME()
        cvolume.channels = self.channels
        for x in range(self.channels):
            cvolume.values[x] = int(round((self.values[x] * PA_VOLUME_NORM) / 100))
        return cvolume

    def debug(self):
        pprint(vars(self))

    def __str__(self):
        return "Channels: {}, Volumes: {}".format(self.channels, [str(x) + "%" for x in self.values])


# Run application

if __name__ == '__main__':
    SoundIcon()


