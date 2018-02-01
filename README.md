# Probably useful scripts

## [btc2usd](https://raw.githubusercontent.com/birdie-github/useful-scripts/master/btc2usd)
A shell script, which could also be used under XFCE via a generic monitor applet, to show the current bitcoin exchange rate in United States dollars (USD) fetched from CoinDesk. Requires a jq utility (can be installed in deb distros using `sudo apt-get install jq` or in RPM distros using `sudo yum install jq`).

## [Firefox-updater](https://raw.githubusercontent.com/birdie-github/useful-scripts/master/Firefox-updater)
If you're unwilling to let your user account update Firefox (it's a little bit unsafe) I've created a script for this situation which you may put in crontab. This script automatically updates the official Linux x86-64 Firefox distribution installed on your PC. It currently supports the ESR, stable and beta channels. It might break in the future because Firefox' version string is not easy to extract.

## [clean_dnf](https://raw.githubusercontent.com/birdie-github/useful-scripts/master/clean_dnf)
Ever wanted to get rid of useless/unnecessary/redundant RPMs lying on your disk? There's a script for that which uses DNF. Run it without arguments to walk through all the installed packaged, or give it a single argument (I may fix it to accept any number of packages) to check whether other packages depend on it. It will skip the RPMs which result in the removal of protected packages like DNF itself.
