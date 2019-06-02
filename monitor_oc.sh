#! /bin/bash

# Jun  2 03:00 2019

name=1920x1080_74.00

test -n "`xrandr | grep $name`" && echo "$name already added" && exit 1

output=`xrandr | awk '/ connected/{print $1}'`
echo "Output: $output"

mode=`cvt 1920 1080 74 | grep Modeline | sed 's/Modeline //;s/"//g'`
echo "Modeline: $mode"

echo -n "Creating a new mode $mode ... "
xrandr --newmode $mode && echo OK || exit 1

echo -n "Adding mode $name to $output ... "
xrandr --addmode $output $name && echo OK || exit 1

echo -n "Activating mode $name for $output ... "
xrandr --output  $output --mode $name && echo OK
