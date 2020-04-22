import re
import ctypes
import ctypes.util
import threading

import cairo

import gi
gi.require_version('Gtk', '3.0')

from gi.repository import GLib
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GdkPixbuf


FONT_SIZE = 0.2
ICON_SIZE = 0.29

X_OFFSET = 0.01
Y_OFFSET = 0.19

DPI = Gdk.Screen.get_default().get_resolution()
FONT_FACE = "Ubuntu"
FONT_SIZE = int(FONT_SIZE * DPI)
ICON_SIZE = int(ICON_SIZE * DPI)
X_OFFSET *= DPI
Y_OFFSET *= DPI
EXIT_LABEL = "Exit"

XKB_MAJOR_VER = 1
XKB_MINOR_VER = 0

xcb_keycode_t = ctypes.c_ubyte
xcb_atom_t = ctypes.c_uint
xcb_xkb_device_spec_t = ctypes.c_ushort

XCB_XKB_ID_USE_CORE_KBD = 256
use_core_kbd = xcb_xkb_device_spec_t(
    XCB_XKB_ID_USE_CORE_KBD
)


class xcb_connection_t(ctypes.Structure):
    pass


class xcb_generic_error_t(ctypes.Structure):
    _fields_ = [
        ('response_type', ctypes.c_ubyte),
        ('error_code', ctypes.c_ubyte),
        ('sequence', ctypes.c_ushort),
        ('resource_id', ctypes.c_uint),
        ('minor_code', ctypes.c_ushort),
        ('major_code', ctypes.c_ubyte),
        ('pad0', ctypes.c_ubyte),
        ('pad', ctypes.c_uint * 5),
        ('full_sequence', ctypes.c_uint),
    ]


class xcb_query_extension_reply_t(ctypes.Structure):
    _fields_ = [
        ('response_type', ctypes.c_ubyte),
        ('pad0', ctypes.c_ubyte),
        ('sequence', ctypes.c_ushort),
        ('length', ctypes.c_uint),
        ('present', ctypes.c_ubyte),
        ('major_opcode', ctypes.c_ubyte),
        ('first_event', ctypes.c_ubyte),
        ('first_error', ctypes.c_ubyte),
    ]


class xcb_xkb_use_extension_reply_t(ctypes.Structure):
    _fields_ = [
        ('response_type', ctypes.c_ubyte),
        ('supported', ctypes.c_ubyte),
        ('sequence', ctypes.c_ushort),
        ('length', ctypes.c_uint),
        ('serverMajor', ctypes.c_ushort),
        ('serverMinor', ctypes.c_ushort),
        ('pad0', ctypes.c_ubyte * 20),
    ]


xcb_atom_t = ctypes.c_uint


class xcb_xkb_key_name_t(ctypes.Structure):
    _fields_ = [
        ('name', ctypes.c_char * 4),
    ]


class xcb_xkb_key_alias_t(ctypes.Structure):
    _fields_ = [
        ('real', ctypes.c_char * 4),
        ('alias', ctypes.c_char * 4),
    ]


class xcb_xkb_get_names_value_list_t(ctypes.Structure):
    _fields_ = [
        ('keycodesName', xcb_atom_t),
        ('geometryName', xcb_atom_t),
        ('symbolsName', xcb_atom_t),
        ('physSymbolsName', xcb_atom_t),
        ('typesName', xcb_atom_t),
        ('compatName', xcb_atom_t),
        ('typeNames', ctypes.POINTER(xcb_atom_t)),
        ('nLevelsPerType', ctypes.POINTER(ctypes.c_ubyte)),
        ('alignment_pad', ctypes.POINTER(ctypes.c_ubyte)),
        ('ktLevelNames', ctypes.POINTER(xcb_atom_t)),
        ('indicatorNames', ctypes.POINTER(xcb_atom_t)),
        ('virtualModNames', ctypes.POINTER(xcb_atom_t)),
        ('groups', ctypes.POINTER(xcb_atom_t)),
        ('keyNames', ctypes.POINTER(xcb_xkb_key_name_t)),
        ('keyAliases', ctypes.POINTER(xcb_xkb_key_alias_t)),
        ('radioGroupNames', ctypes.POINTER(xcb_atom_t)),
    ]


