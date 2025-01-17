#! /bin/bash
#----------------------------------------------------------------------
# Description: updates installed firmware files
# Author: Artem S. Tashkinov
# Created at: Fri Jan 17 02:00:30 2025
# Computer: elite
# System: Linux 6.12.6-200.fc41.x86_64 on x86_64
#
# Copyright (c) 2025 Artem S. Tashkinov  All rights reserved.
#
#----------------------------------------------------------------------

found=0
items=0

cd /lib/firmware || exit 1
sdir=/tmp/linux-firmware
test -n "$1" && sdir="$1"
test ! -d "$sdir" && echo "$sdir doesn't exist" && exit 2
test ! -f "$sdir/WHENCE" && echo "$sdir doesn't look like a directory with Linux firmware: WHENCE is missing" && exit 3

while read fname; do
    cur=`sha256sum < $fname`
    new=`sha256sum 2>/dev/null < $sdir/$fname` || continue
    items=$((items+1))
    if [ "$cur" != "$new" ]; then
        echo -n "Updating $fname ... "
        /bin/cp -a "$sdir/$fname" "$fname" && echo OK || exit 100
        chown 0:0 "$fname"
        chmod 755 "$fname"
        found=$((found+1))
    fi
done <<< "$(find . -type f)"

echo "Scanned $items firmware files"
test "$found" -eq 0 && echo "All the firmware is up to date" || echo "Updated $found firmware files"
