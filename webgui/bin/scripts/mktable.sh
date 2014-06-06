#!/bin/sh
# removes the old db file and initializes/populates a new one
set -u

: ${PYTHON:=python3.3}

rm -vf -- ./db.sqlite3
${PYTHON} ./manage.py syncdb
./bin/debug/populate_db
