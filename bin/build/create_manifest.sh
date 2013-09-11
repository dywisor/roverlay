#!/bin/sh -xeu
SCRIPTS=""
SCRIPT_DIRS="bin/install"
FILES="README"
PYDIRS="roverlay"

# config files, docs?

[ -x setup.py ]
echo setup.py

for x in $SCRIPTS; do
	[ -x "$x" ]
	echo "$x"
done

for x in ${SCRIPT_DIRS}; do
   find "$x" -executable -type f -print
done

for x in $FILES; do
	[ -e "$x" ]
	echo "$x"
done

for x in $PYDIRS; do
	[ -d "$x" ]
	find "$x" -name '*.py' -print
done
