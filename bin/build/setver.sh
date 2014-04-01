#!/bin/sh
#
#  Sets roverlay's version.
#
#  Usage: setver [-S,--src <dir>] [--pretend] [--suffix <str>]
#            [+,pbump|++,mbump|Mbump|[setver] <ver>]
#
# Actions:
#  +, pbump        -- increase patchlevel by one
#  ++, mbump       -- increase minor version by one and set patchlevel to 0
#  Mbump           -- increase major version by one and set minor/patchlevel to 0
#  setver <ver>    -- set a specific version
#
# Options:
# -S, --src <dir>  -- set roverlay source directory (default: $PWD)
# --pretend        -- just show what would be done
# --suffix <str>   -- replace old version suffix with <str>
#
set -u
IFS_DEFAULT="${IFS}"

PY_FILES_TO_EDIT="roverlay/core.py setup.py"


die() {
   echo "${1:-unknown error.}" 1>&2; exit ${2:-2};
}

parse_version() {
   local IFS="."
   set -- ${1}
   IFS="${IFS_DEFAULT}"
   [ ${#} -ge 3 ] || return 2

   major="${1:?}"
   minor="${2:?}"
   plvl="${3:?}"
   shift 3 || die "error in parse_version()"
   suffix="${*}"
}

inc() {
   v0=$(( ${1} + 1 ))
   [ ${v0} -gt ${1} ] || die "overflow"
}

S="${PWD}"
unset -v V
unset -v ACTION
unset -v new_suffix
unset -v do_pretend

doshift=
while [ ${#} -gt 0 ]; do
   doshift=1
   case "${1}" in
      '') : ;;

      '--src'|'-S')
         [ ${#} -ge 2 ] || die "argparse error"
         doshift=2
         S="${2:?}"
      ;;

      pretend|--pretend)
         do_pretend=true
      ;;

      [Mmp]bump) ACTION="${1}" ;;
      '+')       ACTION=pbump  ;;
      '++')      ACTION=mbump  ;;
      *.*.*)     ACTION=setver; V="${1}" ;;

      setver)
         [ ${#} -ge 2 ] || die "argparse error"
         doshift=2
         ACTION=setver
         V="${2:?}"
      ;;

      suffix|--suffix)
         [ ${#} -ge 2 ] || die "argparse error"
         doshift=2
         new_suffix="${2?}"
      ;;

      *)
         die "unknown arg: ${1}" 64
      ;;
   esac
   [ ${doshift} -eq 0 ] || shift ${doshift} || die "argparse: shift failed"
done

: ${do_pretend:=false}
OLDVER="$(cat "${S}/VERSION")"
parse_version "${OLDVER}" || die "bad version: ${OLDVER}."
[ -n "${new_suffix+SET}" ] || new_suffix="${suffix}"

case "${ACTION-}" in
   pbump)
      inc "${plvl}"
      V="${major}.${minor}.${v0}${new_suffix}"
   ;;
   mbump)
      inc "${minor}"
      V="${major}.${v0}.0${new_suffix}"
   ;;
   Mbump)
      inc "${major}"
      V="${v0}.0.0${new_suffix}"
   ;;
   setver)
      true
   ;;
   *)
      die "unknown or no action specified."
   ;;
esac

q="\"\'"
re_pyfile_ver="^(\s*version\s*=\s*)[${q}]?([^\s;,${q}]*)[${q}]?(\s*[;,]?\s*)\$"

_fmt="edit %-18s: %8s  ->  %s\n"
for fname in ${PY_FILES_TO_EDIT}; do
   f="${S}/${fname}"
   fver="$(sed -rn -e "s@${re_pyfile_ver}@\2@p" < "${f}")"
   printf "${_fmt}" "${fname}" "${fver}" "${V}"
   ${do_pretend} || sed -r -e "s@${re_pyfile_ver}@\1\"${V}\"\3@" -i "${f}"
done
printf "${_fmt}" "VERSION" "${OLDVER}" "${V}"
${do_pretend} || echo "${V}" > "${S}/VERSION"