class xcb_xkb_get_names_reply_t(ctypes.Structure):
    _fields_ = [
        ('response_type', ctypes.c_ubyte),
        ('deviceID', ctypes.c_ubyte),
        ('sequence', ctypes.c_ushort),
        ('length', ctypes.c_uint),
        ('which', ctypes.c_uint),
        ('minKeyCode', xcb_keycode_t),
        ('maxKeyCode', xcb_keycode_t),
        ('nTypes', ctypes.c_ubyte),
        ('groupNames', ctypes.c_ubyte),
        ('virtualMods', ctypes.c_ushort),
        ('firstKey', xcb_keycode_t),
        ('nKeys', ctypes.c_ubyte),
        ('indicators', ctypes.c_uint),
        ('nRadioGroups', ctypes.c_ubyte),
        ('nKeyAliases', ctypes.c_ubyte),
        ('nKTLevels', ctypes.c_ushort),
        ('pad0', ctypes.c_ubyte * 4),
    ]


class xcb_xkb_get_state_reply_t(ctypes.Structure):
    _fields_ = [
        ('response_type', ctypes.c_ubyte),
        ('deviceID', ctypes.c_ubyte),
        ('sequence', ctypes.c_ushort),
        ('length', ctypes.c_uint),
        ('mods', ctypes.c_ubyte),
        ('baseMods', ctypes.c_ubyte),
        ('latchedMods', ctypes.c_ubyte),
        ('lockedMods', ctypes.c_ubyte),
        ('group', ctypes.c_ubyte),
        ('lockedGroup', ctypes.c_ubyte),
        ('baseGroup', ctypes.c_short),
        ('latchedGroup', ctypes.c_short),
        ('compatState', ctypes.c_ubyte),
        ('grabMods', ctypes.c_ubyte),
        ('compatGrabMods', ctypes.c_ubyte),
        ('lookup_mods', ctypes.c_ubyte),
        ('compatLookupMods', ctypes.c_ubyte),
        ('pad0', ctypes.c_ubyte),
        ('ptrBtnState', ctypes.c_ushort),
        ('pad1', ctypes.c_ubyte * 6),
    ]


class xcb_generic_event_t(ctypes.Structure):
    _fields_ = [
        ('response_type', ctypes.c_ubyte),
        ('pad0', ctypes.c_ubyte),
        ('sequence', ctypes.c_ushort),
        ('pad', ctypes.c_uint * 7),
        ('full_sequence', ctypes.c_uint),
    ]


