import threading
from Xlib import display, X, XK, protocol
from Xlib.ext import record


RANGE_PRESS = (X.KeyPress, X.KeyPress)
RANGE_RELEASE = (X.KeyRelease, X.KeyRelease)
RANGE_BOTH = (X.KeyPress, X.KeyRelease)


class X11GlobalKeyListener(object):
    def __init__(self, keysyms=[], callback=None, event_range=RANGE_PRESS):
        if callback is not None:
            self.callback = callback
        else:
            self.callback = lambda x, y: print('type: {}, sym: {}'.format(x, y))
        self.event_range = event_range
        self.display = display.Display()
        self.keycodes = [self.display.keysym_to_keycode(k) for k in keysyms]
        thread = threading.Thread(target=self.start_listening)
        thread.daemon = True
        thread.start()

    def start_listening(self):
        ctx = self.display.record_create_context(
            0,
            [record.AllClients],
            [{
                'core_requests': (0, 0),
                'core_replies': (0, 0),
                'ext_requests': (0, 0, 0, 0),
                'ext_replies': (0, 0, 0, 0),
                'delivered_events': (0, 0),
                'device_events': self.event_range,
                'errors': (0, 0),
                'client_started': False,
                'client_died': False,
            }]
        )
        self.display.record_enable_context(ctx, self.handler)
        self.display.record_free_context(ctx)

        while True:
            self.display.next_event()

    def handler(self, reply):
        data = reply.data
        while len(data):
            event, data = protocol.rq.EventField(None).parse_binary_value(
                data, self.display.display, None, None)
            if (event.type not in self.event_range
                or event.detail not in self.keycodes):
                return
            event_type = 'press' if event.type == X.KeyPress else 'release'
            keysym = self.display.keycode_to_keysym(event.detail, 0)
            self.callback(keysym, event_type)
