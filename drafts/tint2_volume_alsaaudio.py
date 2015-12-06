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


import pygtk
import gtk
import signal
import alsaaudio
import subprocess


pygtk.require("2.0")


VOLUME_WIDTH = 175
VOLUME_HEIGHT = 25
SCROLL_BY = 1
MIXER_LABEL = "PulseAudio"
MIXER_CMD = "pavucontrol"
VOL_CTRL="Master"


class SoundIcon:
    def __init__(self):
        signal.signal(signal.SIGUSR1, self.sig_usr1)
        signal.signal(signal.SIGINT, gtk.main_quit)

        self.init_device()
        self.init_menu()

        self.icon = gtk.StatusIcon()
        self.icon.connect('activate', self.show_menu)
        self.icon.connect('popup-menu', self.toggle_mute)
        self.icon.connect('scroll-event', self.on_scroll)

        self.update()
        self.icon.set_visible(True)

    def sig_usr1(self, signum, frame):
        self.update_icon()

    def init_device(self):
        device = None
        for i, card in enumerate(alsaaudio.cards()):
          if VOL_CTRL in alsaaudio.mixers(i):
            device = i
            break
        self.device = device

    @property
    def mixer(self):
        # The mixer must be recreated every time
        # it is used to be able to observe volume/mute
        # changes done by other applications
        return alsaaudio.Mixer(control=VOL_CTRL,
                               cardindex=self.device)

    def init_menu(self):
        self.slider = gtk.HScale()
        self.slider.set_can_focus(False)
        self.slider.set_size_request(VOLUME_WIDTH,
                                     VOLUME_HEIGHT)
        self.slider.set_range(0, 100)
        self.slider.set_increments(-SCROLL_BY, 12)
        self.slider.set_draw_value(0)
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

    def activate_mixer(self, widget):
        subprocess.Popen([MIXER_CMD], shell=True, stdin=None,
                         stdout=None, stderr=None, close_fds=True)

    def redirect_grab(self, widget, event, name):
        self.slider.emit(name, event)
        return True

    def redirect_mouse(self, widget, event, name):
        parent_allocation = widget.get_allocation()
        allocation = self.slider.get_allocation()
        event.x -= allocation.x
        event.y -= allocation.y
        event.x_root -= allocation.y
        event.y_root -= allocation.y
        self.slider.emit(name, event)
        return True

    def show_menu(self, widget):
        self.menu.popup(None, None, None, 1,
                        gtk.get_current_event_time())

    def set_volume(self, level):
        volume = int(round(level))
        if volume > 100:
            volume = 100
        if volume < 0:
            volume = 0
        self.mixer.setvolume(volume)
        self.update()

    def toggle_mute(self, widget, button, time):
        # set mute via amixer subprocess
        # pyalsa mixer doesn't work correctly
        cmd = ["amixer", "-q", "set", 
               VOL_CTRL, "toggle"]
        subprocess.call(cmd)
        self.update()

    def on_slide(self, widget):
        volume = widget.get_value()
        self.set_volume(volume)

    def on_scroll(self, widget, event):
        # minimal step is 2
        delta = SCROLL_BY + 1
        volume = self.mixer.getvolume()[0]
        volume = round(volume)
        if event.direction == gtk.gdk.SCROLL_UP:
            self.set_volume(volume + delta)
        elif event.direction == gtk.gdk.SCROLL_DOWN:
            self.set_volume(volume - delta)

    def update_icon(self):
        # recreate mixer because it caches old values
        volume = round(self.mixer.getvolume()[0])
        muted  = self.mixer.getmute()[0]

        if muted:
            self.icon.set_from_icon_name('audio-volume-muted-panel')
        elif volume < 25:
            self.icon.set_from_icon_name('audio-volume-low-panel')
        elif volume > 75:
            self.icon.set_from_icon_name('audio-volume-high-panel')
        else:
            self.icon.set_from_icon_name('audio-volume-medium-panel')
        return volume, muted

    def update(self):
        volume, muted = self.update_icon()
        self.slider.set_value(volume)
        return True


if __name__ == '__main__':
    SoundIcon()
    gtk.main()
