#!/usr/bin/env python2
# -*- coding: utf-8 -*-


# Copyright (c) Alexander Mishurov. All rights reserved.
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following
# conditions are met:

# 1. Redistributions of source code must retain the above
# copyright notice, this list of conditions and the following disclaimer

# 2. Redistributions in binary form must reproduce the above
# copyright notice, this list of conditions and the following disclaimer
# in the documentation and/or other materials provided with
# the distribution.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,
# STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED
# OF THE POSSIBILITY OF SUCH DAMAGE.


import signal
import subprocess
import ctypes
import ctypes.util

# commands to run on right mouse click
RMB_TOP_CMD = ["echo", "top"]
RMB_RIGHT_CMD =  ["echo", "right"]
RMB_LEFT_CMD =  ["echo", "left"]

# width (height) of clickable area
TOP_THRESHOLD = 2
RIGHT_THRESHOLD = 2
LEFT_THRESHOLD = 2

xcb_button_t = ctypes.c_ubyte
xcb_timestamp_t = ctypes.c_uint
xcb_window_t  = ctypes.c_uint
xcb_colormap_t = ctypes.c_uint
xcb_visualid_t = ctypes.c_uint


class xcb_connection_t(ctypes.Structure):
    pass


class xcb_generic_error_t(ctypes.Structure):
    _fields_ = [
        ('response_type', ctypes.c_ubyte),
        ('error_code', ctypes.c_ubyte),
        ('sequence',  ctypes.c_ushort),
        ('resource_id',  ctypes.c_uint),
        ('minor_code',  ctypes.c_ushort),
        ('major_code', ctypes.c_ubyte),
        ('pad0', ctypes.c_ubyte),
        ('pad',  ctypes.c_uint*5),
        ('full_sequence',  ctypes.c_uint),
    ]


class xcb_query_extension_reply_t(ctypes.Structure):
    _fields_ = [
        ('response_type', ctypes.c_ubyte),
        ('pad0', ctypes.c_ubyte),
        ('sequence',  ctypes.c_ushort),
        ('length',  ctypes.c_uint),
        ('present', ctypes.c_ubyte),
        ('major_opcode', ctypes.c_ubyte),
        ('first_event', ctypes.c_ubyte),
        ('first_error', ctypes.c_ubyte),
    ]


xcb_window_t  = ctypes.c_uint

xcb_colormap_t = ctypes.c_uint

xcb_visualid_t = ctypes.c_uint


class xcb_screen_t(ctypes.Structure):
    _fields_ = [
        ('root', xcb_window_t),
        ('default_colormap', xcb_colormap_t),
        ('white_pixel', ctypes.c_uint),
        ('black_pixel', ctypes.c_uint),
        ('current_input_masks', ctypes.c_uint),
        ('width_in_pixels', ctypes.c_ushort),
        ('height_in_pixels', ctypes.c_ushort),
        ('width_in_millimeters', ctypes.c_ushort),
        ('height_in_millimeters', ctypes.c_ushort),
        ('min_installed_maps', ctypes.c_ushort),
        ('max_installed_maps', ctypes.c_ushort),
        ('root_visual', xcb_visualid_t),
        ('backing_stores', ctypes.c_ubyte),
        ('save_unders', ctypes.c_ubyte),
        ('root_depth', ctypes.c_ubyte),
        ('allowed_depths_len', ctypes.c_ubyte),
    ]


class xcb_screen_t(ctypes.Structure):
    _fields_ = [
        ('root', xcb_window_t),
        ('default_colormap', xcb_colormap_t),
        ('white_pixel', ctypes.c_uint),
        ('black_pixel', ctypes.c_uint),
        ('current_input_masks', ctypes.c_uint),
        ('width_in_pixels', ctypes.c_ushort),
        ('height_in_pixels', ctypes.c_ushort),
        ('width_in_millimeters', ctypes.c_ushort),
        ('height_in_millimeters', ctypes.c_ushort),
        ('min_installed_maps', ctypes.c_ushort),
        ('max_installed_maps', ctypes.c_ushort),
        ('root_visual', xcb_visualid_t),
        ('backing_stores', ctypes.c_ubyte),
        ('save_unders', ctypes.c_ubyte),
        ('root_depth', ctypes.c_ubyte),
        ('allowed_depths_len', ctypes.c_ubyte),
    ]


