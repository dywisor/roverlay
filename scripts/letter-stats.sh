#!/bin/bash
: ${DIST:=./distfiles-root/CRAN}

c= n=
for c in {a..z} {0..9}; do
	n=`2>/dev/null ls -1 "$DIST"/{${c},${c^^}}* | wc -l`
	[[ -z "$n" ]] || [[ $n -eq 0 ]] || echo -e "${n}\t${c}"
done | sort -n
