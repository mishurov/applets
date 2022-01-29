#!/usr/bin/env python3

import re
import subprocess
import signal

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')

from gi.repository import GObject
from gi.repository import Gio
from gi.repository import Gdk
from gi.repository import Gtk


CAM = '/dev/video0'


CTRL_RE = re.compile('\s+([a-z_]+)\s0x[0-9a-f]+\s\(([a-z]+)\)\s+:(.+)')
MENU_RE = re.compile('\s+([0-9]+):\s([0-9A-Za-z\s]+)')

PIX_RE = re.compile("\s+\[[0-9]+\]:\s'([A-Z0-9]+)'")
RES_RE = re.compile('\s+Size:\s[A-Za-z]+\s([0-9]+x[0-9]+)')
FPS_RE = re.compile('\s+Interval:\s.*\(([0-9]+)\.[0-9]+\sfps\)')

PIX_FMT_RE = re.compile("\s+Pixel\sFormat\s*:\s'([A-Z0-9]+)'")
PARM_RE = re.compile('\s+Frames\sper\ssecond\s*:\s([0-9]+)\.')

V4L_BIN = 'v4l2-ctl'
ICON_NAME = 'clipboard'
ICON_SIZE = 16
SLIDER_WIDTH = 300
SLIDER_HEIGHT = 40


signal.signal(signal.SIGINT, signal.SIG_DFL)


class V4l2Ctl(object):
    def cam_cmd(self):
        return [V4L_BIN, '-d', CAM]

    def read_cam(self, param):
        p = subprocess.run(self.cam_cmd() + [param],
            capture_output=True, text=True)
        return p.stdout.splitlines()

    def get_format(self):
        pix = res = None
        for l in self.read_cam('--get-fmt-video'):
            if (l.lstrip().startswith('Width/Height')):
                w, h = l.split(':')[1].strip().split('/')
                res = f'{w}x{h}'
                continue
            m = PIX_FMT_RE.search(l)
            if m:
                pix = m.group(1)
                break
        fps = None
        for l in self.read_cam('--get-parm'):
            m = PARM_RE.search(l)
            if m:
                fps = m.group(1)
        return [pix, res, fps]

    def read_formats(self):
        pix = res = fps = None
        formats = []
        for l in self.read_cam('--list-formats-ext'):
            m = PIX_RE.search(l)
            if m:
                pix = m.group(1)
                continue
            m = RES_RE.search(l)
            if m:
                res = m.group(1)
                continue
            m = FPS_RE.search(l)
            if m:
                fps = m.group(1)
                formats.append([pix, res, fps])
        return formats

    def read_controls(self):
        controls = {}
        last_ctl = None

        for l in self.read_cam('--list-ctrls-menu'):
            m = CTRL_RE.search(l)
            if not m:
                if last_ctl and controls[last_ctl][0] != 'menu':
                    continue
                m2 = MENU_RE.search(l)
                if not m2:
                    continue
                controls[last_ctl][2][m2.group(1)] = m2.group(2)
                continue
            ctl_type = m.group(2)
            ctl_name = m.group(1)
            last_ctl = ctl_name
            params = m.group(3)
            ctl_params = {}
            for p in params.split():
                k, v = p.split('=')
                ctl_params[k] = v
            controls[ctl_name] = [ctl_type, ctl_params]
            if ctl_type == 'menu':
                controls[ctl_name].insert(2, {})
        return controls

    def set_control(self, name, value):
        subprocess.call(self.cam_cmd() + [f'--set-ctrl={name}={value}',])

    def set_format(self, pix, res, fps):
        w, h = res.split('x')
        subprocess.call(self.cam_cmd() + [
            f'--set-fmt-video=width={w},height={h},pixelformat={pix}',])
        subprocess.call(self.cam_cmd() + [f'--set-parm={fps}',])

    def export_script(self):
        cam_cmd = ' '.join(self.cam_cmd())
        controls = self.read_controls()
        script = '#!/bin/sh\n\n'
        cmd_controls = []
        for k, v in controls.items():
            cmd_controls.append(f'{k}={v[1]["value"]}')
        script += f'{cam_cmd} --set-ctrl=' + ','.join(cmd_controls) + '\n\n'
        pix, res, fps = self.get_format()
        w, h = res.split('x')
        script += f'{cam_cmd} --set-fmt-video=width={w},height={h},pixelformat={pix}\n\n'
        script += f'{cam_cmd} --set-parm={fps}'
        return script


