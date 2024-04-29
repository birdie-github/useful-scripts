#! /bin/bash

# 2024-03-20 20:12:41 - first release
# 2024-04-28 23:21:29 - simplify and improve, rewrite in pure bash

# "default" is specified but doesn't work, wtf?
modes='performance|balance_performance|balance_power|power'

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

if [[ "$1" =~ $modes && "$now" != "$1" ]]; then
    setter "$1"
elif [ "$1" = "switch" ]; then
    if [[ "$now" =~ "power" ]]; then
        setter performance
    else
        setter power
    fi
elif [ -z "$1" ]; then
    echo "Use is: `basename $0` [$modes|switch]"
else
    echo "There's nothing to do"
fi
