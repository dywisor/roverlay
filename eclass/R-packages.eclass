# Copyright 1999-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2
# $Header: $

inherit eutils

EXPORT_FUNCTIONS src_unpack src_prepare src_compile src_install

SLOT="0"
KEYWORDS="~amd64 ~x86"
IUSE="byte-compile"

DEPEND="dev-lang/R"
RDEPEND="${DEPEND}"

S="${WORKDIR}"

R-packages_src_unpack() {
	unpack ${A}
	mv ${PN} ${P}
}

R-packages_src_prepare() {
	epatch_user
}

R-packages_src_compile() {
	R CMD INSTALL ${S}/${P} -l . $(use byte-compile && echo "--byte-compile")
}

R-packages_src_install() {
	insinto "${EPREFIX}/usr/$(get_libdir)/R/site-library"
	doins -r ${PN}
}