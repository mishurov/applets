from typing import Any, Callable
from enum import Enum
import os
import socket
import struct
import json


MAGIC = 'i3-ipc'
HEADER = '=%dsII' % len(MAGIC.encode('utf-8'))
HEADER_SIZE = struct.calcsize(HEADER)

SCRATCH_NAME = '__i3_scratch'


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
    # sway only
    GET_INPUTS = 100
    GET_SEATS = 101


class EventType(Enum):
    WORKSPACE = (1 << 0)
    OUTPUT = (1 << 1)
    MODE = (1 << 2)
    WINDOW = (1 << 3)
    BARCONFIG_UPDATE = (1 << 4)
    BINDING = (1 << 5)
    SHUTDOWN = (1 << 6)
    TICK = (1 << 7)
    INPUT = (1 << 21)


def socket_path() -> str | None:
    return os.environ.get('SWAYSOCK', None)


def pack(msg_type: MessageType, payload: str) -> bytes:
    pb = payload.encode('utf-8')
    s = struct.pack('=II', len(pb), msg_type.value)
    return MAGIC.encode('utf-8') + s + pb


def unpack_header(data: bytes) -> tuple[str, int, str]:
    return struct.unpack(HEADER, data[:HEADER_SIZE])


def unpack(data: bytes) -> str:
    msg_magic, msg_length, msg_type = unpack_header(data)
    msg_size = HEADER_SIZE + msg_length
    payload = data[HEADER_SIZE:msg_size]
    return payload.decode('utf-8', 'replace')


def read(sock: socket.socket) -> Any:
    data = sock.recv(14)
    msg_magic, msg_length, msg_type = unpack_header(data)
    msg_size = HEADER_SIZE + msg_length
    while len(data) < msg_size:
        data += sock.recv(msg_length)
    payload = unpack(data)
    return json.loads(payload)


def get_socket() -> socket.socket | None:
    path = socket_path()
    if path is None:
        return path
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.connect(path)
    return sock


def print_version(sock: socket.socket) -> None:
    sock.sendall(pack(MessageType.GET_VERSION, ''))
    decoded = read(sock)
    print(decoded)


def get_tree(sock: socket.socket) -> Any:
    sock.sendall(pack(MessageType.GET_TREE, ''))
    return read(sock)


def get_workspaces(sock: socket.socket) -> Any:
    sock.sendall(pack(MessageType.GET_WORKSPACES, ''))
    return read(sock)


def get_marks(sock: socket.socket) -> Any:
    sock.sendall(pack(MessageType.GET_MARKS, ''))
    return read(sock)


def command(sock: socket.socket, cmd: str) -> Any:
    sock.sendall(pack(MessageType.COMMAND, cmd))
    return read(sock)


def subscribe_window() -> tuple[socket.socket, Any] | None:
    sub_sock = get_socket()
    if sub_sock is None:
        return None
    window = ['window',]
    sub_sock.sendall(pack(MessageType.SUBSCRIBE, json.dumps(window)))
    return sub_sock, [read(sub_sock)]


def find_con_parent_workspace(
    parent: dict[str, Any],
    callback_fn: Callable[[dict[str, Any]], bool],
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None]:
    nodes = parent['nodes'] + parent['floating_nodes']
    workspace = None
    for n in nodes:
        if n['type'] == 'workspace':
            workspace = n
        if callback_fn(n):
            return n, parent, workspace
        else:
            rn, p, w = find_con_parent_workspace(n, callback_fn)
            if rn is not None:
                return rn, p, w or workspace
    return None, None, None


def find_nodes(
    parent: dict[str, Any],
    callback_fn: Callable[[dict[str, Any]], bool],
) -> list[dict[str, Any]]:
    nodes = parent['nodes'] + parent['floating_nodes']
    apps = []
    for n in nodes:
        if callback_fn(n):
            apps.append(n)
        apps.extend(find_nodes(n, callback_fn))
    return apps
