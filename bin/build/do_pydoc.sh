#!/bin/sh -xe

into="${1:?}"

cd "$into"
[ -e ./roverlay ]

find roverlay/ -name "*.py" | \
	sed -e 's,\/,.,g' -e 's,[.]__init__[.]py$,,' -e 's,[.]py$,,' | \
	xargs pydoc -w && \
	ln -fs roverlay.html index.html && \
	rm -f -- roverlay

