from enum import Enum
import os
import socket
import struct
import json


MAGIC = 'i3-ipc'
HEADER = '=%dsII' % len(MAGIC.encode('utf-8'))
HEADER_SIZE = struct.calcsize(HEADER)


class MessageType(Enum):
    COMMAND = 0
    GET_WORKSPACES = 1
    SUBSCRIBE = 2
    GET_OUTPUTS = 3
    GET_TREE = 4
    GET_MARKS = 5
    GET_BAR_CONFIG = 6
    GET_VERSION = 7
    GET_BINDING_MODES = 8
    GET_CONFIG = 9
    SEND_TICK = 10
    GET_INPUTS = 100
    GET_SEATS = 101


def socket_path():
    return os.environ.get('SWAYSOCK', None)


def get_socket():
    path = socket_path()
    if path is None:
        return path
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.connect(socket_path())
    return sock


def pack(msg_type, payload):
    pb = payload.encode('utf-8')
    s = struct.pack('=II', len(pb), msg_type.value)
    return MAGIC.encode('utf-8') + s + pb


def unpack_header(data):
    return struct.unpack(HEADER, data[:HEADER_SIZE])


def unpack(data):
    msg_magic, msg_length, msg_type = unpack_header(data)
    msg_size = HEADER_SIZE + msg_length
    payload = data[HEADER_SIZE:msg_size]
    return payload.decode('utf-8', 'replace')


def read(sock):
    data = sock.recv(14)
    msg_magic, msg_length, msg_type = unpack_header(data)
    msg_size = HEADER_SIZE + msg_length
    while len(data) < msg_size:
        data += sock.recv(msg_length)
    payload = unpack(data)
    return json.loads(payload)


def get_workspaces(sock):
    sock.sendall(pack(MessageType.GET_WORKSPACES, ''))
    return read(sock)


def command(sock, cmd):
    sock.sendall(pack(MessageType.COMMAND, cmd))
    return read(sock)
