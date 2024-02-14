#! /bin/bash

# 2023-08-07 00:46:52 - created
# 2023-08-10 14:15:30 - lots more limits
# 2023-08-12 20:11:58 - let's add a delay because --power-saving doesn't always work otherwise
# 2023-08-21 20:16:20 - tune for console and rc.d
# 2023-11-02 09:25:35 - setting for running on battery power
# 2023-11-16 15:45:27 - rewrite
# 2023-11-24 20:06:52 - dump the defaults to /dev/shm/AMD
# 2023-11-29 09:53:29 - remove --power-saving, it breaks the CPU up on resume
# 2023-12-29 22:25:19 - restore --power-saving, firmware is broken regardless
# 2024-02-11 18:00:14 - since 6.7 /sys/class/graphics/fb0 is missing, adjusting accordingly
delay=60

binary=/usr/local/bin/ryzenadj

gpupower()
{
    gpl=device/power_dpm_force_performance_level
    gpudev=/sys/class/graphics/fb0/$gpl
    test -f $gpudev || gpudev=/sys/class/drm/card1/$gpl
    test -f $gpudev || gpudev=/sys/class/drm/card0/$gpl
    if [ -f $gpudev ]; then
        echo "$1" > $gpudev && ( echo -n "Setting GPU performance to: " && cat $gpudev ) || echo "Failed!"
    else
        echo "iGPU [ $gpudev ] is missing!"
    fi
}

conf()
{
    if [ -z "$1" ]; then
        echo "Mains settings:"
        $binary --tctl-temp=75 --power-saving --stapm-limit=30000 --fast-limit=30000 --slow-limit=20000 2>&1 | grep -v SMU
        gpupower auto
    else # with any second argument, i.e. "battery"
        echo "Battery settings:"
        $binary --tctl-temp=70 --power-saving --stapm-limit=15000 --fast-limit=15000 --slow-limit=10000 2>&1 | grep -v SMU
        echo "Enabling GPU low power, this limits RAM speed!"
        gpupower low
    fi

    true
}

test -f /dev/shm/AMD || $binary --info &> /dev/shm/AMD

echo "Enabling power savings via ryzenadj and /sys ..."
conf "$1"

if [ "$TERM" = "linux" -o "$TERM" = "xterm-256color" ]; then
    :
else
    echo "Second attempt in $delay seconds ..."
    ( sleep $delay; conf ) &
fi
