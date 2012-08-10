# Copyright 1999-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2
# $Header: $

EAPI="4"
# python < 2.7 is not supported
PYTHON_COMPAT="python2_7 python3_1 python3_2"

inherit base python-distutils-ng git-2

EGIT_REPO_URI='git://git.overlays.gentoo.org/proj/R_overlay.git'

DESCRIPTION="Automatically generated overlay of R packages (SoC2012)"
HOMEPAGE="http://git.overlays.gentoo.org/gitweb/?p=proj/R_overlay.git;a=summary"
SRC_URI=""

LICENSE="GPL"
SLOT="0"
IUSE="bzip2"

KEYWORDS=""

DEPEND=""
RDEPEND="${DEPEND:-}
	dev-python/argparse
"

_CONFDIR=/etc/${PN}

python_prepare_all() {
	if use bzip2; then
		einfo "USE=bzip2: Compressing dependency rule files"
		bzip2 simple-deprules.d/* || die "Cannot compress dependency rules!"
	fi
	sed -f misc/sed_expression_roverlay_installed roverlay.py -i || \
		die "sed expression, roverlay.py"
	base_src_prepare
}

python_install_all() {
	newbin roverlay.py roverlay

	insinto "${_CONFDIR}"
	doins config/description_fields.conf repo.list
	doins -r simple-deprules.d/
	newins R-overlay.conf.install R-overlay.conf

	doman  doc/man/*.*
	dohtml doc/html/*
}
