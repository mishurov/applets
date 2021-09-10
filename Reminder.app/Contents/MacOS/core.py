import os
import re
import json
from datetime import datetime, timedelta


ALERT_TEXT = 'Alarm'
BUTTON_LABEL = 'Start'
EXIT_LABEL = 'Quit'
SPINBOX_WINDOW_TITLE = 'Reminder'

FILE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(FILE_DIR, '..', 'Resources')
ALARM_PATH = os.path.join(ASSETS_DIR, 'alarm-clock.svg')
ALARM_URGENT_PATH = os.path.join(ASSETS_DIR, 'alarm-clock-urgent.svg')
ALARM_ACTIVE_PATH = os.path.join(ASSETS_DIR, 'alarm-clock-active.svg')

HOME = os.environ.get("HOME")
CACHE_DIR = os.environ.get("XDG_CACHE_HOME", None) or os.path.join(HOME, ".cache")
REMINDER_FILE = os.path.join(CACHE_DIR, "reminder_data.json")


def str_to_timedelta(s):
    m = re.match(r'(?P<hours>\d+):(?P<minutes>\d+):(?P<seconds>\d[\.\d+]*)', s)
    kwargs = {key: float(val) for key, val in m.groupdict().items()}
    return timedelta(**kwargs)


class TimerMixin(object):
    start = None
    timedelta = None
    discount = {'hours': 0, 'minutes': 0, 'seconds': 0}

    def init_saved_alarm(self):
        if not os.path.isfile(REMINDER_FILE):
            open(REMINDER_FILE, "w").close()
        else:
            with open(REMINDER_FILE, "r") as reminder_file:
                data = reminder_file.read()
                if data:
                    data = json.loads(data)
                    self.start = datetime.fromisoformat(data['start'])
                    self.timedelta = str_to_timedelta(data['timedelta'])
                    self.set_icon(self.icon_active)

    def save_alarm(self):
        data = {
            'start': self.start.isoformat(),
            'timedelta': str(self.timedelta),
        }
        data = json.dumps(data, indent=4)
        with open(REMINDER_FILE, "w") as reminder_file:
            reminder_file.write(data)

    def clear_alarm(self):
        with open(REMINDER_FILE, "w") as reminder_file:
            reminder_file.write('')

    def start_timer(self, h, m, s):
        self.timedelta = timedelta(hours=h, minutes=m, seconds=s)
        self.start = datetime.now()
        self.save_alarm()
        self.set_icon(self.icon_active)

    def update_clock(self):
        if self.start is not None and self.timedelta is not None:
            t_time = '{hours:2d}:{minutes:02d}:{seconds:02d}'
        else:
            t_time = 'X:YY:ZZ'

        self.update_clock_text(t_time.format(**self.discount))

    def idle(self):
        if self.start is not None and self.timedelta is not None:
            td = datetime.now() - self.start
            if self.timedelta > td:
                td = self.timedelta - td
                self.discount.update({
                    'hours': int(td.seconds / 3600) % 24,
                    'minutes': int(td.seconds / 60) % 60,
                    'seconds': td.seconds % 60,
                })
            else:
                self.start = None
                self.timedelta = None
                self.discount.update({'hours': 0, 'minutes': 0, 'seconds': 0})
                self.set_icon(self.icon_urgent)
                self.show_popup()

            if self.is_menu_visible():
                self.update_clock()

        return True