class BaseControl(object):
    signals_created = False
    def __init__(self, name, *args, **kwargs):
        self.name = name
        if not self.__class__.signals_created:
            GObject.signal_new('value-changed',
                self, GObject.SignalFlags.RUN_LAST, GObject.TYPE_NONE, ())
            GObject.signal_new('change-finished',
                self, GObject.SignalFlags.RUN_LAST, GObject.TYPE_NONE, ())
            self.__class__.signals_created = True
        return super().__init__(*args, **kwargs)

    def get_name(self):
        return self.name

    def get_value(self):
        return self.value

    def finish_change(self, *args):
        while Gtk.events_pending():
            Gtk.main_iteration()
        self.emit('change-finished')


class Slider(BaseControl, Gtk.Box):
    def __init__(self, minimum, maximum, step, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.minimum = minimum
        self.maximum = maximum
        self.step = step
        self.set_orientation(Gtk.Orientation.HORIZONTAL)

        self.hscale = Gtk.HScale()
        self.hscale.set_draw_value(False)
        self.hscale.set_range(self.minimum / self.step, self.maximum / self.step)
        self.hscale.set_round_digits(0)
        self.hscale.set_size_request(SLIDER_WIDTH, SLIDER_HEIGHT)
        self.hscale_handler_id = self.hscale.connect(
            'value-changed', self.on_slider_changed, self.name, self.step)
        self.hscale.connect('button-release-event', self.finish_change)

        self.spin = Gtk.SpinButton()
        self.spin.set_numeric(True)
        self.spin.set_snap_to_ticks(True)
        self.spin.set_increments(step, 0)
        self.spin.set_range(self.minimum, self.maximum)
        self.spin_handler_id = self.spin.connect(
            'value-changed', self.on_spin_changed, self.name, self.step)

        self.add(self.hscale)
        self.add(self.spin)

    def on_slider_changed(self, slider, name, step):
        self.value = int(slider.get_value() * step)
        with self.spin.handler_block(self.spin_handler_id):
            self.spin.set_value(self.value)
        self.emit('value-changed')

    def on_spin_changed(self, spin, name, step):
        value = int(spin.get_value())
        if self.value == value:
            return
        self.value = value
        with self.hscale.handler_block(self.hscale_handler_id):
            self.hscale.set_value(self.value)
        self.emit('value-changed')
        self.finish_change()

    def set_value(self, value):
        self.value = value
        with self.spin.handler_block(self.spin_handler_id):
            self.spin.set_value(self.value)
        with self.hscale.handler_block(self.hscale_handler_id):
            self.hscale.set_value(self.value)


class Dropdown(BaseControl, Gtk.ComboBox):
    def __init__(self, options, *args, **kwargs):
        super().__init__(*args, **kwargs)
        model = Gtk.ListStore(str, str)
        for k, v in options.items():
            model.append([k, v])
        self.set_model(model)
        renderer_text = Gtk.CellRendererText()
        self.pack_start(renderer_text, True)
        self.add_attribute(renderer_text, 'text', 1)
        self.set_id_column(0)
        self.handler_id = self.connect('changed', self.on_value_changed)

    def on_value_changed(self, combo):
        self.value = int(combo.get_active_id())
        self.emit('value-changed')
        self.finish_change()

    def set_value(self, value):
        self.value = value
        with self.handler_block(self.handler_id):
            self.set_active_id(str(self.value))


class CheckBox(BaseControl, Gtk.CheckButton):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.handler_id = self.connect('toggled', self.on_value_changed)

    def on_value_changed(self, button):
        self.value = int(button.get_active())
        self.emit('value-changed')
        self.finish_change()

    def set_value(self, value):
        self.value = value
        with self.handler_block(self.handler_id):
            self.set_active(bool(self.value))


class Camera(Gtk.Application):
    formats = []
    ui_controls = {}
    ui_format = None

    def __init__(self):
        Gtk.Application.__init__(
            self, 
            flags=Gio.ApplicationFlags.FLAGS_NONE
        )
        self.v4l2_ctl = V4l2Ctl()

    def on_control_value_changed(self, control):
        name = control.get_name()
        value = control.get_value()
        self.v4l2_ctl.set_control(name, value)

    def on_control_change_finished(self, control):
        self.update_controls()

    def on_format_value_changed(self, ui_format):
        value = ui_format.get_value()
        pix, res, fps = self.formats[value]
        self.v4l2_ctl.set_format(pix, res, fps)

    def on_format_change_finished(self, control):
        self.update_format()

    def on_export(self, button):
        dialog = Gtk.FileChooserDialog(
            title='Please choose a file',
            parent=self.get_windows()[0],
            action=Gtk.FileChooserAction.SAVE
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL,
            Gtk.ResponseType.CANCEL,
            Gtk.STOCK_SAVE,
            Gtk.ResponseType.OK,
        )
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            filename = dialog.get_filename()
            if filename:
                script = self.v4l2_ctl.export_script()
                with open(filename, 'w') as f:
                    f.write(script)
        dialog.destroy()

    def get_grid_rows(self, grid):
        return len([c for c in grid.get_children() if
            grid.child_get_property(c, 'left-attach') == 0])

    def add_controls(self, grid):
        controls_data = self.v4l2_ctl.read_controls()

        for row, [k, v] in enumerate(controls_data.items(), self.get_grid_rows(grid)):
            label = Gtk.Label.new(k)
            label.set_xalign(1)
            grid.attach(label, 0, row, 1, 1)

            ctl_type = v[0]
            params = v[1]
            control = None
            if ctl_type == 'bool':
                control = CheckBox(k)
            elif ctl_type == 'int':
                control = Slider(
                    int(params['min']),
                    int(params['max']),
                    int(params['step']),
                    k,
                )
            elif ctl_type == 'menu':
                control = Dropdown(v[2], k)

            if control is None:
                continue

            control.connect('value-changed', self.on_control_value_changed)
            control.connect('change-finished', self.on_control_change_finished)
            grid.attach(control, 1, row, 1, 1)
            self.ui_controls[k] = control

    def add_format(self, grid):
        self.formats = self.v4l2_ctl.read_formats()
        formats = {str(k) : f'{p} {r} {f}' for k, [p, r, f] in enumerate(self.formats)}
        self.ui_format = Dropdown(formats, 'formats')
        self.ui_format.connect('value-changed', self.on_format_value_changed)
        self.ui_format.connect('change-finished', self.on_format_change_finished)
        rows = self.get_grid_rows(grid)
        grid.attach(Gtk.Separator(), 0, rows, 2, 1)
        grid.attach(self.ui_format, 0, rows + 1, 2, 1)
        grid.attach(Gtk.Separator(), 0, rows + 2, 2, 1)

    def add_export(self, grid):
        button = Gtk.Button.new_with_label('Export settings script')
        button.connect('clicked', self.on_export)
        rows = self.get_grid_rows(grid)
        grid.attach(button, 0, rows, 2, 1)

    def update_controls(self):
        controls_data = self.v4l2_ctl.read_controls()
        for k, v in self.ui_controls.items():
            data = controls_data[k][1]
            v.set_value(int(data['value']))
            insensitive = 'flags' in data and data['flags'] == 'inactive'
            v.set_sensitive(not insensitive)

    def update_format(self):
        current_format = self.v4l2_ctl.get_format()
        self.ui_format.set_value(self.formats.index(current_format))

    def do_activate(self):
        w = Gtk.Window()
        w.set_type_hint(Gdk.WindowTypeHint.DIALOG)
        w.set_role('V4l2Ctl')
        w.set_title('v4l2-ctl')

        sw = Gtk.ScrolledWindow()
        sw.set_min_content_width(480)
        sw.set_max_content_width(1024)
        sw.set_min_content_height(320)
        sw.set_max_content_height(768)
        sw.set_propagate_natural_width(True)
        sw.set_propagate_natural_height(True)
        g = Gtk.Grid()
        g.set_border_width(15)
        g.set_row_spacing(5)
        g.set_column_spacing(7)
        self.add_controls(g)
        self.add_format(g)
        self.add_export(g)
        sw.add(g)

        w.add(sw)
        w.show_all()
        self.add_window(w)
        self.update_controls()
        self.update_format()

    def do_startup(self):
        Gtk.Application.do_startup(self)

    def do_shutdown(self):
        Gtk.Application.do_shutdown(self)

    def on_quit(self, widget, data):
        self.quit()


if __name__ == '__main__':
    cam = Camera()
    cam.run(None)
