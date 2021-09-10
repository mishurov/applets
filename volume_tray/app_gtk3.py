import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import GObject, GLib, Gtk, Gdk

from core import (
    PulseMixer,
    VolumeMixin,
    MediaKeysMixin,
    APP_NAME,
    LABEL_MIXER,
    LABEL_EXIT,
    SCROLL_BY
)


VOLUME_WIDTH = 300
VOLUME_HEIGHT = 80

ICON_SIZE = 22
GDK_MONITOR = Gdk.Display.get_default().get_monitor(0)
SCALE_FACTOR = GDK_MONITOR.get_scale_factor()
ROOT_HEIGHT = GDK_MONITOR.get_geometry().height


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


class SoundIcon(VolumeMixin, MediaKeysMixin):
    def __init__(self):
        Gdk.set_program_class(APP_NAME)

        self.mixer = PulseMixer()
        self.init_dbus()
        self.create_icon()
        self.mixer.start_listener(self.get_pulse_callback)
        self.create_menu()
        self.update_icon()
        self.init_keys()
        self.create_styles()

        self.run()

    def get_pulse_callback(self):
        return lambda s: GLib.idle_add(self.update_icon)

    def get_notify_callback(self):
        return lambda k, t: GLib.idle_add(self.on_media_key_pressed, [k, t])

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

    def create_icon(self):
        self.icon_name = ''
        self.icon = Gtk.StatusIcon()
        self.icon_theme = Gtk.IconTheme.get_default()
        self.icon.connect('button-press-event', self.activate)
        self.icon.connect('scroll-event', self.on_scroll)

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

    def create_mixer(self):
        item = Gtk.MenuItem(label=LABEL_MIXER)
        item.connect('activate', self.activate_mixer)
        return item

    def create_exit(self):
        item = Gtk.MenuItem(label=LABEL_EXIT)
        item.connect('activate', self.activate_exit)
        return item

    def activate_exit(self, *args):
        self.loop.quit()
        return True

    def activate(self, widget, event):
        if event.button == 3:
            self.mixer.toggle_mute()
            return True
        if event.button > 1:
            return False
        self.update_menu()
        volume, mute = self.mixer.get_sink_volume_and_mute()
        self.slider_item.set_value(volume)
        self.slider_item.set_sensitive(not mute)
        current_time = Gtk.get_current_event_time()
        self.menu.popup_at_pointer(event)
        # fix bottom positioning
        if event.y_root > ROOT_HEIGHT / 2:
            self.menu.popup(None, None,
                self.icon.position_menu, self.icon,
                event.button, current_time)
        return True

    def destroy_item(self, item):
        item.destroy()

    def insert_label_item(self, label, pos):
        item = Gtk.MenuItem(label=label)
        style_context = item.get_style_context()
        style_context.add_class('subtitle')
        item.set_sensitive(False)
        item.set_visible(True)
        self.menu.insert(item, pos)
        self.profile_items.append(item)

    def insert_subaction_item(self, profile, link, pos):
        item = Gtk.MenuItem(label=profile)
        style_context = item.get_style_context()
        style_context.add_class('submenu')
        item.connect(
            'activate',
            lambda s, m: self.mixer.set_profile(m),
            link
        )
        if link == self.mixer.current_profile:
            item.set_sensitive(False)
        item.set_visible(True)
        self.menu.insert(item, pos)
        self.profile_items.append(item)

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

    def set_theme_icon(self, icon_name):
        gicon = self.icon_theme.load_icon_for_scale(
            icon_name, ICON_SIZE, SCALE_FACTOR, 0)
        self.icon.set_property("gicon", gicon)

    def is_menu_visible(self):
        return self.menu.get_visible()

    def run(self):
        self.loop = GLib.MainLoop()
        self.loop.run()


if __name__ == '__main__':
    SoundIcon()
