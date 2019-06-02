#! /bin/bash

# Jun  2 03:00 2019

# Adjust according to your needs
width=1920
height=1080
freq=74

name=${width}x${height}_${freq}.00

test -n "`xrandr | grep $name`" && echo "$name is already added" && exit 1

# Specifically for the first monitor
output=`xrandr | awk '/ connected/{print $1}' | head -1`
echo "Output: $output"

# Adjust according to your needs
mode=`cvt $width $height $freq | grep Modeline | sed 's/Modeline //;s/"//g'`
echo "Modeline: $mode"

echo -n "Creating a new mode $mode ... "
xrandr --newmode $mode && echo OK || exit 1

echo -n "Adding mode $name to $output ... "
xrandr --addmode $output $name && echo OK || exit 1

echo -n "Activating mode $name for $output ... "
xrandr --output  $output --mode $name && echo OK

echo
echo "Use these two commands to undo the changes (*after* setting the normal refresh rate):"
echo "xrandr --delmode $output $name"
echo "xrandr --rmmode 1920x1080_74.00"
