# Copyright 1999-2013 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2
# $Header: $

EAPI=4

# python < 2.7 is not supported
PYTHON_COMPAT="python2_7 python3_1 python3_2"
PYTHON_USE="ssl"

inherit base python-distutils-ng git-2

EGIT_REPO_URI='git://git.overlays.gentoo.org/proj/R_overlay.git'

DESCRIPTION="Automatically generated overlay of R packages (SoC2012)"
HOMEPAGE="http://git.overlays.gentoo.org/gitweb/?p=proj/R_overlay.git;a=summary"
SRC_URI=""

LICENSE="GPL-2+"
SLOT="0"
IUSE="bzip2 +prebuilt-documentation"

KEYWORDS=""

DEPEND="!prebuilt-documentation? ( >=dev-python/docutils-0.9 )"
RDEPEND="
	sys-apps/portage
	virtual/python-argparse
"

python_prepare_all() {
	if use bzip2; then
		einfo "USE=bzip2: Compressing dependency rule files"
		emake BUILDDIR="${S}/tmp" compress-config
	fi
	sed -f misc/sed_expression_roverlay_installed roverlay.py -i || \
		die "sed expression, roverlay.py"
	base_src_prepare
}

src_compile() {
	python-distutils-ng_src_compile

	if ! use prebuilt-documentation; then
		emake htmldoc
	fi
}

python_install_all() {
	#newbin roverlay.py roverlay

	# hooks etc. into /usr/share (architecture-independent data)
	emake BUILDDIR="${S}/tmp" DESTDIR="${D}" \
		install-data $(usex bzip2 install-config{-compressed,})

	dohtml doc/html/*
}
