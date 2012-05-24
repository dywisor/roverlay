#!/bin/bash
# temporary script
#  extracts data (=files) out of a R src package
#

## this is a multicall script whose only functionality is get(file, *info) - don't rename

readonly _ARGV="$*"
_SELF="${0##*/}"
_SELF="${_SELF%.*sh}"
readonly _SELF
set --
set -u

# get (file, *info)
#  extracts *info out of file (or all gzip-tarballs in `pwd`)
#
get() {
	local file="${1:-}" x fname name
	shift ||:

	[[ "$file" ]] || return ${undone:-101}

	if [[ "$file" == "all" ]]; then
		for x in *.tar.gz *.tgz; do
			if [[ -r "$x" ]]; then
				get "$x" $* || return $?
			fi
		done
		return 0
	fi

	fname="${file##*/}"
	fname="${fname%%.*}"
	name="${fname%%_*}"
	for x in $*; do
		case "${x}" in
			desc) tar xvzf "$file" "${name}/DESCRIPTION" && \
						mv -f -v -- "${name}/DESCRIPTION" "${name}.desc" &&
						rmdir "${name}" && chmod a=r "${name}.desc" || return $?
					;;
			*) return ${undef:-56} ;;
		esac
	done
	return 0
}

__error__() {
	local -i _ret=$?
	1>&2 echo "error when calling method '${1:-$_SELF}'."
	return $_ret
}

${_SELF} $_ARGV || __error__ "${_SELF}"
