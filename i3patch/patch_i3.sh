#!/bin/sh

# clear install (has no option to uninstall ability)

git clone https://github.com/i3/i3
cd i3
git checkout 4.10.4
git apply ../files/add_zoom_i3_4.10.4.patch
make
make install

# gentoo custom portage

mkdir -p /usr/local/portage/x11-wm/i3
cp ./i3-4.10.4.ebuild /usr/local/portage/x11-wm/i3
cp -r ./files /usr/local/portage/x11-wm/i3
ebuild /usr/local/portage/x11-wm/i3/i3-4.10.4.ebuild \
manifest clean merge
