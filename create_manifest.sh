#!/bin/sh -xe
SCRIPTS="roverlay.py"
FILES="README"
PYDIRS="roverlay"

# config files, docs?

[ -x setup.py ]
echo setup.py

for x in $SCRIPTS; do
	[ -x "$x" ]
	echo "$x"
done

for x in $FILES; do
	[ -e "$x" ]
	echo "$x"
done

for x in $PYDIRS; do
	[ -d "$x" ]
	find "$x" -name '*.py'
done
