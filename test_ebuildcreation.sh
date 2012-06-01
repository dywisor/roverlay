#!/bin/bash
set -u
set -e
readonly ARGV="$*"
readonly _SELF="${0##*/}"
readonly _SELF_NAME="${_SELF%.*sh}"
readonly TEST_SECTION="${_SELF_NAME#test_}"
#
readonly py=${PYTHON:-python3}
#
_ROOT=`pwd`
if [[ ! -e "${_ROOT}/examples" ]]; then
	_ROOT="${_ROOT%/*}"
fi
readonly EXAMPLES="${_ROOT}/examples"
readonly PKGDIR="${EXAMPLES}/packages"


if [[ "${TEST_SECTION}" == "ebuildcreation" ]]; then
	if [[ "${1:-}" == "-q" ]]; then
		q=1
		shift ||:
	else q=0; fi

	declare -i multiply=${1:-1}
	[[ $multiply -gt 0 ]] || multiply=1
	pkgline=""
	pkgcount=0
	for x in "${PKGDIR}"/*.tar.gz "${PKGDIR}"/*.tgz; do
		if [[ -r "$x" ]]; then
			pkgline+=" ${x}"
			((pkgcount++)) ||:
		fi
	done
	pkgline="${pkgline# }"

	argline=""
	for i in `seq 1 $multiply`; do
		argline+=" ${pkgline}"
	done

	num=$(( $multiply * $pkgcount ))
	echo "Please note: python may return 'Argument list too long'. Double check your result if it's too fantastic to believe. (28500 pkgs could work, but 30000 don't)." 1>&2
	echo "Creating $num packages" 1>&2
	time {
		if [[ $q -eq 1 ]]; then
			&>/dev/null $py "${_ROOT}/run_ebuildcreation.py" $argline || echo fail 1>&2
		else
			$py "${_ROOT}/run_ebuildcreation.py" $argline
		fi;
	}
	echo "Done creating $num packages" 1>&2
else
	echo "test section not defined: ${TEST_SECTION}"
	exit ${__UNDEF__:-102}
fi
