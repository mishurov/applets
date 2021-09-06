#!/usr/bin/python3

# sudo apt install python3-xlib
import time
import threading
from Xlib import display, X, protocol
from Xlib.ext import record, xtest


BAR_POSITION = 'bottom'

# Num Lock (Mod2) for i3bar settings
# emulate key press and release to display the bar
NUM_LOCK_KEYSYM = 0xff7f
# Alt (Mod1) + Shift + Arrows are keybindings to switch desktop
# show the bar when they're pressed
MODIFIER_MASK = X.Mod1Mask | X.ShiftMask
LEFT_KEYSYM = 0xff51
RIGHT_KEYSYM = 0xff53


def find_bar(display_arg):
    tree = display_arg.screen().root.query_tree()
    wins = tree.children
    bar = None
    for win in wins:
        try:
            name = win.get_wm_name()
        except:
            continue
        if (name and name.startswith('i3bar')):
            bar = win
            break
    return bar


def send_key_event(code, event_type):
    display_loc = display.Display()
    bar = find_bar(display_loc)
    xtest.fake_input(bar, event_type, code)
    display_loc.sync()


def send_numlock():
    send_key_event(numlock_keycode, X.KeyPress)
    send_key_event(numlock_keycode, X.KeyRelease)


def show_bar():
    global bar_is_visible
    if bar_is_visible:
        return
    #print('show')
    send_numlock()
    bar_is_visible = True


def bar_hide_task():
    global bar_is_visible
    global bar_hiding_started
    thread_event.clear()
    with thread_lock:
        bar_hiding_started = True
    thread_event.wait(2)
    if not bar_hiding_started:
        #print('terminate')
        return
    with thread_lock:
        #print('hide')
        send_numlock()
        bar_hiding_started = False
        bar_is_visible = False


def start_hiding_bar():
    global thread
    thread = threading.Thread(target=bar_hide_task)
    thread.start()


def stop_hiding_bar():
    global bar_hiding_started
    if not  bar_hiding_started:
        return
    with thread_lock:
        bar_hiding_started = False
    thread_event.set()
    if thread is not None and thread.is_alive():
        thread.join()



def handler(reply):
    global bar_is_visible
    global bar_hiding_started
    data = reply.data
    while len(data):
        event, data = protocol.rq.EventField(None).parse_binary_value(
            data, display_glob.display, None, None)

        # event.state may contain the sent Num Lock as well
        if (event.type == X.KeyPress
            and (event.state & MODIFIER_MASK) == MODIFIER_MASK
            and event.detail in arrow_keycodes
            and bar_test(event.root_y)):
            stop_hiding_bar()
            show_bar()
            start_hiding_bar()

        if event.type != X.MotionNotify:
            continue

        if (event.root_y == edge
            or (bar_hiding_started and not bar_test(event.root_y))):
            stop_hiding_bar()
            show_bar()

        if (bar_is_visible
            and not bar_hiding_started
            and bar_test(event.root_y)):
            stop_hiding_bar()
            start_hiding_bar()


if __name__ == '__main__':
    # TODO: configurable constants: delay etc
    display_glob = display.Display()
    screen_height = display_glob.screen().root.get_geometry().height
    bar_height = find_bar(display_glob).get_geometry().height
    bar_height = int(bar_height * 1.5)
    barless_height = screen_height - bar_height

    edge = screen_height - 1 if BAR_POSITION == 'bottom' else 0
    bar_test = ((lambda y: y > bar_height) if BAR_POSITION == 'top' else
                (lambda y: y < barless_height))

    numlock_keycode = display_glob.keysym_to_keycode(NUM_LOCK_KEYSYM)
    arrow_keycodes = [
        display_glob.keysym_to_keycode(LEFT_KEYSYM),
        display_glob.keysym_to_keycode(RIGHT_KEYSYM)
    ]
    bar_is_visible = False
    bar_hiding_started = False
    thread_lock = threading.Lock()
    thread_event = threading.Event()
    thread = None

    display_glob.flush()
    display_glob.sync()

    ctx = display_glob.record_create_context(
        0,
        [record.AllClients],
        [{
            'core_requests': (0, 0),
            'core_replies': (0, 0),
            'ext_requests': (0, 0, 0, 0),
            'ext_replies': (0, 0, 0, 0),
            'delivered_events': (0, 0),
            'device_events': (X.KeyPress, X.MotionNotify),
            'errors': (0, 0),
            'client_started': False,
            'client_died': False,
        }]
    )
    display_glob.record_enable_context(ctx, handler)
    display_glob.record_free_context(ctx)

    while True:
        display_glob.next_event()
