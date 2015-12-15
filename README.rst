===========
GTK Applets
===========

Python2 scripts used with openbox and tint2. Also code may be adapted for use as i3 status apps and so on.

Dependencies (Gentoo)
---------------------

* dev-python/pygobject
* dev-python/pygtk
* dev-python/pyalsa (for volume applet)
* dev-python/libwnck-python (for wm daemon)
* app-misc/jq (for i3 wm shell scripts, parse output)

**Note:** All applications use Python2. For example: Gentoo starts **python3** by default, to run applet, run **python2 /path/to/script.py**.

Tray applets
============

.. image:: https://dl.dropboxusercontent.com/u/20988720/github/applets/tray.png
    :alt: tray applets screenshot
    :align: center

**Volume applet** uses gtk2 and official python binding to alsa (python-pyalsa) http://www.alsa-project.org/ instead of python-alsaaudio, where you have to recreate every time mixer to get real volume value (not cached one). Reload mixer necessary when sink is changed, for example after bluetooth headphones connect.

**Keyboard applet** uses gtk2, ctypes and xcb http://xcb.freedesktop.org/ with xkb extension http://www.x.org/wiki/XKB/ (enabled by default on most systems). I don't use xpyb, because it too old and some people claims that it has memory leaks. Text rendered with Cairo.

WM Daemon
=========

.. image:: https://dl.dropboxusercontent.com/u/20988720/github/applets/maximus.png
    :alt: feh screenshot
    :align: center

1. Acts as **Maximus**. On every "maximize" event undecorates window and turns on decorations when window being restored.
2. Adds icon (tray and window title) for every new **feh** window.

**Note:** you can use "mouse_right = maximize_restore" in **tint2rc** file to restore maximized windows with mouse.

Hot Corners
===========
Daemon uses ctypes and xcb with record extension http://xcb.freedesktop.org/manual/group__XCB__Record__API.html. Executes commands on mouse clicks on edges of screen. I use right click on top to exit fullscreen mode and clicks on right and left edges to switch between workspaces.

Calendar
========

.. image:: https://dl.dropboxusercontent.com/u/20988720/github/applets/calendar.png
    :alt: calendar screenshot
    :align: center

Simple gtk3 Calendar application. I use it on click on clock in tint2.

i3 wm zoom patch
================

.. image:: https://dl.dropboxusercontent.com/u/20988720/github/applets/i3_patch.png
    :alt: i3_patch screenshot
    :align: center

Patch to enable tmux-like "zoom" mode - maximize container and don't hide i3bar. And shell script (**smart_fullscreen.sh**) which zooms/fullscreens (in or out depending on state) whole stacked and tabbed layouts instead of particular focused container

**Make (no uninstall target)**

.. code-block:: bash

    git clone https://github.com/mishurov/applets
    cd applets/i3patch
    git clone https://github.com/i3/i3
    cd i3
    git checkout 4.10.4
    git apply ../files/add_zoom_i3_4.10.4.patch
    make
    sudo make install


**Gentoo (local ebuild)**

.. code-block:: bash

    git clone https://github.com/mishurov/applets
    cd applets/i3patch
    sudo mkdir -p /usr/local/portage/x11-wm/i3
    sudo cp ./i3-4.10.4.ebuild /usr/local/portage/x11-wm/i3
    sudo cp -r ./files /usr/local/portage/x11-wm/i3
    sudo ebuild /usr/local/portage/x11-wm/i3/i3-4.10.4.ebuild manifest clean merge


Drafts
======
Directory **drafts** contains various attempts to make applets with gtk3 python binding, using subprocess to run background daemons, handle UNIX signals in gtk3 and so on.
