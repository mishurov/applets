import re
import ctypes
import ctypes.util
import threading

ICON_SIZE = 22
EXIT_LABEL = 'Exit'
FONT_FACE = 'Ubuntu'
FONT_COLOR = (0.85, 0.85, 0.85, 1)

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


class XKBMixin(object):
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
            print('No XKEYBOARD extension')
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
            print('Extension in not supported by Server')
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
            print('Cant initialize event handler')
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

    def _init_xkb_groups(self):
        names = self._get_group_names()
        groups = self._parse_group_names(names)
        self.xkb_groups = groups

    def _init_xkb_groups_simple(self):
        groups = self._get_group_names_simple()
        self.xkb_groups = groups

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

    def _get_group_names_simple(self):
        return ['en', 'ru']

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

    def _draw_langs_renderer(self):
        langs = []
        for gt in self.xkb_groups:
            langs.append(
                self._draw_text(gt[:2])
            )
        self.langs = langs

    def _draw_langs_icon_theme(self):
        langs = []
        for gt in self.xkb_groups:
            icon_name = 'indicator-keyboard-' + gt[:2].capitalize()
            icon = self._get_theme_icon(icon_name)
            langs.append(icon)
        self.langs = langs
