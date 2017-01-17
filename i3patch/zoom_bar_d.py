#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import os
import signal
import subprocess
import struct
import json
import socket


ZOOMED_MARK = "*Z"

FNULL = open(os.devnull, 'w')


class I3Connection(object):
    MAGIC = 'i3-ipc'
    _struct_header = '<%dsII' % len(MAGIC.encode('utf-8'))
    _struct_header_size = struct.calcsize(_struct_header)

    def check_output(self, cmd, shell=False):
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE,
            #stderr=FNULL,
            env=os.environ.copy(),
            shell=shell
        )
        return process.communicate()[0]

    def _check_zoom_enabled(self):
        out = self.check_output(["i3-msg", "zoom"])
        if "^^^" in out.decode('UTF-8'):
            print("Zoom isn't enabled")
            exit()

    def _check_and_kill_another_instance(self):
        script_name = os.path.basename(__file__)
        cmd = 'ps ax | grep "python.*%s.*" | grep -v grep' % script_name
        ps = self.check_output(cmd, shell=True)
        for line in ps.splitlines():
            pid = int(line.split()[0])
            if pid != os.getpid():
                os.kill(pid, signal.SIGTERM)

    def __init__(self):
        self._check_zoom_enabled()
        self._check_and_kill_another_instance()
        signal.signal(signal.SIGTERM, self.main_quit)
        signal.signal(signal.SIGINT, self.main_quit)

        path = subprocess.check_output(["i3","--get-socketpath"])
        path = path.strip()

        self.cmd_socket = socket.socket(
            socket.AF_UNIX, socket.SOCK_STREAM
        )
        self.cmd_socket.connect(path)
        self.sub_socket = socket.socket(
            socket.AF_UNIX, socket.SOCK_STREAM
        )
        self.sub_socket.connect(path)
        data = self._ipc_send(
            self.sub_socket, 2, json.dumps(["window"])
        )
        self.remark_all()

    def _ipc_send(self, sock, message_type, payload):
        sock.sendall(self._pack(message_type, payload))
        data, msg_type = self._ipc_recv(sock)
        return data

    def _pack(self, msg_type, payload):
        pb = payload.encode()
        s = struct.pack('=II', len(pb), msg_type)
        return self.MAGIC.encode() + s + pb

    def _unpack(self, data):
        msg_magic, msg_length, msg_type = self._unpack_header(data)
        msg_size = self._struct_header_size + msg_length
        return data[self._struct_header_size:msg_size].decode('utf-8')

    def _unpack_header(self, data):
        return struct.unpack(self._struct_header,
                             data[:self._struct_header_size])

    def _ipc_recv(self, sock):
        data = sock.recv(14)

        if len(data) == 0:
            return '', 0
        msg_magic, msg_length, msg_type = self._unpack_header(data)
        msg_size = self._struct_header_size + msg_length
        while len(data) < msg_size:
            data += sock.recv(msg_length)
        return self._unpack(data), msg_type

    def get_workspaces(self):
        data = self._ipc_send(self.cmd_socket, 1, '')
        return json.loads(data, object_hook=dict)

    def get_tree(self):
        data = self._ipc_send(self.cmd_socket, 4, '')
        return json.loads(data, object_hook=dict)

    def command(self, payload):
        data = self._ipc_send(self.cmd_socket, 0, payload)
        return json.loads(data, object_hook=dict)

    def get_ws_name(self):
        name = ''
        for w in self.get_workspaces():
            if w['focused']:
                name = w['name']
                break
        return name

    def unmark_all(self):
        for w in self.get_workspaces():
            name = w['name']
            if name.endswith(ZOOMED_MARK):
                self.command(
                    'rename workspace %s to %s' % (name, name[:-2])
                )

    def find_any_in_tree(self, parent_node, key, value):
        for k in parent_node.keys():
            if k == key and parent_node[k] == value:
                return parent_node
        for child_node in parent_node['nodes']:
            ret = self.find_any_in_tree(child_node, key, value)
            if ret: return ret

    def mark_all_zoomed(self):
        tree = self.get_tree()
        wss = self.get_workspaces()
        for ws in wss:
            name = ws['name']
            ws_branch = self.find_any_in_tree(tree, 'name', name)
            if self.find_any_in_tree(ws_branch, 'zoomed', 1) \
                and not name.endswith(ZOOMED_MARK):
                self.command(
                    'rename workspace %s to %s%s' % (name, name, ZOOMED_MARK)
                )
            else:
                if name.endswith(ZOOMED_MARK):
                    self.command(
                        'rename workspace %s to %s' % name, name[:-2]
                    )

    def remark_all(self):
        self.unmark_all()
        self.mark_all_zoomed()

    def remove_z_mark_from_focused(self):
        name = self.get_ws_name()
        if name.endswith(ZOOMED_MARK):
            self.command('rename workspace to %s' % name[:-2])

    def add_z_mark_to_focused(self):
        name = self.get_ws_name()
        if not name.endswith(ZOOMED_MARK):
            self.command(
                'rename workspace to %s%s' % (name, ZOOMED_MARK)
            )

    def main(self):
        while True:
            data, msg_type = self._ipc_recv(self.sub_socket)
            json_data = json.loads(data)
            change = json_data['change']
            if not change in ['zoomed', 'close']:
                continue
            focused = json_data['container']['focused']
            zoomed = json_data['container']['zoomed']

            if change == 'close' and zoomed:
                if focused:
                    self.remove_z_mark_from_focused()
                else:
                    self.mark_all_zoomed()

            if focused and change == 'zoomed':
                if zoomed:
                    self.add_z_mark_to_focused()
                else:
                    self.remove_z_mark_from_focused()

    def main_quit(self, *args):
        self.unmark_all()
        self.cmd_socket.close()
        self.sub_socket.close()
        self.cmd_socket = None
        self.sub_socket = None


if __name__ == '__main__':
    i3c = I3Connection()
    i3c.main()

