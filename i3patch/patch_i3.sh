#!/bin/sh

git clone https://github.com/i3/i3
cd i3
git checkout 4.10.4
git apply ../add_zoom_i3_4.10.4.patch
make
make install
