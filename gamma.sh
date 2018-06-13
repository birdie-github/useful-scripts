#! /bin/bash

current=`xgamma 2>&1 | awk '{print $7}'`

change()
{
    new=1
    if [ "$1" = "+" -o "$1" = "-" ]; then
        new=`echo "${current}${1}0.05" | bc -l`
    fi
    xgamma -gamma "$new" 2>/dev/null
    xmessage -timeout 1 "New gamma value : $new" 2>/dev/null &
}

case $1 in
    "+" | "-" | "0" )
        change $1
    ;;
    * )
        echo "`basename $0` +/-/0"
    ;;
esac
