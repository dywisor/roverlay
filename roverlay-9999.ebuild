# Copyright 1999-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2
# $Header: $

EAPI="4"
# python3_1 is probably supported, too (<2.7 is not)
PYTHON_COMPAT="python2_7 python3_2"

inherit base python-distutils-ng git-2

EGIT_REPO_URI='git://git.overlays.gentoo.org/proj/R_overlay.git'

DESCRIPTION="Automatically generated overlay of R packages (SoC2012)"
HOMEPAGE="http://git.overlays.gentoo.org/gitweb/?p=proj/R_overlay.git;a=summary"
SRC_URI=""

LICENSE="GPL"
SLOT="0"
IUSE=""

KEYWORDS=""

DEPEND=""
RDEPEND="${DEPEND:-}
	dev-python/argparse
"

python_prepare_all() {
	base_src_prepare
}

python_install_all() {
	insinto "/usr/share/${PN}"
	doins config/description_fields.conf config/R-overlay.conf repo.list
	if [[ -e "R-overlay.conf.install" ]]; then
		newins R-overlay.conf.install R-overlay.conf.quickstart
	else
		newins R-overlay.conf R-overlay.conf.quickstart
	fi

	doman man/?*.?*

	newbin roverlay.py roverlay
}
