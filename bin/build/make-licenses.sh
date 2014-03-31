#!/bin/sh
#
#  Creates a license list file for roverlay.
#
#  Usage: make-licenses [dest_file] [compression]
#
#  Environment variables:
#  * PORTDIR: path to the main tree (= root of the "licenses" dir)
#
set -u

die() { echo "${1:-error}" 1>&2; exit ${2:-2}; }

mkmap() {
   local x
   # find -type f, ls -1, ...
   set +f
   for x in "${PORTDIR}/licenses/"*; do
      [ ! -f "${x}" ] || echo "${x##*/}"
   done
}

mkmap_bz2() { mkmap | bzip2 -c; }
mkmap_xz()  { mkmap | xz -c; }
mkmap_gz()  { mkmap | gzip -c; }

get_mkmap_func() {
   case "${1-}" in
      '') func=mkmap ;;
      bz2|xz|gz) func=mkmap_${1} ;;
      *) die "unknown compression '${1-}'." 64 ;;
   esac
}

if [ -z "${PORTDIR-}" ]; then
   PORTDIR="$(portageq get_repo_path / gentoo)"
   #PORTDIR="$(portageq get_repo_path $(portageq envvar EROOT) gentoo)"
   [ -n "${PORTDIR}" ] || PORTDIR="$(portageq envvar PORTDIR)"
   [ -n "${PORTDIR}" ] || die "failed to get \$PORTDIR"
fi

case "${1-}" in
   ''|'-')
      get_mkmap_func "${2-}" && ${func}
   ;;
   *.bz2|*.xz|*.gz)
      [ -z "${2-}" ] || [ "${2}" = "${1##*.}" ] || die
      get_mkmap_func "${1##*.}" && ${func} > "${1}"
   ;;
   *)
      get_mkmap_func "${2-}" && ${func} > "${1}"
   ;;
esac
