#!/bin/bash

doit() {
	x="$1"
	echo "Processing $1"
	if [ -e "$x" ]; then
		python add_pho2opf.py "$x"
	else
		echo "file $x not found. Processing and reporting alternate file."
		find `dirname $x` -name '*.opf' -print -exec python add_pho2opf.py {} \; -quit
	fi
}


export -f doit

cat "$1" | parallel doit
