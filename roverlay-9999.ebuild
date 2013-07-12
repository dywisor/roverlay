# Copyright 1999-2013 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2
# $Header: $

EAPI=4

# python < 2.7 is not supported
PYTHON_COMPAT="python2_7 python3_1 python3_2"
PYTHON_USE="ssl"

inherit base python-distutils-ng git-2 user

EGIT_REPO_URI='git://git.overlays.gentoo.org/proj/R_overlay.git'
#EGIT_BRANCH='gsoc13/next'

DESCRIPTION="Automatically generated overlay of R packages (SoC2012)"
HOMEPAGE="http://git.overlays.gentoo.org/gitweb/?p=proj/R_overlay.git;a=summary"
SRC_URI=""

LICENSE="GPL-2+"
SLOT="0"
IUSE="-bzip2 +prebuilt-documentation"

KEYWORDS=""

_CDEPEND="dev-python/setuptools"
DEPEND="${_CDEPEND}
	!prebuilt-documentation? ( >=dev-python/docutils-0.9 )
"
RDEPEND="${_CDEPEND}
	sys-apps/portage
	virtual/python-argparse
"

python_prepare_all() {
	base_src_prepare
	if use bzip2; then
		einfo "USE=bzip2: Compressing dependency rule files"
		emake BUILDDIR="${S}/tmp" compress-config
	fi
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

	# roverlay expects these directories to exist
	#  (due to the default config file)
	keepdir /etc/${PN}/{files,package-rules.d}
}

pkg_setup() {
	enewgroup roverlay
}

pkg_config() {
	## vars
	local DEFAULT_CONF_ROOT="${ROOT}etc/${PN}"

	local roverlay_user="roverlay"
	local roverlay_group="roverlay"
	#local user_is_root
	local want_conf_import

	local data_root="${ROOT}usr/share/${PN}"
	local conf_root
	local work_root

	local input

	## get user input
	einfo "Enter user/uid that will run ${PN} (user has to exist!) ['${roverlay_user}']:"
	# input= not strictly needed
	input=; read input
	[[ -z "${input}" ]] || roverlay_user="${input}"

	egetent passwd "${roverlay_user}" 1>/dev/null || \
		die "no such user/uid: ${roverlay_user}"

	case "${roverlay_user}" in
		'0'|'root')
			#user_is_root=y

			work_root="${ROOT}var/${PN}"
			conf_root="${DEFAULT_CONF_ROOT}"
			config_file="${conf_root}/R-overlay.conf"

			einfo "config root is ${conf_root}"
			want_conf_import=n
		;;
		*)
			#user_is_root=n

			# get user config location
			input="$(egethome ${roverlay_user})"
			[[ -d "${input}" ]] || die "user has no home directory: ${input}"

			work_root="${input}/${PN}"
			conf_root="${work_root}/config"
			config_file="${work_root}/R-overlay.conf"

			if [[ ! -e "${conf_root}" ]]; then
				einfo "config root is ${conf_root} (will be created)"
				want_conf_import=y
			else
				einfo "config root is ${conf_root} (already exists)"
				want_conf_import=n
			fi

			einfo "Import default config (${DEFAULT_CONF_ROOT})? (y/n) ['${want_conf_import}']"
			input=; read input
			case "${input}" in
				'')
					true
				;;
				'y'|'n')
					want_conf_import="${input}"
				;;
				*)
					die "answer '${input}' not understood."
				;;
			esac
		;;
	esac

	if [[ -e "${config_file}" ]]; then
		einfo "This will overwrite ${config_file}!"
		echo
	fi

	einfo "Enter the directory for 'work' data (overlay, distfiles, mirror) ['${work_root}']:"

	input=; read input
	[[ -z "${input}" ]] || work_root="${input}"

	einfo "Enter additional variables (VAR=VALUE) [optional]:"
	input=; read input

	## print what would be done
	local noconf="(not configurable)"
	echo
	einfo "Configuration:"
	einfo "- user/uid             : ${roverlay_user}"
	einfo "- group/gid            : ${roverlay_group} ${noconf}"
	einfo "- work root            : ${work_root}"
	einfo "- data root            : ${data_root} ${noconf}"
	einfo "- config root          : ${conf_root}"
	einfo "- import config        : ${want_conf_import}"
	einfo "- additional variables : ${input:-<none>}"
	einfo
	einfo "Press Enter to continue..."
	read

	## do it
	ebegin "Creating temporary config file"
	/usr/bin/roverlay-mkconfig -O "${T}/${PF}.config" \
		-W "${work_root}" -D "${data_root}" -C "${conf_root}" -- ${input-}
	eend $? || die

	if [[ "${want_conf_import}" == "y" ]]; then
		[[ -d "${conf_root}" ]] || mkdir -p "${conf_root}" || \
			die "cannot create ${conf_root}"

		ebegin "Importing default config (${DEFAULT_CONF_ROOT})"
		cp -dRu --preserve=mode,timestamps \
			"${DEFAULT_CONF_ROOT}"/* "${conf_root}"/ && \
			chown -Rh --from="root:root" \
				"${roverlay_user}:${roverlay_group}" "${conf_root}"
		eend $? || die
	fi

	ebegin "Creating directories"
	/usr/bin/roverlay --config "${T}/${PF}.config" \
		--target-uid ${roverlay_user} --target-gid ${roverlay_group} setupdirs
	eend $? || die

	ebegin "Copying new config file to ${config_file}"
	cp --preserve=mode,timestamps "${T}/${PF}.config" "${config_file}" && \
	chown "${roverlay_user}:${roverlay_group}" "${config_file}"
	eend $? || die

	echo
	einfo "Configuration for user '${roverlay_user}' is complete."
	einfo "You can run '${PN} --print-config' (as user) to verify it."
}
