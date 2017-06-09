#!/usr/bin/env python3

import os
import sys
import fcntl
import errno
from signal import signal, SIGABRT, SIGILL, SIGINT, SIGSEGV, SIGTERM
import random
import string
from subprocess import (Popen, PIPE, check_output,
                        CalledProcessError, DEVNULL)
from tempfile import TemporaryFile
import re
import threading

# i3ipc 1.3.0 patched:
# added "zoomed" to class Con > __init__ > ipc_properties
import i3ipc


CWD = os.path.dirname(os.path.realpath(__file__))
HOME = os.environ.get("HOME")
SHELL = os.environ.get("SHELL", None) or "/bin/sh"
CACHE_DIR = os.environ.get("XDG_CACHE_HOME", None) or os.path.join(HOME, ".cache")
CACHE_RUN_FILE = os.path.join(CACHE_DIR, "dmenu_run")
FAVOURITES = os.path.join(CWD, "..", "favourites")
EXIT_I3_SCRIPT = os.path.join(CWD, "exit_i3.sh")
WORKSPACES_NAMES = os.path.join(CWD, "..", "workspaces_names")
DMENU = "dmenu"
DMENU_ARGS = [ DMENU,
    "-fn", "Ubuntu-12",
    "-x", "520",
    "-y", "23",
    "-l", "30",
    "-w", "580",
]
DMENU_RUN_ARGS = [
    "-p", "'execute command:'",
    "-sb", "'#0858b1'",
]
DMENU_RENAME_ARGS = [
    "-p", "new workspace name:",
    "-sb", "#583f3f",
]
DMENU_ACTIONS_ARGS = [
    "-p", "window actions:",
    "-sb", "#BF0A37",
]
FIFO = os.path.join(CWD, '..', 'fifo')
PID = os.path.join(CWD, "i3_daemon.pid")
ZOOMED_MARK = "*Z"


# Allow only one instance of the daemon
pid = open(PID, 'w')
try:
    fcntl.lockf(pid, fcntl.LOCK_EX | fcntl.LOCK_NB)
except IOError:
    print("Another instance is running. Exiting...")
    sys.exit(0)


def is_zoom_enabled():
    # check if i3 is patched and zoom is enabled
    # NOTE: add property "zoomed" to i3ipc.Con for the patched i3
    zoom_output = check_output(["i3-msg", "zoom"], stderr=DEVNULL)
    return "^^^^" not in str(zoom_output, 'utf-8')


class Connection(object):
    def __init__(self):
        self.is_zoom_enabled = is_zoom_enabled()
        self.reconnect()

    def reconnect(self):
        self.i3 = i3ipc.Connection()

        # listen in a thread zoom events of the patched i3
        if self.is_zoom_enabled:
            self.relabel_workspaces(self.i3)
            thread = getattr(self, "thread", None)
            if not thread or not thread.is_alive():
                self.thread = threading.Thread(
                    target=self.daemon_connection
                )
                self.thread.daemon = True
                self.thread.start()

    def daemon_connection(self):
        # create a second connection for the listening thread
        self.i3_daemon = i3ipc.Connection()
        self.i3_daemon.on("window::zoomed", self.zoom_callback)
        self.i3_daemon.on("window::close", self.zoom_callback)
        self.i3_daemon.main()

    def zoom_callback(self, i3, e):
        self.relabel_workspaces(self.i3_daemon)

    def rename_workspace(self, i3, name, new_name):
        i3.command(
            "rename workspace %s to %s" % (name, new_name)
        )

    def relabel_workspaces(self, i3):
        tree = i3.get_tree()
        zoomed = [c.workspace() for c in tree.descendents()
                    if getattr(c, "zoomed", False)]
        for workspace in tree.workspaces():
            name = workspace.name
            marked = name.endswith(ZOOMED_MARK)
            if workspace in zoomed and not marked:
                new_name = name + ZOOMED_MARK
                self.rename_workspace(i3, name, new_name)
            elif workspace not in zoomed and marked:
                new_name = name[:-len(ZOOMED_MARK)]
                self.rename_workspace(i3, name, new_name)


conn = Connection()


def reconnect():
    conn.reconnect()


def create_workspace():
    """creates a workspace with the next biggest number
    """
    workspaces = conn.i3.get_workspaces()
    num = 0
    for w in workspaces:
        num = w.num if num < w.num else num
    chars = "".join(
        [random.choice(string.ascii_letters) for i in range(5)]
    )
    conn.i3.command('workspace %s' % str(num + 1) + chars)


def was_dmenu_running():
    """kills and returns True if dmenu is running 
    """
    try:
        pid = check_output(["pidof", DMENU])
    except CalledProcessError:
        return False
    else:
        #os.kill(int(pid), SIGTERM)
        os.system("killall dmenu");
        return True


