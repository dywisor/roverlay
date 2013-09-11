# Copyright 1999-2013 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2
# $Header: $

EAPI=5

# dev-python/mako doesn't support python3.3, currently
PYTHON_COMPAT=( python{2_7,3_2} )
PYTHON_REQ_USE="ssl,threads(+),readline(+)"

EGIT_REPO_URI='git://git.overlays.gentoo.org/proj/R_overlay.git'

DOCS=()
HTML_DOCS=( doc/html/. )

inherit user distutils-r1 git-r3

DESCRIPTION="Automatically generated overlay of R packages"
HOMEPAGE="http://git.overlays.gentoo.org/gitweb/?p=proj/R_overlay.git;a=summary"
SRC_URI=""

LICENSE="GPL-2+"
SLOT="0"
KEYWORDS=""
IUSE="bzip2 +prebuilt-documentation"


_CDEPEND="dev-python/setuptools"
RDEPEND="${_CDEPEND?}
	prebuilt-documentation? ( >=dev-python/docutils-0.9 )"
DEPEND="${_CDEPEND?}
	sys-apps/portage
	virtual/python-argparse
	dev-python/mako[${PYTHON_USEDEP}]
	$(python_gen_cond_dep dev-python/futures[$(python_gen_usedep python2_7)] python2_7)"


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

	newbashcomp "${S}/files7misc/${PN}.bashcomp" "${PN}"
}

## TODO (when roverlay-setup is done)
##pkg_config() {
##	:
##}
