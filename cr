#! /bin/bash

# Too tired of remembering all the flags required to launch Google Chrome
# 2018-03-06 22:47:33

# 2021-04-17 17:32:06 a fix for 27" display

RES=`xdpyinfo | awk '/dimensions/{print $2}'`
extra=

if [ "$RES" == "2560x1440" ]; then
    extra=--force-device-scale-factor=1
    echo "Setting $extra"
fi

env TZ=USA/Pacific FREETYPE_PROPERTIES=truetype:interpreter-version=35 chrome --disk-cache-dir=/tmp/.chrome-cache $extra "$@"