class KeyboardIcon(object):
    def __init__(self):
        self._init_menu()
        self._init_xcb_xkb()
        self._init_xkb_groups()
        #self._draw_langs()
        self._draw_langs_pango()
        self.icon = Gtk.StatusIcon()
        self.icon.connect('activate', self.activate_icon)
        self.icon.connect('popup-menu', self.popup_menu_icon)
        self._init_xkb_handler()
        self.update_icon()

    def _exit(self, *args):
        self.xcb.xcb_disconnect(self.conn)
        self.loop.quit()
        return True

    def _init_xcb_xkb(self):
        xcb_location = ctypes.util.find_library('xcb')
        self.xcb = ctypes.CDLL(xcb_location)
        self.xcb.xcb_connect.restype = ctypes.POINTER(
            xcb_connection_t
        )
        self.conn = self.xcb.xcb_connect(None, None)
        self.xcb.xcb_request_check.restype = ctypes.POINTER(
            xcb_generic_error_t
        )
        ext_name = b'XKEYBOARD'
        cookie = self.xcb.xcb_query_extension(
            self.conn,
            ctypes.c_ushort(9),
            ctypes.c_char_p(ext_name)
        )
        self.xcb.xcb_query_extension_reply.restype = ctypes.POINTER(
            xcb_query_extension_reply_t
        )
        reply = self.xcb.xcb_query_extension_reply(
            self.conn, cookie, None
        )
        present = reply.contents.present
        self.xcb.free(reply)
        if not present:
            print("No XKEYBOARD extension")
            self._exit()

        xcb_xkb_location = ctypes.util.find_library('xcb-xkb')
        self.xcb_xkb = ctypes.CDLL(xcb_xkb_location)

        self.xcb_xkb.xcb_xkb_use_extension_reply.restype = ctypes.POINTER(
            xcb_xkb_use_extension_reply_t
        )

        cookie = self.xcb_xkb.xcb_xkb_use_extension(
            self.conn, XKB_MAJOR_VER, XKB_MINOR_VER
        )
        reply = self.xcb_xkb.xcb_xkb_use_extension_reply(
            self.conn, cookie, None
        )
        supported = reply.contents.supported
        self.xcb_xkb.free(reply)
        if not supported:
            print("Extension in not supported by Server")
            self._exit()

    def _init_xkb_handler(self):
        XCB_XKB_EVENT_TYPE_EXTENSION_DEVICE_NOTIFY = 2048
        affectWhich = ctypes.c_ushort(
            XCB_XKB_EVENT_TYPE_EXTENSION_DEVICE_NOTIFY
        )
        affectMap = ctypes.c_ushort(0)
        cookie = self.xcb_xkb.xcb_xkb_select_events_checked(
            self.conn,
            use_core_kbd,
            affectWhich,
            ctypes.c_ushort(0),
            affectWhich,
            affectMap,
            affectMap,
            None
        )
        err = self.xcb.xcb_request_check(self.conn, cookie)
        if err:
            self.xcb_xkb.free(err)
            print("Cant initialize event handler")
            self._exit()

        self.xcb.xcb_wait_for_event.restype = ctypes.POINTER(
            xcb_generic_event_t
        )
        self.xcb.xcb_flush(self.conn)

        # start blocking listening in another thread
        self.thread = threading.Thread(
            target=self.async_listener
        )
        self.thread.daemon = True
        self.thread.start()

    def async_listener(self):
        while True:
            e = self.xcb.xcb_wait_for_event(self.conn)
            if e:
                self.xcb.free(e)
                GLib.idle_add(self.update_icon)

    def _init_xkb_groups(self):
        #names = self._get_group_names()
        #groups = self._parse_group_names(names)
        groups = self._get_group_names_simple()
        self.xkb_groups = groups

    def _get_group_names_simple(self):
        return ["en", "ru"]

    def _get_group_names(self):
        XCB_XKB_NAME_DETAIL_SYMBOLS = 4
        which = ctypes.c_uint(XCB_XKB_NAME_DETAIL_SYMBOLS)
        cookie = self.xcb_xkb.xcb_xkb_get_names(
            self.conn, use_core_kbd, which
        )
        self.xcb_xkb.xcb_xkb_get_names_reply.restype = ctypes.POINTER(
            xcb_xkb_get_names_reply_t
        )
        reply = self.xcb_xkb.xcb_xkb_get_names_reply(
            self.conn, cookie, None
        )
        buf = self.xcb_xkb.xcb_xkb_get_names_value_list(reply)
        content = reply.contents
        name_list = xcb_xkb_get_names_value_list_t()

        self.xcb_xkb.xcb_xkb_get_names_value_list_unpack(
            buf, content.nTypes, content.indicators,
            content.virtualMods, content.groupNames, content.nKeys,
            content.nKeyAliases, content.nRadioGroups, content.which,
            ctypes.byref(name_list))
        self.xcb_xkb.free(reply)

        cookie = self.xcb.xcb_get_atom_name(
            self.conn, name_list.symbolsName
        )
        reply = self.xcb.xcb_get_atom_name_reply(
            self.conn, cookie, None
        )

        self.xcb.xcb_get_atom_name_name.restype = ctypes.c_char_p
        atom_name = self.xcb.xcb_get_atom_name_name(reply)
        self.xcb.free(reply)
        return atom_name

    def _parse_group_names(self, atom_name):
        kb_groups = []
        kbs = re.sub(r'^pc[+_]', '', atom_name.decode("utf-8"))
        kbs = re.findall(r'[a-z0-9():\-]+(?:_[0-9])?', kbs)
        kb_groups.append(kbs[0])
        postfix = r'[_:][0-9]$'
        for k in kbs:
            if re.search(postfix, k):
                kb_groups.append(re.sub(postfix, '', k))
        if len(kb_groups) > 4:
            kb_groups = kb_groups[:4]
        return kb_groups

    def get_xkb_group(self):
        cookie = self.xcb_xkb.xcb_xkb_get_state(
            self.conn, use_core_kbd
        )
        self.xcb_xkb.xcb_xkb_get_state_reply.restype = ctypes.POINTER(
            xcb_xkb_get_state_reply_t
        )
        reply = self.xcb_xkb.xcb_xkb_get_state_reply(
            self.conn, cookie, None
        )
        group = reply.contents.group
        self.xcb_xkb.free(reply)
        return group

    def activate_icon(self, widget):
        self.set_next_group()
        self.update_icon()

    def set_next_group(self):
        group = self.get_xkb_group()
        groups_len = len(self.xkb_groups)
        next_group = group + 1
        if next_group >= groups_len:
            next_group = 0
        self.set_xkb_group(next_group)

    def set_xkb_group(self, group):
        self.xcb_xkb.xcb_xkb_latch_lock_state(
            self.conn, use_core_kbd, 0, 0, True, group, 0, 0, 0
        )

    def update_icon(self):
        group = self.get_xkb_group()
        self.icon.set_property("pixbuf", self.langs[group])

    def popup_menu_icon(self, widget, event_button, event_time):
        self.menu.popup(None, None, None, None, 0, event_time)

    def _init_menu(self):
        self.menu = Gtk.Menu()
        close_item = Gtk.MenuItem(label=EXIT_LABEL)
        close_item.connect("activate", self._exit)
        self.menu.append(close_item)
        self.menu.show_all()

    def _draw_langs(self):
        icon_theme = Gtk.IconTheme.get_default()
        langs = []
        for gt in self.xkb_groups:
           icon_name = "indicator-keyboard-" + gt[:2].capitalize()
           icon = icon_theme.load_icon(icon_name, ICON_SIZE, 0)
           langs.append(icon)
        self.langs = langs

    def _draw_langs_pango(self):
        langs = []
        for gt in self.xkb_groups:
            langs.append(
                self._draw_text(gt[:2])
            )
        self.langs = langs

    def _draw_text(self, text):
        pixbuf = GdkPixbuf.Pixbuf.new(
            GdkPixbuf.Colorspace.RGB, True, 8, ICON_SIZE, ICON_SIZE
        )
        pixbuf.fill(0xff000000)
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
        context.set_source_rgba(0.9, 0.9, 0.9, 1)
        context.set_font_size(FONT_SIZE)
        context.move_to(X_OFFSET, Y_OFFSET)
        context.show_text(text)

        # get the resulting pixbuf
        surface = context.get_target()
        pixbuf = Gdk.pixbuf_get_from_surface(
            surface, 0, 0, surface.get_width(), surface.get_height())

        return pixbuf

    def run(self):
        self.loop = GLib.MainLoop()
        self.loop.run()


if __name__ == '__main__':
    keyboard_icon = KeyboardIcon()
    keyboard_icon.run()
