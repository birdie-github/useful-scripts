# Probably useful scripts

## btc2usd
A shell script, which could also be used under XFCE via a generic monitor applet, to show the current bitcoin exchange rate in United States dollars (USD) fetched from CoinDesk. Requires a jq utility (can be installed in deb distros using `sudo apt-get install jq` or in RPM distros using `sudo yum install jq`).

## Firefox-updater
If you're unwilling to let your user account update Firefox (it's a little bit unsafe) I've created a script for this situation which you may put in crontab. This script automatically updates the official Linux x86-64 Firefox distribution installed on your PC. Currently it's only tested to work with Firefox ~58. It might break in the future because Firefox' version string is not easy to extract.
