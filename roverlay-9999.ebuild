# Copyright 1999-2013 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2
# $Header: $

EAPI=5

PYTHON_COMPAT=( python{3_2,3_3} )
PYTHON_REQ_USE="ssl,threads(+),readline(+)"

EGIT_REPO_URI='git://git.overlays.gentoo.org/proj/R_overlay.git'

DOCS=()
HTML_DOCS=( doc/html/. )
EXAMPLES=( examples/. )

inherit user distutils-r1 git-r3 bash-completion-r1

DESCRIPTION="Automatically generated overlay of R packages"
HOMEPAGE="http://git.overlays.gentoo.org/gitweb/?p=proj/R_overlay.git;a=summary"
SRC_URI=""

LICENSE="GPL-2+"
SLOT="0"
KEYWORDS=""
IUSE="bzip2 +prebuilt-documentation"


DEPEND="
	dev-python/setuptools
	!prebuilt-documentation? ( >=dev-python/docutils-0.9 )"
RDEPEND="
	sys-apps/portage
	virtual/python-argparse
	dev-python/mako[${PYTHON_USEDEP}]
	virtual/python-futures"


pkg_setup() {
	enewgroup roverlay
}

python_prepare_all() {
	distutils-r1_python_prepare_all
	if use bzip2; then
		einfo "USE=bzip2: Compressing dependency rules and license map"
		emake BUILDDIR="${S}/compressed" compress-config
	fi
}

python_compile_all() {
	use prebuilt-documentation || emake htmldoc
}

python_install_all() {
	distutils-r1_python_install_all

	emake BUILDDIR="${S}/compressed" DESTDIR="${D}" \
		install-data $(usex bzip2 install-config{-compressed,})

	# could be done in the Makefile as well
	dobin "${S}/bin/install/${PN}-setup-interactive"

	newbashcomp "${S}/files/misc/${PN}.bashcomp" "${PN}"
}

pkg_config() {
	${PN}-setup-interactive || die
}
