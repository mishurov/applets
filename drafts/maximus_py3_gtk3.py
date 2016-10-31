import os

import gi
gi.require_version('Wnck', '3.0')

from gi.repository import Wnck
from gi.repository import GLib
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GdkX11
from gi.repository import GdkPixbuf


FEH_ICON_PATH="/home/mishurov/.config/feh/icon.png"
CWD = os.path.dirname(os.path.abspath(__file__))
#FEH_ICON_PATH = CWD + "/../feh/icon.png"
#ZATHURA_ICON_PATH = CWD + "/../zathura/icon.png"


def window_wnck_to_gdk(window):
    xid = window.get_xid()
    gdk_display = GdkX11.X11Display.get_default()
    return GdkX11.X11Window.foreign_new_for_display(
        gdk_display, xid
    )


def maximus(window, changed_mask, new_state):
    mask_h = Wnck.WindowState.MAXIMIZED_HORIZONTALLY
    mask_v = Wnck.WindowState.MAXIMIZED_VERTICALLY
    mask_all = mask_h | mask_v

    if changed_mask in (mask_all, mask_h, mask_v):
        gdk_window = window_wnck_to_gdk(window)
        if new_state == changed_mask:
            gdk_window.set_decorations(0)
        elif new_state == 0:
            gdk_window.set_decorations(Gdk.WMDecoration.ALL)


def set_win_icon(window, path):
    pixbuf = GdkPixbuf.Pixbuf.new_from_file(path)
    gdk_window = window_wnck_to_gdk(window)
    #gdk_window.set_icon_list([pixbuf,])


def on_window_opened(screen, window):
    window.connect('state-changed', maximus)
    win_class = window.get_class_group().get_res_class()
    if win_class == "feh":
        set_win_icon(window, FEH_ICON_PATH)
    elif win_class in ["Zathura", "llpp"]:
        set_win_icon(window, ZATHURA_ICON_PATH)


if __name__ == "__main__":
    screen = Wnck.Screen.get_default()
    screen.connect("window_opened", on_window_opened)
    GLib.MainLoop().run()


