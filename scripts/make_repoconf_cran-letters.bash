#!/bin/bash
#  Creates repo entries for packages from CRAN that
#  start with a specific letter.
# Usage: $0 word [word]...,
#  where the first char of each word is used
#  Automatically detects duplicates.
set +o history

TRUE=0
FALSE=1

[[ $# -gt 0 ]] || { 1>&2 echo "Usage: $0 word [word]..."; exit 2; }

_in() {
	local z
	for z in $*; do [[ "$kw" != "$z" ]] || return $TRUE; done
	return $FALSE
}

CHARS=""

first=y
for x in $*; do
	char="${x::1}"
	low="${char,,}"
	high="${char^^}"

	kw="$low" _in $CHARS && continue
	CHARS+=" $low"

	[[ -z "$first" ]] && echo || first=

	cat << END_REPO
[CRAN_test/letter_${high}]
# A repo that sync only packages starting with ${low} or ${high}

# repo's distdir is <distroot>/CRAN_test/letter_${high}
type             = rsync
rsync_uri        = cran.r-project.org::CRAN/src/contrib
src_uri          = http://cran.r-project.org/src/contrib
extra_rsync_opts = --progress --include=${low}* --include=${high}* --exclude=*
END_REPO
# @EOF >> cat
done
[[ "${CHARS# }" ]]
