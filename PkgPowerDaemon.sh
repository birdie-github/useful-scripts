#!/usr/bin/env bash

set -o pipefail

: "${INTERVAL:=0.999}"

if ! printf "%f" "$INTERVAL" >/dev/null 2>&1; then
    echo "'$INTERVAL' is an invalid float, bailing out"
    exit 1
fi

if [ -z "$SYSTEMD_EXEC_PID" ]; then
    echo "This script is not intended to be run directly"
    exit 1
fi

echo "Running with interval '$INTERVAL'"

while :; do
    data="⚙ $(turbostat --quiet --num_iterations 1 --interval "$INTERVAL" --show PkgWatt --Summary | tail -1 | tr -d '\n')W"
    printf "%s\n" "$data" > /run/cpu/power || exit 100
done
