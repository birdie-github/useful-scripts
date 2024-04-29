#! /bin/bash

cpus=`ls /sys/devices/system/cpu/cpufreq/*/energy_performance_preference`
test -z "$cpus" && echo "WTF?" && exit 1

getter()
{
    cat $cpus | sort -u
}

setter()
{
    echo -n "Switching to: "
    echo "$1" | tee $cpus
    echo "Result: `getter`"
}

now=`getter`
echo "Now: $now"

if [ "$1" = "performance" -a "$now" != "performance" ]; then
    setter performance
elif [ "$1" = "power" -a "$now" != "power" ]; then
    setter power
elif [ "$1" = "switch" ]; then
    if [ "$now" = "power" ]; then
        setter performance
    else
        setter power
    fi
elif [ -z "$1" ]; then
    echo "Use is: `basename $0` [performance|power|switch]"
else
    echo "There's nothing to do"
fi
