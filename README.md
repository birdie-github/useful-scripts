# Probably useful scripts

## [btc2usd](https://raw.githubusercontent.com/birdie-github/useful-scripts/master/btc2usd)
A shell script which shows the current bitcoin exchange rates for CoinDesk.com and CoinMarketCap.com in the United States dollars (USD). Requires the jq utility (can be installed in deb distros using `sudo apt-get install jq` or in RPM distros using `sudo yum install jq`). It could also be used under XFCE via the generic monitor applet.

## [Firefox-updater](https://raw.githubusercontent.com/birdie-github/useful-scripts/master/Firefox-updater)
If you're unwilling to let your user account update Firefox (it's a little bit unsafe) I've created a script for this situation which could be added in a crontab. This script automatically updates the official Linux x86-64 Firefox distribution installed on your PC. It currently supports the ESR, stable and beta channels.

## [clean_dnf](https://raw.githubusercontent.com/birdie-github/useful-scripts/master/clean_dnf)
Ever wanted to get rid of useless/unnecessary/redundant RPMs lying on your disk? There's a script for that which uses DNF. Run it without arguments to walk through all the installed packaged, or give it a single argument (I may fix it to accept any number of packages) to check whether other packages depend on it. It will skip the RPMs which result in the removal of protected packages like DNF itself.

## [monitor_oc.sh](https://github.com/birdie-github/useful-scripts/blob/master/monitor_oc.sh)
This script allows you to overclock your monitor (refresh rate/frequency) under Linux. It was created specifically for my sole monitor, so you'll have to adjust it if yours is different. Modifications to /etc/X11/xorg.conf.d/conf.conf are [required](https://devtalk.nvidia.com/default/topic/1054885/linux/monitor-refresh-frequency-overclocking-in-linux-is-not-available/).
