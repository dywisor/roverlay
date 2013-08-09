# Copyright 1999-2013 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2
# $Header: $

EAPI=4

# python < 2.7 is not supported
PYTHON_COMPAT="python2_7 python3_2"
PYTHON_USE="ssl"

inherit base python-distutils-ng git-2 user bash-completion-r1

EGIT_REPO_URI='git://git.overlays.gentoo.org/proj/R_overlay.git'
[[ "${PV}" != "99999"* ]] || EGIT_BRANCH=gsoc13/next

DESCRIPTION="Automatically generated overlay of R packages (SoC2012)"
HOMEPAGE="http://git.overlays.gentoo.org/gitweb/?p=proj/R_overlay.git;a=summary"
SRC_URI=""

LICENSE="GPL-2+"
SLOT="0"
IUSE="bash-completion bzip2 +prebuilt-documentation"

KEYWORDS=""

_CDEPEND="
	dev-python/setuptools
	python_targets_python2_7? ( dev-python/futures[python_targets_python2_7] )
"
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
	# hooks etc. into /usr/share (architecture-independent data)
	emake BUILDDIR="${S}/tmp" DESTDIR="${D}" \
		install-data $(usex bzip2 install-config{-compressed,})

	dohtml doc/html/*

	if use bash-completion; then
		newbashcomp "${S}/files/misc/${PN}.bashcomp" "${PN}"
	fi

	# roverlay expects these directories to exist
	#  (due to the default config file)
	keepdir /etc/${PN}/{files,package-rules.d}
}

pkg_setup() {
	enewgroup roverlay
}

pkg_config() {
	## func
	get_user_dir() {
		if [[ -d "${1}" ]]; then
			return 0
		else
			mkdir -m 0750 "${1}" && \
				chown -h "${roverlay_user}:${roverlay_group}" "${1}" || \
				die "failed to create '${1}'."
		fi
	}
	# enable_hook ( hook_script_name, hook_name, **hook_destdir, **data_root )
	enable_hook() {
		local hook_src="${data_root?}/hooks/${1%.sh}.sh"
		local hook_dest="${hook_destdir?}/${2%.sh}.sh"

		if [[ ! -f "${hook_src}" ]]; then
			die "hook script '${hook_src}' does not exist."
		elif [[ -L "${hook_dest}" ]]; then
			if [[ "$(readlink -f ${hook_dest})" == "${hook_src}" ]]; then
				einfo "skipping ${2%.sh} - already set up"
			else
				ewarn "skipping ${2%.sh} - link to another script"
			fi
		elif [[ -e "${hook_dest}" ]]; then
			ewarn "skipping hook ${2%.sh} - exists, but not a link"
		else
			ebegin "Adding hook ${1%.sh} as ${2%.sh}"
			ln -sT "${hook_src}" "${hook_dest}" && \
			chown -Ph "${roverlay_user}:${roverlay_group}" "${hook_dest}"
			eend $? || die "failed to add hook ${2%.sh}"
		fi
	}

	## vars
	local DEFAULT_CONF_ROOT="${ROOT}etc/${PN}"

	local roverlay_user="roverlay"
	local roverlay_group="roverlay"
	#local user_is_root
	local want_conf_import

	local data_root="${ROOT}usr/share/${PN}"
	local conf_root
	local work_root

	local want_default_hooks=y

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
				'') true ;;
				'y'|'n') want_conf_import="${input}" ;;
				*) die "answer '${input}' not understood." ;;
			esac
		;;
	esac

	if [[ -e "${config_file}" ]]; then
		einfo "This will overwrite ${config_file}!"
		echo
	fi

	einfo "Enable default overlay creation hooks (git history and metadata cache)? (y/n) ['${want_default_hooks}']"
	input=; read input
	case "${input}" in
		'') true ;;
		'y'|'n') want_default_hooks="${input}" ;;
		*) die "answer '${input}' not understood." ;;
	esac

	einfo "Enter the directory for 'work' data (overlay, distfiles, mirror) ['${work_root}']:"

	input=; read input
	[[ -z "${input}" ]] || work_root="${input}"

	# setting ADDITIONS_DIR here "breaks" hook activation
	einfo "Enter additional config options (VAR=VALUE; use with care) [optional]:"
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
	einfo "- enable default hooks : ${want_default_hooks}"
	einfo "- additional options   : ${input:-<none>}"
	einfo
	einfo "Press Enter to continue..."
	read

	## do it

	# temporary config file - will be moved to its final location when done
	ebegin "Creating temporary config file"
	/usr/bin/roverlay-mkconfig -O "${T}/${PF}.config" \
		-W "${work_root}" -D "${data_root}" -C "${conf_root}" -- ${input-}
	eend $? || die

	# import config
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

	# run "roverlay setupdirs"
	ebegin "Creating directories"
	/usr/bin/roverlay --config "${T}/${PF}.config" \
		--target-uid ${roverlay_user} --target-gid ${roverlay_group} setupdirs
	eend $? || die

	# move config file
	ebegin "Copying new config file to ${config_file}"
	cp --preserve=mode,timestamps "${T}/${PF}.config" "${config_file}" && \
	chown "${roverlay_user}:${roverlay_group}" "${config_file}"
	eend $? || die

	# adjust permissions for $work_root
	if [[ ! -L "${work_root}" ]]; then
		# ^ chmod doesn't work nicely for symlinks

		ebegin "Adjusting permissions for ${work_root}"
		chmod 0750 "${work_root}" && \
			chown -h --from="root:root" \
				"${roverlay_user}:${roverlay_group}" "${work_root}"
		eend $? || die
	fi

	# enable hooks
	if [[ "${want_default_hooks}" ]]; then
		einfo "Activating default hooks"
		if [[ ! -d "${conf_root}/files" ]]; then
			ewarn "Skipping hook activation: ADDITIONS_DIR not in config root."
		else
			local hook_destdir="${conf_root}/files/hooks/overlay_success"

			# non-recursive
			get_user_dir "${hook_destdir%/*}"
			get_user_dir "${hook_destdir}"

			enable_hook {,50-}create-metadata-cache
			enable_hook {,80-}git-commit-overlay
		fi
	fi

	echo
	einfo "Configuration for user '${roverlay_user}' is complete."
	einfo "You can run '${PN} --print-config' (as user) to verify it."
}