def execute_command():
    """Runs dmenu with optional commands
    """
    cmd = DMENU_ARGS + DMENU_RUN_ARGS
    if not os.path.isfile(CACHE_RUN_FILE):
        favourites = ""
        with open(FAVOURITES, "r") as buf:
            favourites = buf.read()
        favourites = list(filter(None, favourites.split("\n")))
        # get all executables
        paths = os.environ["PATH"].split(":")
        list_dir = lambda p : os.listdir(p) if os.path.isdir(p) else []
        is_file = lambda x, y : os.path.isfile(os.path.join(x, y))
        bins = []
        for p in paths:
            for f in list_dir(p):
                if is_file(p, f):
                    bins.append(f)
        # remove dublicates in bins from favourites, keep favourites first
        options = favourites + list(set(bins) - set(favourites))
        data = "\n".join(options)
        with open(CACHE_RUN_FILE, "w") as buf:
            buf.write(data)
    # open dmenu
    cmd = "%s < %s | %s" % (" ".join(cmd), CACHE_RUN_FILE, SHELL)
    Popen(
        cmd, shell=True, stdin=None,
        stdout=None, stderr=None, close_fds=True
    )


def async_rename(names, current_num):
    cmd = DMENU_ARGS + DMENU_RENAME_ARGS
    input_name = b''
    with TemporaryFile("w") as temp:
        temp.write(names)
        temp.seek(0)
        try:
            input_name = check_output(cmd, stdin=temp)
        except CalledProcessError:
            return False

    input_name = str(input_name, 'utf-8')
    input_num = re.findall(r'^\d+', input_name)

    # If number of input name has some of existing workspaces,
    # reassign number
    if len(input_num) > 0:
        input_num = int(input_num[0])
        workspaces = conn.i3.get_workspaces()
        reassign = False
        max_num = 0
        for w in workspaces:
            max_num = w.num if max_num < w.num else max_num
            if input_num == w.num and input_num != current_num:
                reassign = True
        if reassign:
            input_name = re.sub(r'^\d+', str(max_num + 1), input_name)
    conn.i3.command("rename workspace to %s" % input_name)


def rename_workspace():
    tree = conn.i3.get_tree()
    focused = tree.find_focused()
    current_num = focused.workspace().num
    current_num = current_num if current_num > -1 else ""
    names = ""
    with open(WORKSPACES_NAMES, "r") as buf:
        names_list = buf.readlines()
    for n in names_list:
        names += str(current_num) + n

    thread = threading.Thread(
        target=async_rename, args=(names, current_num)
    )
    thread.daemon = True
    thread.start()


SCRATCH_NAME = "__i3_scratch"

def get_scratch():
    tree = conn.i3.get_tree()
    try:
        return next(c for c in tree.descendents() if c.name == SCRATCH_NAME)
    except StopIteration:
        return None


def cut():
    conn.i3.command("move scratchpad")


def paste():
    conn.i3.command("scratchpad show floating disable")


def scratch_to_from():
    scratch = get_scratch()
    leaves = scratch.leaves()
    if len(leaves) > 0:
        paste()
    else:
        cut()


def move_to_new_workspace():
    """moves a con from scratch to a new workspace
    or cuts a focused con and pastes it on a new workspace
    """
    scratch = get_scratch()
    leaves = scratch.leaves()
    if len(leaves) > 0:
        create_workspace()
        paste()
        return
    tree = conn.i3.get_tree()
    focused = tree.find_focused()
    leaves = focused.workspace().leaves()
    if len(leaves) > 0:
        cut()
        create_workspace()
        paste()


def smart_run():
    scratch = get_scratch()
    leaves = scratch.leaves()
    if len(leaves) > 0:
        paste()
    else:
        was_dmenu_running()
        execute_command()


def smart_fullscreen():
    if is_zoom_enabled():
        maximize_action="zoom"
        maximize_mode="zoomed"
    else:
        maximize_action="fullscreen"
        maximize_mode="fullscreen_mode"

    tree = conn.i3.get_tree()
    focused = tree.find_focused()

    is_focused_fullscreen = getattr(focused, maximize_mode)
    if is_focused_fullscreen:
        conn.i3.command("%s disable" % maximize_action)
        return

    is_parent_fullscreen = 0
    parent = focused.parent
    # find fullscreen among parents
    if not is_focused_fullscreen:
        while parent and parent.type != "workspace" :
            is_parent_fullscreen = getattr(parent, maximize_mode)
            if not is_parent_fullscreen:
                parent = parent.parent
            else:
                break

    if is_parent_fullscreen:
        parent.command("focus")
        parent.command("%s disable" % maximize_action)
        focused.command("focus")
        return

    # is container in stacked or tabbed environment
    parent = focused
    while parent and parent.type != "workspace" :
        if not parent.layout in ["tabbed", "stacked"]:
            parent = parent.parent
        else:
            break

    if parent.layout in ["tabbed", "stacked"]:
        parent.command("focus")
        parent.command("%s enable" % maximize_action)
        focused.command("focus")
        return

    if (focused.type != "workspace"
       and len(parent.leaves()) > 1):
        focused.command("%s enable" % maximize_action)


def fullscreen(): conn.i3.command("fullscreen")

