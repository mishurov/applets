#!/bin/bash

set -e

if [ $# -ne 1 ]; then
	echo "Usage:   svg2icns filename.svg [filename2.svg...]"
	exit 100
fi
if [ ! -e "/usr/bin/iconutil" ]; then
	echo "/usr/bin/iconutil required (are you on macOS?)."
	exit 1
fi
if [ ! -e "/usr/bin/sips" ]; then
	echo "/usr/bin/sips required (are you on macOS?)."
	exit 1
fi

inkscape="/usr/local/bin/inkscape"

SIZES="
16,16x16
32,16x16@2x
64,32x32@2x
128,128x128
256,128x128@2x
512,256x256@2x
1024,512x512@2x
"

for SVG in "$@"; do
	BASE=$(basename "$SVG" | sed 's/\.[^\.]*$//')
	ICONSET="$BASE.iconset"
	echo "processing: $SVG"
	mkdir -p "$ICONSET"
	# Blah
	if [ -e "$inkscape" ]; then
		$inkscape -w 1024 -h 1024 "$SVG" --export-filename "$ICONSET"/icon_512x512@2x.png
	else
		echo "svg2icns depends on inkscape."
		echo "brew install inkscape"
		exit 1
	fi
	for PARAMS in $SIZES; do
		SIZE=$(echo $PARAMS | cut -d, -f1)
		LABEL=$(echo $PARAMS | cut -d, -f2)
		sips -z $SIZE $SIZE "$ICONSET"/icon_512x512@2x.png --out "$ICONSET"/icon_$LABEL.png
	done
	cp "$ICONSET/icon_16x16@2x.png" "$ICONSET/icon_32x32.png"
	cp "$ICONSET/icon_128x128@2x.png" "$ICONSET/icon_256x256.png"
	cp "$ICONSET/icon_256x256@2x.png" "$ICONSET/icon_512x512.png"
	iconutil -c icns "$ICONSET"
	#rm -rf "$ICONSET"
done
