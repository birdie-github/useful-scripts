#! /bin/bash

echo "Enabling power savings via ryzenadj and /sys ..."

# 2023-08-07 00:46:52
# 2023-08-10 14:15:30 + lots more limits
/usr/local/bin/ryzenadj --tctl-temp=75 --power-saving --stapm-limit=30000 --fast-limit=30000 --slow-limit=20000 2>&1 | grep -v SMU

# force GPU power savings
device=/sys/class/graphics/fb0/device/power_dpm_force_performance_level
test -f $device && echo "low > $device" && echo low > $device