def floating(): conn.i3.command("floating toggle")

def split(): conn.i3.command("layout toggle split")

def tabbed(): conn.i3.command("layout tabbed")

def stacking(): conn.i3.command("layout stacking")

def vertical_split_and_run():
    conn.i3.command("split v")
    was_dmenu_running()
    execute_command()

def horisontal_split_and_run():
    conn.i3.command("split h")
    was_dmenu_running()
    execute_command()

def vertical_split_and_paste():
    conn.i3.command("split v")
    paste()

def horisontal_split_and_paste():
    conn.i3.command("split h")
    paste()

def close():
    conn.i3.command("kill")

def exit_i3():
    cmd = ["sh", EXIT_I3_SCRIPT]
    Popen(
        cmd, stdin=False, shell=False,
        stdout=None, stderr=None, close_fds=True
    )


MAIN_ACTIONS = [
    "toggle fullscreen",
    "toggle floating",
]

EMPTY_SCRATCH_ACTIONS = [
    "cut to scratch",
    "split vertically and run",
    "split horisontally and run",
]

FULL_SCRATCH_ACTIONS = [
    "paste from scratch",
    "split vertically and paste",
    "split horisontally and paste",
]

AUX_ACTIONS = [
    "set split layout",
    "set tabbed layout",
    "set stacked layout",
    "close window",
    "exit i3",
]

def async_con(actions):
    cmd = DMENU_ARGS + DMENU_ACTIONS_ARGS
    input_action = None
    with TemporaryFile("w") as temp:
        temp.write(actions)
        temp.seek(0)
        try:
            input_action = check_output(cmd, stdin=temp)
        except CalledProcessError:
            return False
    if not input_action:
        return False
    input_action = str(input_action, 'utf-8').rstrip()
    actions_map = {
        MAIN_ACTIONS[0]: fullscreen,
        MAIN_ACTIONS[1]: floating,
        EMPTY_SCRATCH_ACTIONS[0]: cut,
        FULL_SCRATCH_ACTIONS[0]: paste,
        EMPTY_SCRATCH_ACTIONS[1]: vertical_split_and_run,
        EMPTY_SCRATCH_ACTIONS[2]: horisontal_split_and_run,
        FULL_SCRATCH_ACTIONS[1]: vertical_split_and_paste,
        FULL_SCRATCH_ACTIONS[2]: horisontal_split_and_paste,
        AUX_ACTIONS[0]: split,
        AUX_ACTIONS[1]: tabbed,
        AUX_ACTIONS[2]: stacking,
        AUX_ACTIONS[3]: close,
        AUX_ACTIONS[4]: exit_i3,
    }
    actions_map[input_action]()


def con_actions():
    scratch = get_scratch()
    leaves = scratch.leaves()
    actions = []
    actions += MAIN_ACTIONS
    if len(leaves) > 0:
        actions += FULL_SCRATCH_ACTIONS
    else:
        actions += EMPTY_SCRATCH_ACTIONS
    actions += AUX_ACTIONS
    actions = "\n".join(actions)

    thread = threading.Thread(
        target=async_con, args=(actions,)
    )
    thread.daemon = True
    thread.start()


# create and listen fifo
# usage:
# echo command_name > /path/to/fifo

def clean(*args):
    try:
        os.remove(FIFO)
    except OSError:
        pass
    else:
        print("FIFO deleted")


clean()


for sig in (SIGABRT, SIGILL, SIGINT, SIGSEGV, SIGTERM):
    signal(sig, clean)


try:
    os.mkfifo(FIFO)
except OSError as oe:
    if oe.errno != errno.EEXIST:
        raise


LMB = 1
RMB = 3


while True:
    cmd = ""
    print("Opening FIFO...")
    with open(FIFO) as fifo:
        print("FIFO opened")
        while True:
            data = fifo.read()
            if len(data) == 0:
                print("Writer closed")
                # break loop in order to do not load cpu
                break
            else:
                cmd = data.rstrip()
    # process commands to fifo
    print(cmd)
    if cmd == "menu_block %s" % LMB or cmd == "exec":
        was_dmenu_running() or execute_command()
    elif cmd == "menu_block %s" % RMB or cmd == "rename_workspace":
        was_dmenu_running() or rename_workspace()
    elif cmd == "move_block %s" % LMB or cmd == "smart_create":
        create_workspace()
        smart_run()
    elif cmd == "move_block %s" % RMB or cmd == "move_to_new":
        move_to_new_workspace()
    elif cmd == "con_block %s" % LMB:
        was_dmenu_running() or con_actions()
    elif cmd == "con_block %s" % RMB or cmd == "smart_fullscreen":
        smart_fullscreen()
    elif cmd == "create_workspace":
        create_workspace()
    elif cmd == "exit_i3":
        exit_i3()
    elif cmd == "scratch_to_from":
        scratch_to_from()
    elif cmd == "smart_run":
        smart_run()
    elif cmd == "reconnect":
        reconnect()
    else:
        pass




