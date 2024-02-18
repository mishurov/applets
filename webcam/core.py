#!/usr/bin/env python3

# sudo apt install v4l-utils

import os
import re
import subprocess

CAM1 = '/dev/video0'
CAM2 = '/dev/video2'

CAM = CAM2 if os.path.isfile(CAM2) else CAM1


CTRL_RE = re.compile('\s+([a-z_]+)\s0x[0-9a-f]+\s\(([a-z]+)\)\s+:(.+)')
MENU_RE = re.compile('\s+([0-9]+):\s([0-9A-Za-z\s]+)')

PIX_RE = re.compile("\s+\[[0-9]+\]:\s'([A-Z0-9]+)'")
RES_RE = re.compile('\s+Size:\s[A-Za-z]+\s([0-9]+x[0-9]+)')
FPS_RE = re.compile('\s+Interval:\s.*\(([0-9]+)\.[0-9]+\sfps\)')

PIX_FMT_RE = re.compile("\s+Pixel\sFormat\s*:\s'([A-Z0-9]+)'")
PARM_RE = re.compile('\s+Frames\sper\ssecond\s*:\s([0-9]+)\.')

V4L_BIN = 'v4l2-ctl'

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
                if '=' not in p:
                    continue
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

