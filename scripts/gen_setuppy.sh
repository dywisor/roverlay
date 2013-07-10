#!/bin/sh
#
# creates a setup.py file
#

set -u

readonly I="   "
readonly Q="'"
readonly QQ='"'

case "${0##*/}" in
   gen_setup*)
      readonly PRJROOT=$( dirname $( readlink -f $( dirname "${0}" ) ) )
   ;;
   *)
      readonly PRJROOT=$( readlink -f "${PWD}" )
   ;;
esac
readonly S="${PRJROOT}"

# --- PRJ_* ---

: ${PRJ_NAME:='R_Overlay'}
: ${PRJ_DESC:='Automatically generated overlay of R packages (SoC2012)'}
: ${PRJ_AUTHOR:='André Erdmann'}
: ${PRJ_AUTHOR_EMAIL:='dywi@mailerd.de'}
: ${PRJ_LICENSE:='GPLv2+'}
: ${PRJ_URL:='http://git.overlays.gentoo.org/gitweb/?p=proj/R_overlay.git;a=summary'}
: ${PRJ_SCRIPTS='roverlay.py'}

if [ -z "${PRJ_VERSION-}" ]; then
   PRJ_VERSION=$( sed -rn -e \
      "s,^version\s*=\s*[${Q}${QQ}]([^${Q}${QQ}]+)[${Q}${QQ}].*$,\1,p" \
      "${S}/roverlay/__init__.py"
   )
   #PRJ_VERSION=$( python -EB "${S}/roverlay.py" --version 2>&1 )
fi

case "${PRJ_VERSION}" in
   [0-9]*) true ;;
   *)
      echo "invalid roverlay version '${PRJ_VERSION}'!" 1>&2
      exit 9
   ;;
esac
# --- end PRJ_* ---

get_pkglist() {
   if [ -e "${1}/local" ]; then
      echo "excluding ${1}: local" 1>&2
   elif [ "${1##*/}" == '__pycache__' ]; then
      true
   else
      echo "${I}${I}${Q}${1%/}${Q}"
      local d
      for d in ${1}/*; do
         if [ -d "${d}" ]; then
            get_pkglist "${d}" || return
         fi
      done
   fi
   return 0
}

PKGLIST=$( get_pkglist roverlay | sort | sed -e 's=[/]=.=g' )

#PKGLIST=$(
#   find roverlay/ -type d -not -name __pycache__| \
#      sort | sed -e "s=^=${I}${I}$Q=" -e "s=[/]*$=$Q,=" -e 's=[/]=.=g'
#)



mklist() { local word; for word; do echo "${Q}${word}${Q},"; done; }
i_mklist() { mklist "$@" | sed -e "s=^=${I}${I}="; }



gen_data_list() {
   # disabled
   return 0

   g() {
      local w="${1}"; shift || return
      echo -n "( ${Q}${w}${Q}, [ "
      local k
      for k; do echo -n "${Q}${k}${Q}, "; done
      echo "]),"
   }
   p() {
      local pre="${1}"; shift || return
      local w
      for w; do echo "${pre}${w}"; done
   }

   g '/etc/roverlay' $( p 'config/' \
         'description_fields.conf' \
         'license.map' \
         'repo.list' \
         'R-overlay.conf'
   )

   unset -f p
   unset -f g
}

gen_setup() {
   : ${I?}
cat << EOF
#!/usr/bin/python
# -*- coding: utf-8 -*-

import distutils.core

distutils.core.setup (
${I}name         = '${PRJ_NAME?}',
${I}version      = '${PRJ_VERSION?}',
${I}description  = '${PRJ_DESC?}',
${I}author       = '${PRJ_AUTHOR?}',
${I}author_email = '${PRJ_AUTHOR_EMAIL?}',
${I}license      = '${PRJ_LICENSE?}',
${I}url          = '${PRJ_URL?}',
${I}packages     = [
${PKGLIST?}
${I}],
${I}scripts      = [
$(i_mklist ${PRJ_SCRIPTS})
${I}],
${I}data_files   = [
$( gen_data_list | sed "s=^=${I}${I}=" )
${I}],
${I}classifiers  = [
${I}${I}#'Development Status :: 3 - Alpha',
${I}${I}'Development Status :: 4 - Beta',
${I}${I}'Environment :: Console',
${I}${I}'Intended Audience :: Developers',
${I}${I}'Intended Audience :: System Administrators',
${I}${I}'License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)',
${I}${I}'Operating System :: POSIX :: Linux',
${I}${I}'Programming Language :: Python :: 2.7',
${I}${I}'Programming Language :: Python :: 3',
${I}${I}'Programming Language :: Unix Shell',
${I}${I}'Topic :: System :: Software Distribution',
${I}],
)
EOF
}

gen_setup_file() {
   if gen_setup > "${1:?}.new"; then
      mv -f "${1}.new" "${1}" && chmod ug+x "${1}"
   fi
}


case "${1-}" in
   '')
      gen_setup_file "${S}/setup.py"
   ;;
   '-1'|'--stdout'|'-')
      gen_setup
   ;;
   *)
      gen_setup_file "${1}"
   ;;
esac
