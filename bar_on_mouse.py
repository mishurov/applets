#!/usr/bin/python3

# sudo apt install python3-xlib
import time
from Xlib import display, X, protocol
from Xlib.ext import record, xtest


BAR_POSITION = 'bottom'
SAFE_AREA_MULT = 2.5

# Num Lock (Mod2) for i3bar settings
# emulate key press and release to display the bar
NUM_LOCK_KEYSYM = 0xff7f
# Alt (Mod1) + Shift + Arrows are keybindings to switch desktop
# show the bar when they're pressed
MODIFIER_MASK = X.Mod1Mask | X.ShiftMask
LEFT_KEYSYM = 0xff51
RIGHT_KEYSYM = 0xff53
ALT_L_KEYSYM = 0xffe9
SHIFT_L_KEYSYM = 0xffe1


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


def handler(reply):
    global bar_is_visible
    global bar_hiding_started
    global alt_is_pressed
    global win_is_pressed
    data = reply.data
    while len(data):
        event, data = protocol.rq.EventField(None).parse_binary_value(
            data, display_glob.display, None, None)

        if (not bar_is_visible
            and event.type == X.KeyPress
            and (event.state & MODIFIER_MASK) == MODIFIER_MASK
            and event.detail in arrow_keycodes):
            send_numlock()
            bar_is_visible = True
            continue

        if (bar_is_visible
            and event.type == X.KeyRelease
            and (event.state & MODIFIER_MASK) < MODIFIER_MASK
            and event.detail in mod_keycodes
            and bar_test(event.root_y)):
            send_numlock()
            bar_is_visible = False
            continue

        if event.type != X.MotionNotify:
            continue

        if not bar_is_visible and event.root_y == edge:
            send_numlock()
            bar_is_visible = True
            continue

        if bar_is_visible and bar_test(event.root_y):
            send_numlock()
            bar_is_visible = False


if __name__ == '__main__':
    display_glob = display.Display()
    screen_height = display_glob.screen().root.get_geometry().height
    bar_height = find_bar(display_glob).get_geometry().height
    bar_height = int(bar_height * SAFE_AREA_MULT)
    barless_height = screen_height - bar_height

    edge = screen_height - 1 if BAR_POSITION == 'bottom' else 0
    bar_test = ((lambda y: y > bar_height) if BAR_POSITION == 'top' else
                (lambda y: y < barless_height))

    numlock_keycode = display_glob.keysym_to_keycode(NUM_LOCK_KEYSYM)
    arrow_keycodes = [
        display_glob.keysym_to_keycode(LEFT_KEYSYM),
        display_glob.keysym_to_keycode(RIGHT_KEYSYM)
    ]
    mod_keycodes = [
        display_glob.keysym_to_keycode(ALT_L_KEYSYM),
        display_glob.keysym_to_keycode(SHIFT_L_KEYSYM)
    ]
    bar_is_visible = False

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
