=======
Applets
=======

Python scripts for openbox and tint2. The code also may be adapted as i3 status apps and so forth.

Dependencies (Gentoo)
---------------------

* dev-python/pygobject
* dev-python/pygtk
* dev-python/libwnck-python
* x11-libs/libwnck
* app-misc/jq

Tray applets
============

.. image:: http://mishurov.co.uk/images/github/applets/tray.png
    :alt: tray applets screenshot
    :align: center

**Volume applet** uses gtk3 and ctypes calls to pulsaudio.

**Keyboard applet** uses gtk3, ctypes and xcb http://xcb.freedesktop.org/ with the xkb extension http://www.x.org/wiki/XKB/ (enabled by default on the most systems). I don't use xpyb, because it is too old and some people claim that it has memory leaks. The text icons are rendered with Cairo.

WM Daemon
=========

.. image:: http://mishurov.co.uk/images/github/applets/maximus.png
    :alt: feh screenshot
    :align: center

1. Acts as **Maximus**. On every "maximize" event it undecorates window and turns on decorations when window is restored.
2. Adds an icon (tray and window title) for every new **feh** window.

**Note:** you can use "mouse_right = maximize_restore" in a **tint2rc** file to restore maximized windows with mouse. It uses gtk2 because python GI is still buggy with wnck and assigning icons.

Hot Corners
===========
The daemon uses ctypes and xcb with record extension http://xcb.freedesktop.org/manual/group__XCB__Record__API.html. It executes commands on mouse clicks at edges of a screen. I use a right click on the top of a screen to exit the fullscreen mode and clicks on the right and left edges to switch between workspaces.

Calendar
========

.. image:: http://mishurov.co.uk/images/github/applets/calendar.png
    :alt: calendar screenshot
    :align: center

A simple gtk3 Calendar application. I use it on click on the clock in the tint2 panel.

i3 wm zoom patch
================

.. image:: http://mishurov.co.uk/images/github/applets/i3_patch.png
    :alt: i3_patch screenshot
    :align: center

A patch to enable a tmux-like "zoom" mode: to maximize a container and to don't hide an i3bar. The daemon **daemon.py** marks the workspaces containing zoomed windows. You can start it in an i3 config 'exec --no-startup-id python /path/to/daemon.py', to reconnect in case an ipc socket was changed 'echo reconnect > /path/to/daemons/fifo'. It uses "i3ipc-python" package with the "zoomed" property added.

**Workspace switch patch** There's also another patch file, which changes the behaviour of "next_on_output" and
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

**Debian Jessie-backports**

.. code-block:: bash

  apt-get install -y \
  devscripts \ 
  dh-autoreconf \
  libxcb-util0-dev \
  libxcb-keysyms1-dev \
  libxcb-xinerama0-dev \
  libxcb-icccm4-dev \
  libxcb-cursor-dev \
  libxcb-xrm-dev \
  libxcb-xkb-dev \
  libxkbcommon-x11-dev \
  asciidoc \
  xmlto \
  docbook-xml \
  libev-dev \
  libyajl-dev \
  libstartup-notification0-dev \
  libcairo2-dev
  
  git clone https://github.com/mishurov/applets
  mkdir i3wm
  cd i3wm
  
  wget http://http.debian.net/debian/pool/main/i/i3-wm/i3-wm_4.13.orig.tar.bz2
  tar xf i3-wm_4.13.orig.tar.bz2
  rm i3-wm_4.13.orig.tar.bz2
  cd i3-4.13
  git apply ../../applets/i3patch/files/add_zoom_i3_4.13.patch
  cd ..
  tar -cvjSf i3-wm_4.13.orig.tar.bz2 i3-4.13

  wget http://http.debian.net/debian/pool/main/i/i3-wm/i3-wm_4.13-1~bpo8+1.debian.tar.xz
  tar xf i3-wm_4.13-1\~bpo8+1.debian.tar.xz
  mv debian i3-4.13
  cd i3-4.13

  dpkg-buildpackage -uc -us

  cd ..

  sudo apt-get remove i3
  sudo dpkg -i i3-wm_4.13-1\~bpo8+1_amd64.deb
  sudo apt-get -t jessie-backports install i3

PyQT
======

.. image:: http://mishurov.co.uk/images/github/applets/pyqt.png
    :alt: pyqt screenshot
    :align: center

Simple boilerplates for PyQT 5

Drafts
======
The directory **drafts** contains the various attempts to make the applets with the diffrerent python and gtk versions, using subprocess to run background daemons, alsa instead of pulseaudio, handle UNIX signals in gtk3 and so forth.
