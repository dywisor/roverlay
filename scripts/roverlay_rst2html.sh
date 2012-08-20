#!/bin/bash -u
usage() { echo "usage: $0 <rst file> <html file>"; exit 1; }

[[ $# -eq 2 ]] || usage

from="${1}"
to="${2}"

[[ -r "${from}" ]] || usage

TITLE='Automatically Generated Overlay of R packages'

rst2html.py --title "${TITLE}" --date "${from}" "${to}"
