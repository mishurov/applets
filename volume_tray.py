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
import select
import pygtk
import gtk
import gobject
from pyalsa import alsacard, alsamixer


VOLUME_WIDTH = 175
VOLUME_HEIGHT = 35
SCROLL_BY = 1
MIXER_LABEL = "PulseAudio"
MIXER_CMD = "pavucontrol"
VOL_CTRL="Master"
POLL_TIMEOUT=100


class SoundIcon(object):
    def __init__(self):
        signal.signal(signal.SIGINT, gtk.main_quit)
        self.init_alsa()
        self.init_menu()
        self.init_icon()
        self.update_icon()

    def init_alsa(self):
        self.mixer = alsamixer.Mixer()
        self.mixer.attach()
        self.mixer.load()
        self.element = alsamixer.Element(self.mixer, VOL_CTRL)
        self.element.set_callback(self.on_element_changed)
        self.volume_range = self.element.get_volume_range()

        # Setup mixer changes event handling
        self.poller = select.poll()
        self.mixer.register_poll(self.poller)
        gobject.timeout_add(POLL_TIMEOUT,
                            self.poll)
        self.poller.poll()

    def poll(self):
        self.mixer.handle_events()
        return True

    def init_icon(self):
        self.icon = gtk.StatusIcon()
        self.icon.connect('activate', self.on_icon_left_click)
        self.icon.connect('popup-menu', self.on_icon_right_click)
        self.icon.connect('scroll-event', self.on_icon_scroll)

    def on_element_changed(self, element, event):
        self.update_icon()

    def init_menu(self):
        self.slider = gtk.HScale()
        self.slider.set_can_focus(False)
        self.slider.set_size_request(VOLUME_WIDTH,
                                     VOLUME_HEIGHT)
        self.slider.set_range(0, 100)
        self.slider.set_digits(0)
        self.slider.set_draw_value(True)
        self.slider.connect('value-changed', self.on_slide)

        slider_item = gtk.ImageMenuItem()
        slider_item.add(self.slider)
        for e in ('motion-notify-event',
                  'button-press-event',
                  'button-release-event',):
            slider_item.connect(e, self.redirect_mouse, e)

        for e in ('grab-broken-event',
                  'grab-notify',):
            slider_item.connect(e, self.redirect_grab, e)

        mixer_item = gtk.MenuItem(MIXER_LABEL)
        mixer_item.connect('activate', self.activate_mixer)

        self.menu = gtk.Menu()
        self.menu.append(slider_item)
        self.menu.append(mixer_item)
        self.menu.show_all()

    def redirect_mouse(self, widget, event, name):
        parent_allocation = widget.get_allocation()
        allocation = self.slider.get_allocation()
        event.x -= allocation.x
        event.y -= allocation.y
        event.x_root -= allocation.y
        event.y_root -= allocation.y
        self.slider.emit(name, event)
        return True

    def redirect_grab(self, widget, event, name):
        self.slider.emit(name, event)
        return True

    def activate_mixer(self, widget):
        gobject.spawn_async(
            [MIXER_CMD],
            flags=gobject.SPAWN_SEARCH_PATH
        )

    def on_icon_left_click(self, widget):
        self.update_slider()
        self.menu.popup(None, None, None, 1,
                        gtk.get_current_event_time())

    def on_icon_right_click(self, widget, button, time):
        mute = self.element.get_switch()
        self.element.set_switch_all(not mute)
        self.update_icon()

    def on_slide(self, widget):
        level = widget.get_value()
        level = self.volume_range[1] / 100 * level
        gobject.idle_add(
           self.set_volume, level
        )

    def set_volume(self, level):
        volume = int(level)
        if volume > self.volume_range[1]:
            volume = self.volume_range[1]
        if volume < self.volume_range[0]:
            volume = self.volume_range[0]
        self.element.set_volume_all(volume)
        gobject.idle_add(
            self.update_icon
        )
        return False

    def on_icon_scroll(self, widget, event):
        delta = self.volume_range[1] / 100 * SCROLL_BY
        volume = self.element.get_volume()
        if event.direction == gtk.gdk.SCROLL_UP:
            self.set_volume(volume + delta)
        elif event.direction == gtk.gdk.SCROLL_DOWN:
            self.set_volume(volume - delta)

    def update_icon(self):
        volume = self.element.get_volume()
        is_muted  = not self.element.get_switch()

        low_tresh = int(self.volume_range[1] / 100 * 25)
        high_tresh = int(self.volume_range[1] / 100 * 75)

        if is_muted:
            self.icon.set_from_icon_name('audio-volume-muted-panel')
        elif volume < low_tresh:
            self.icon.set_from_icon_name('audio-volume-low-panel')
        elif volume >  high_tresh:
            self.icon.set_from_icon_name('audio-volume-high-panel')
        else:
            self.icon.set_from_icon_name('audio-volume-medium-panel')
        return False

    def update_slider(self):
        volume = self.element.get_volume()
        level = volume / (self.volume_range[1] / 100)
        self.slider.set_value(level)


if __name__ == '__main__':
    pygtk.require("2.0")
    gobject.threads_init()
    SoundIcon()
    gtk.threads_enter()
    gtk.main()
    gtk.threads_leave()
