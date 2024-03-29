# Probably useful scripts

## [boost-tuner](https://raw.githubusercontent.com/birdie-github/useful-scripts/master/boost-tuner)
I'm not content that my Ryzen 3700 CPU boosts so often and so much while I'm simply browsing the web (governor: ondemand) which leads to the CPU operating at relatively high temperatures (45-60C, with an average run-of-the-mill air cooler and around 19C temperature in the room where I am) and voltages (1.5V voltage doesn't sound safe to me despite AMD assurance this voltage is 100% safe). The whole situation made me write the script which disables boost unless certain predefined processes are found to be running. At the moment I've allowed only compilation but you can add anything you want. To run it you may add it to `/etc/rc.d/rc.local`, e.g. this way:
`( sleep 60 && exec /root/bin/boost-tuner & ) &` # this is not to delay any further commands and probably to disable boost only after the user has logged on (60 seconds are more than enough to enter your password). It must be run under root. As a user you may force enable boost by creating /tmp/boost, e.g. `touch /tmp/boost`

## [btc2usd](https://raw.githubusercontent.com/birdie-github/useful-scripts/master/btc2usd)
A shell script which shows the current bitcoin exchange rates for CoinDesk.com and CoinMarketCap.com in the United States dollars (USD). Requires the jq utility (can be installed in deb distros using `sudo apt-get install jq` or in Fedora using `sudo dnf install jq`). It could also be used under XFCE via the generic monitor applet.

## [clean_dnf](https://raw.githubusercontent.com/birdie-github/useful-scripts/master/clean_dnf)
Ever wanted to get rid of useless/unnecessary/redundant RPMs lying on your disk? There's a script for that which uses DNF. Run it without arguments to walk through all the installed packaged, or give it a single argument (I may fix it to accept any number of packages) to check whether other packages depend on it. It will skip the RPMs which result in the removal of protected packages like DNF itself.

## [defrag](https://raw.githubusercontent.com/birdie-github/useful-scripts/master/defrag)
fast recursive defrag for ext4
* Fast recursive defragmentation for the specified directory residing on an ext4 filesystem; it doesn't support anything else
* ext4 doesn't allow to defrag free space, so it's impossible to fully defragment a filesystem if free space is fragmented and there are files larger than continuous chunks of free space
* If you want to defrag the root filesystem, start with `defrag /var`, then `defrag /` - files in var are usually heavily fragmented and need to be defragged first
* It's theoretically possible to fully defrag the ext4 filesystem: you first need to shrink it, then expand it. I will never recommend this as it's quite a dangerous operation and mustn't be performed without backing up first; in addition you cannot obviously do that on a mounted filesystem

## [Firefox-updater](https://raw.githubusercontent.com/birdie-github/useful-scripts/master/Firefox-updater)
If you're unwilling to let your user account update Firefox (it's a little bit unsafe) I've created a script for this situation which could be added in a crontab. This script automatically updates the official Linux x86-64 Firefox distribution installed on your PC. It currently supports the ESR, stable and beta channels.

## [monitor_overclock](https://raw.githubusercontent.com/birdie-github/useful-scripts/master/monitor_overclock)
This script allows you to overclock your monitor (refresh rate/frequency) under Linux. It was created specifically for my sole monitor, so you'll have to adjust it if yours is different. Modifications to /etc/X11/xorg.conf.d/conf.conf are [required](https://devtalk.nvidia.com/default/topic/1054885/linux/monitor-refresh-frequency-overclocking-in-linux-is-not-available/).

## [watch_raw_io](https://raw.githubusercontent.com/birdie-github/useful-scripts/master/watch_raw_io)
Monitor input/output read/write nicely formatted stats for all block devices/disks in the system in real time in Linux. Takes a single argument: a refresh interval which is 2 seconds by default. Works under a normal (non-root) user as well.

## Bottom line

To be honest I have close to a hundred such scripts but many of them are either silly or useful only for me. I publish them elsewhere.

## SAST Tools

[PVS-Studio](https://pvs-studio.com/pvs-studio/?utm_source=website&utm_medium=github&utm_campaign=open_source) - static analyzer for C, C++, C#, and Java code.
