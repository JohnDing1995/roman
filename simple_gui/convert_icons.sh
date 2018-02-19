#!/bin/sh -e

png2icns roman.icns roman.png

convert roman.png  -bordercolor white -border 0 \
	\( -clone 0 -resize 16x16 \) \
	\( -clone 0 -resize 32x32 \) \
	\( -clone 0 -resize 48x48 \) \
	\( -clone 0 -resize 256x256 \) \
	-delete 0 -alpha off -colors 256 \
	roman.ico
