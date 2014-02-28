#!/bin/bash
#
# Script to update metadata caches.
# Run this at frequent intervals e.g. by daily crontab.
#
# -----------------------------------------------------

#set -u

export PYTHONPATH=${HOME}/seiscomp3/lib/python:${PYTHONPATH}
export PATH=/usr/local/bin:/usr/bin:/bin:${HOME}/seiscomp3/bin

# Check in which directory is this script located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

function show_usage() {
	echo "$0: update webinterface metadata cache(s)"
	cat <<EOF

Options:
  -h  : show this help.
  -v  : be verbose.
EOF
}


verbosity=0

while getopts ":v" opt; do
	case "$opt" in
		h)  show_usage
			exit 0
			;;
		v)  verbosity=1
			;;
		*)  show_usage
			exit 1
			;;
	esac
done

if [ $verbosity -gt 0 ]; then
    echo "Dir: $DIR"
    echo "Path: $PATH"
fi

cd $DIR

# Check for arclink_fetch in PATH
if ! hash arclink_fetch 2>/dev/null; then
    echo "ERROR: arclink_fetch was not found! Check your SeisComP environment variables."
    exit 1;
fi

# Retrieve inventory information from your local Arclink server
ADDRESS=eida.gfz-potsdam.de:18002
ARCLINKUSER="webinterface@$(hostname -f)"
if [ $verbosity -gt 0 ]; then
    echo "Requesting inventory from $ADDRESS with arclink_fetch as $ARCLINKUSER"
fi
YEAR=$(($(date +%Y)+1))
echo "1980,1,1,0,0,0 $YEAR,1,1,0,0,0 * * * * " | arclink_fetch -a $ADDRESS -u $ARCLINKUSER -k inv -o ./Arclink-inventory.download 2>&1 >./Arclink-inventory.out

status=$?
if [[ "$status" != "0" ]]; then
    echo "WARNING: arclink_fetch returned an error!"
    echo "stdout/stderr was:"
    cat ./Arclink-inventory.out
    exit $status
fi

if [[ -e "./Arclink-inventory.download" ]]
then
    # If there is old information, make a backup
    if [[ -e "./Arclink-inventory.xml" ]]; then
        cp ./Arclink-inventory.xml ./Arclink-inventory.old
    fi

    # Move the new data to the proper place, delete stale cache
    mv ./Arclink-inventory.download ./Arclink-inventory.xml
    rm -f ./webinterface-cache*
fi

wget -O ./eida.download "http://eida.gfz-potsdam.de/arclink/table?group=eida" >./wget.out 2>&1
status=$?
if [[ "$status" != "0" ]]; then
	echo "WARNING: wget returned an error!"
	echo "stdout/stderr was:"
	cat ./wget.out
	exit $status
fi

if [[ -e "./eida.download" ]]
then
    # If there is old information, make a backup
    if [[ -e "./eida.xml" ]]; then
        cp ./eida.xml ./eida.old
    fi

    # Move the new data to the proper place
    mv ./eida.download ./eida.xml
fi

