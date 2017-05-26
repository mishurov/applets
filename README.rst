===========
GTK Applets
===========

Python2 scripts used with openbox and tint2. Also code may be adapted for use as i3 status apps and so on.

Dependencies (Gentoo)
---------------------

* dev-python/pygobject
* dev-python/pygtk
* dev-python/libwnck-python
* x11-libs/libwnck
* app-misc/jq

Tray applets
============

.. image:: http://mishurov.usite.pro/github/applets/tray.png
    :alt: tray applets screenshot
    :align: center

**Volume applet** uses gtk3 and ctypes calls to pulsaudio.

**Keyboard applet** uses gtk3, ctypes and xcb http://xcb.freedesktop.org/ with xkb extension http://www.x.org/wiki/XKB/ (enabled by default on most systems). I don't use xpyb, because it too old and some people claims that it has memory leaks. Text rendered with Cairo.

WM Daemon
=========

.. image:: http://mishurov.usite.pro/github/applets/maximus.png
    :alt: feh screenshot
    :align: center

1. Acts as **Maximus**. On every "maximize" event undecorates window and turns on decorations when window being restored.
2. Adds icon (tray and window title) for every new **feh** window.

**Note:** you can use "mouse_right = maximize_restore" in **tint2rc** file to restore maximized windows with mouse. It uses gtk2 because python GI is still buggy with wnck and assigning icons.

Hot Corners
===========
Daemon uses ctypes and xcb with record extension http://xcb.freedesktop.org/manual/group__XCB__Record__API.html. Executes commands on mouse clicks on edges of screen. I use right click on top to exit fullscreen mode and clicks on right and left edges to switch between workspaces.

Calendar
========

.. image:: http://mishurov.usite.pro/github/applets/calendar.png
    :alt: calendar screenshot
    :align: center

Simple gtk3 Calendar application. I use it on click on clock in tint2.

i3 wm zoom patch
================

.. image:: http://mishurov.usite.pro/github/applets/i3_patch.png
    :alt: i3_patch screenshot
    :align: center

Patch to enable tmux-like "zoom" mode - maximize container and don't hide i3bar. And shell script (**smart_fullscreen.sh**) which zooms/fullscreens (in or out depending on state) whole stacked and tabbed layouts instead of particular focused container.
Daemon **zoom_bar_d.py** marks workspaces with zoomed windows. You can run it in i3 config 'exec_always --no-startup-id python2 ~/.config/i3/scripts/zoom_bar_d.py', 'exec_always' instead 'exec' because on reloading i3 ipc-socket may be changed.

**Workspace switch patch** There's also another patch file, whitch changes behaviour of "next_on_output" and
"prev_on_ouput" commands, it swithes to the first workspace on the next output from the last workspace on the current output and vice versa. It's added to the Gentoo ebuild and the shell script.

i3 wm zoom patch
================



.. code-block:: bash

    git clone https://github.com/mishurov/applets
    cd applets/i3patch
    git clone https://github.com/i3/i3
    cd i3
    git checkout 4.10.4
    git apply ../files/add_zoom_i3_4.10.4.patch
    git apply ../files/workspace_switch_i3_4.10.4.patch
    make
    sudo make install


**Gentoo** (local ebuild)

.. code-block:: bash

    git clone https://github.com/mishurov/applets
    cd applets/i3patch
    sudo mkdir -p /usr/local/portage/x11-wm/i3
    sudo cp ./i3-4.13-r1.ebuild /usr/local/portage/x11-wm/i3
    sudo cp -r ./files /usr/local/portage/x11-wm/i3
    sudo ebuild /usr/local/portage/x11-wm/i3/i3-4.13-r1.ebuild manifest clean merge
    echo "x11-wm/i3::gentoo" | sudo tee --append /etc/portage/package.mask

**FreeBSD** (custom port)

.. code-block:: bash

    git clone https://github.com/mishurov/applets
    cd applets/i3patch
    sudo cp -r ./files ./freebsd/
    cd ./freebsd
    make install clean
    # and place "freebsd" directory to your sources location


Drafts
======
Directory **drafts** contains various attempts to make applets with gtk3 python binding, using subprocess to run background daemons, handle UNIX signals in gtk3 and so on.
