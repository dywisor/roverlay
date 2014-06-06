#!/bin/sh
# *hacky* script that fetches and installs bootstrap and jquery
# to $WEBGUI_PRJROOT/static
#
set -u

TROOT="${ROVERLAY_WEBGUI_PRJROOT}/tmp"
D="${ROVERLAY_WEBGUI_PRJROOT}/static"
T="${TROOT}/$(date +%s)"


BS_VER="3.1.1"
BS_PN="bootstrap-${BS_VER}-dist"
BS_P="${BS_PN}.zip"
BS_URI="https://github.com/twbs/bootstrap/releases/download/v3.1.1/${BS_P}"


JQ_VER="2.1.0"
JQ_PN="jquery-${JQ_VER}.min"
JQ_P="${JQ_PN}.js"
JQ_URI="http://code.jquery.com/${JQ_P}"

INSMODE=0644
EXEMODE=0755
DIRMODE=0755

_INSTALL="_ install"
DOINS="${_INSTALL} -m ${INSMODE}"
DOEXE="${_INSTALL} -m ${EXEMODE}"
DODIR="${_INSTALL} -m ${DIRMODE} -d"

_() {
   echo "$*"
   "$@"
}


recursive_install() {
   local src dst f fname
   src="${1:?}"
   dst="${2:?}"

   ${DODIR} ${dst}
   for f in "${src}/"*; do
      fname="${f##*/}"
      if [ -f "${f}" ]; then
         ${DOINS} -- "${f}" "${dst}/${fname}"
      elif [ -d "${f}" ]; then
         recursive_install "${f}" "${dst}/${fname}"
      else
         echo "cannot install ${f}" 1>&2
      fi
   done
}

cleanup() {
   trap - TERM EXIT
   rm -rf -- "${T}"
}

set -e
set +f

trap cleanup TERM EXIT
mkdir -p -- "${T}/bs"
x="${TROOT}/${BS_P}"
wget -c "${BS_URI}" -O "${x}"

unzip "${x}" -d "${T}/bs"
recursive_install "${T}/bs/${BS_PN}" "${D}"


x="${TROOT}/${JQ_P}"
wget -c "${JQ_URI}" -O "${x}"

${DODIR} -- "${D}/js"
${DOINS} -- "${x}" "${D}/js/${JQ_P}"
ln -nfsvT -- "${JQ_P}" "${D}/js/jquery.min.js"

cleanup