class xcb_screen_iterator_t(ctypes.Structure):
    _fields_ = [
        ('data',  ctypes.POINTER(xcb_screen_t)),
        ('rem', ctypes.c_int),
        ('index', ctypes.c_int),
    ]

class xcb_generic_reply_t(ctypes.Structure):
    _fields_ = [
        ('response_type', ctypes.c_ubyte),
        ('pad0', ctypes.c_ubyte),
        ('sequence', ctypes.c_ushort),
        ('length', ctypes.c_uint),
    ]

xcb_button_t = ctypes.c_ubyte

xcb_timestamp_t = ctypes.c_uint

class xcb_button_event_t(ctypes.Structure):
    _fields_ = [
        ('response_type', ctypes.c_ubyte),
        ('detail', xcb_button_t),
        ('sequence', ctypes.c_ushort),
        ('time', xcb_timestamp_t),
        ('root', xcb_window_t),
        ('event', xcb_window_t),
        ('child', xcb_window_t),
        ('root_x', ctypes.c_ushort),
        ('root_y', ctypes.c_ushort),
        ('event_x', ctypes.c_ushort),
        ('event_y', ctypes.c_ushort),
        ('state', ctypes.c_ushort),
        ('same_screen', ctypes.c_ubyte),
        ('pad0', ctypes.c_ubyte),
    ]

class xcb_record_range_8_t(ctypes.Structure):
    _fields_ = [
        ('first', ctypes.c_ubyte),
        ('last', ctypes.c_ubyte),
    ]

class xcb_record_range_16_t(ctypes.Structure):
    _fields_ = [
        ('first', ctypes.c_ushort),
        ('last', ctypes.c_ushort),
    ]

class xcb_record_ext_range_t(ctypes.Structure):
    _fields_ = [
        ('major', xcb_record_range_8_t),
        ('minor', xcb_record_range_16_t),
    ]

class xcb_record_range_t(ctypes.Structure):
    _fields_ = [
        ('core_requests', xcb_record_range_8_t),
        ('core_replies', xcb_record_range_8_t),
        ('ext_requests', xcb_record_ext_range_t),
        ('ext_replies', xcb_record_ext_range_t),
        ('delivered_events', xcb_record_range_8_t),
        ('device_events', xcb_record_range_8_t),
        ('errors', xcb_record_range_8_t),
        ('client_started', ctypes.c_ubyte),
        ('client_died', ctypes.c_ubyte),
    ]


xcb_record_element_header_t = ctypes.c_ubyte


class xcb_record_enable_context_reply_t(ctypes.Structure):
    _fields_ = [
        ('response_type', ctypes.c_ubyte),
        ('category', ctypes.c_ubyte),
        ('sequence', ctypes.c_ushort),
        ('length', ctypes.c_uint),
        ('element_header', xcb_record_element_header_t),
        ('client_swapped', ctypes.c_ubyte),
        ('pad0 ', ctypes.c_ubyte*2),
        ('xid_base', ctypes.c_uint),
        ('server_time', ctypes.c_uint),
        ('rec_sequence_num', ctypes.c_uint),
        ('pad1 ', ctypes.c_ubyte*8),
]

xcb_record_client_spec_t = ctypes.c_uint

XCB_RECORD_CS_ALL_CLIENTS = 3
XCB_BUTTON_PRESS = 4
XCB_BUTTON_RELEASE = 5
XRecordFromServer = 0


