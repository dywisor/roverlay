#!/bin/sh -u
# Usage: genfiles.sh <src tree> <dest tree> [query-config args...]
#
#  Converts template files from <src tree> to real files in <dest tree>.
#

# die ( [message], [exit_code] ), raises exit()
die()           { echo "${1:+died: }${1:-died.}" 1>&2; exit ${2:-2}; }
autodie()       { "$@" || die "command '$*' returned ${?}." ${?}; }
OUT_OF_BOUNDS() { die "shift returned non-zero."; }
dodir()         { [ -d "${1-}" ] || mkdir -p -- "${1}"; }


# genfile ( infile, destdir_relpath, *query_config_args )
#
genfile() {
   local infile destdir destfile fname

   infile="${1}"
   [ -n "${2}" ] && destdir="${DEST_TREE%/}/${2}" || destdir="${DEST_TREE}"
   fname="${1##*/}"; fname="${fname%.in}"
   destfile="${destdir%/}/${fname}"

   shift 2 || OUT_OF_BOUNDS

   if [ "${infile}" = "${destfile}" ]; then
      die "infile = outfile: ${infile}"
   else
      autodie dodir "${destdir}"
      echo "creating ${destfile}"
      if ${X_RV_QUERY_CONFIG} "$@" -f "${infile}" -O "${destfile}"; then
         # chmod, ...?
         true
      else
         echo "!!! failed to create '${destfile}' (rc=${?})" 1>&2
         fail=$(( ${fail?} + 1 ))
      fi
   fi
}

# genfiles_recursive ( root, root_relpath, *query_config_args )
#
genfiles_recursive() {
   local root relpath item

   root="${1}"
   relpath="${2#/}"

   shift 2 || OUT_OF_BOUNDS

   for item in "${root}/"*; do
      if [ -d "${item}" ]; then
         genfiles_recursive "${item}" "${relpath}/${item##*/}" "$@"
      elif [ -f "${item}" ]; then
         # converts file symlinks to files
         genfile "${item}" "${relpath}" "$@"
      else
         echo "cannot handle '${item}'" 1>&2
      fi
   done
}

# ---

: ${X_RV_QUERY_CONFIG:=/usr/bin/roverlay-query-config}

case "${1-}" in
   '-h'|'--help')
      echo "Usage: genfiles.sh <src tree> <dest tree< [<query-config arg>...]"
      exit 0
   ;;
esac

[ -n "${1-}" ] || die "missing src tree arg."
[ -n "${2-}" ] || die "missing dest tree arg."

SRC_TREE="$(readlink -f "${1}")"
DEST_TREE="$(readlink -f "${2}")"

[ -n "${SRC_TREE}" ] && [ -d "${SRC_TREE}" ] || die "src tree does not exist."
[ -n "${DEST_TREE}" ] || die "invalid dest tree."

shift 2

# globbing is essential, make sure that "noglob" is disabled
set +f
fail=0
genfiles_recursive "${SRC_TREE}" "" "$@"
if [ ${fail} -gt 0 ]; then
   exit 3
else
   exit 0
fi