class HotCornersApp(object):
    def __init__(self):
        signal.signal(signal.SIGINT, self._exit)
        self._init_xcb_record()
        self._get_screen_data()
        self._init_record_handler()
        self.poll()

    def _exit(self, *args):
        self.xcb.xcb_disconnect(self.conn)
        exit()

    def get_area(self, x, y):
        w = self.screen_width
        h = self.screen_height
        if y <= TOP_THRESHOLD and x > LEFT_THRESHOLD \
           and x < w - RIGHT_THRESHOLD:
           return "top"
        elif x >= w - RIGHT_THRESHOLD and y > TOP_THRESHOLD:
           return "right"
        elif x <= LEFT_THRESHOLD and y > TOP_THRESHOLD:
           return "left"
        return None

    def handle_rbm(self, event):
        area = self.get_area(event.root_x, event.root_y)
        if RMB_TOP_CMD and area == "top":
            subprocess.call(RMB_TOP_CMD)
        elif RMB_RIGHT_CMD and area == "right":
            subprocess.call(RMB_RIGHT_CMD)
        elif RMB_LEFT_CMD and area == "left":
            subprocess.call(RMB_LEFT_CMD)

    def event_callback(self, reply, data):
        response = ctypes.cast(
            data,
            ctypes.POINTER(xcb_generic_reply_t)
        ).contents
        if response.response_type == XCB_BUTTON_RELEASE \
           and response.pad0 == 3:
            button_event = ctypes.cast(
                data,
                ctypes.POINTER(xcb_button_event_t)
            ).contents
            self.handle_rbm(button_event)

    def poll(self):
        while True:
            reply = self.xcb_record.xcb_record_enable_context_reply(
                self.conn, self.record_cookie, None
            )
            if not reply:
                break

            if reply.contents.client_swapped:
                self.xcb_record.free(reply)
                print "Swapped bytes not implemented"
                self._exit()

            if reply.contents.category == XRecordFromServer:
                data = self.xcb_record.xcb_record_enable_context_data(
                    reply
                )
                self.event_callback(reply, data)
                self.xcb_record.free(reply)

    def _init_xcb_record(self):
        xcb_location = ctypes.util.find_library('xcb')
        self.xcb = ctypes.CDLL(xcb_location)
        self.xcb.xcb_connect.restype = ctypes.POINTER(
            xcb_connection_t
        )
        self.conn = self.xcb.xcb_connect(None, None)
        self.xcb.xcb_request_check.restype = ctypes.POINTER(
            xcb_generic_error_t
        )
        cookie = self.xcb.xcb_query_extension(
            self.conn,
            ctypes.c_ushort(6),
            ctypes.c_char_p("RECORD")
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
            print "No RECORD extension"
            self._exit()
        xcb_record_location = ctypes.util.find_library('xcb-record')
        self.xcb_record = ctypes.CDLL(xcb_record_location)

    def _get_screen_data(self):
        setup = self.xcb.xcb_get_setup(self.conn)
        self.xcb.xcb_setup_roots_iterator.restype \
        = xcb_screen_iterator_t
        screen_iterator = self.xcb.xcb_setup_roots_iterator(setup)

        self.screen_width \
        = screen_iterator.data.contents.width_in_pixels
        self.screen_height \
        = screen_iterator.data.contents.height_in_pixels

    def _init_record_handler(self):
        device_events = xcb_record_range_8_t(
            first=XCB_BUTTON_RELEASE,
            last=XCB_BUTTON_RELEASE,
        )
        record_range = xcb_record_range_t(
            device_events=device_events
        )
        client_spec = xcb_record_client_spec_t(
            XCB_RECORD_CS_ALL_CLIENTS
        )
        record_context = self.xcb.xcb_generate_id(self.conn)
        cookie = self.xcb_record.xcb_record_create_context_checked(
            self.conn, record_context, 0, 1, 1,
            ctypes.byref(client_spec),
            ctypes.byref(record_range)
        )
        err = self.xcb.xcb_request_check(self.conn, cookie)
        if err:
            self.xcb_xkb.free(err)
            print "Cant initialize event handler"
            self._exit()

        self.record_cookie = self.xcb_record.xcb_record_enable_context(
            self.conn, record_context
        )

        self.xcb_record.xcb_record_enable_context_reply.restype \
        = ctypes.POINTER(xcb_record_enable_context_reply_t)

        self.xcb_record.xcb_record_enable_context_data.restype \
        = ctypes.POINTER(ctypes.c_ubyte)


if __name__ == '__main__':
    HotCornersApp()

