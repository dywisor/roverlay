# Some make targets for testing / distribution
#  run "make help" to list them

# don't create bytecode files when running py scripts (racy)
unexport PYTHONDONTWRITEBYTECODE
export PYTHONDONTWRITEBYTECODE=y

_PRJNAME := R_Overlay
_PN      := roverlay
DISTNAME := $(_PN)

SHELL    ?= sh

S        := $(CURDIR)
# !!! for proper outdir $O support,
#      generate-* and install-* have to modified
O        := $(S)
BUILDDIR := $(O)/tmp

DESTDIR  := /
DESTTREE := $(DESTDIR)usr/

DATADIR     := $(DESTTREE)share
BINDIR      := $(DESTTREE)bin
CONFDIR     := $(DESTDIR)etc
BASHCOMPDIR := $(DATADIR)/bash-completion

DIRMODE  := 0755
INSMODE  := 0644
EXEMODE  := 0755

_DODIR    = install -m $(DIRMODE) -d
_DOINS    = install -m $(INSMODE)
_DOEXE    = install -m $(EXEMODE)

PYMOD_FILE_LIST := $(O)/$(_PN)_files.list

_SETUP_PY_DIRS := $(addprefix $(S)/,build/ $(_PRJNAME).egg-info/)
_PYMOD_DIRS    := $(addprefix $(S)/,roverlay/)

ROVERLAY_TARGET_TYPE := gentoo
COMPRESSED_CONFIG    := n
RELEASE_NOT_DIRTY    := n
RELEASE_DIRTY_SUFFIX := -dirty
VBUMP_COMMIT         := y

MANIFEST      := $(S)/MANIFEST
LICENSES_FILE := $(S)/files/licenses
VERSION_FILE  := $(S)/VERSION
HTML_DOCS     := usage
HTMLDOC_TITLE := Automatically Generated Overlay of R packages

X_GIT         := git
X_RST2HTML    := rst2html.py
X_GZIP        := gzip
X_BZIP2       := bzip2
X_XZ          := xz
X_COMPRESS    := $(X_BZIP2)
ifeq ($(X_COMPRESS),$(X_BZIP2))
X_COMPRESS_SUFFIX := .bz2
else ifeq ($(X_COMPRESS),$(X_GZIP))
X_COMPRESS_SUFFIX := .gz
else ifeq ($(X_COMPRESS),$(X_XZ))
X_COMPRESS_SUFFIX := .xz
else
X_COMPRESS_SUFFIX :=
endif

PYVER         :=
PYTHON        := python$(PYVER)

_SCRIPTS_DIR  := $(S)/bin
_BUILDSCRIPTS := $(_SCRIPTS_DIR)/build

MANIFEST_GEN  := $(_BUILDSCRIPTS)/create_manifest.sh
LICENSES_GEN  := $(_BUILDSCRIPTS)/make-licenses.sh
X_SETVER      := $(_BUILDSCRIPTS)/setver.sh
RV_SETUP      := $(_SCRIPTS_DIR)/$(_PN)-setup
X_RUN_TESTS   := $(_SCRIPTS_DIR)/run_tests

SETUP_PY      := $(S)/setup.py
PKG_DISTDIR   := $(O)/release

LOGDIR        := $(S)/log
SRC_DOCDIR    := $(S)/doc
SELFDOC       := $(SRC_DOCDIR)/pydoc

_TRUE_WORDS   := y Y 1 yes YES true TRUE

# _f_recursive_install ( src_root, src_names, dest_root, file_mode )
#
#  Recursively installs files from <src_root>/<%name> to <dest_root>/<%name>
#  for each name in <src_names>.
#
_f_recursive_install = ( \
	cd $(1)/ && find $(2) -type f -print0 | \
		xargs -0 -n 1 -I '{FILE}' $(SHELL) -c \
		'set -- install -m "$(4)" -D -- "{FILE}" "$(3)/{FILE}" && \
			echo "$${*}" && "$${@}"' \
)

# _f_install_config_files ( src_dir )
#
#  Installs "optionally compressable" files from src_dir to CONFDIR/_PN.
#  (i.e. config files not installed by install-config-common)
#
_f_install_config_files = $(call _f_recursive_install,$(1),\
	license.map simple-deprules.d/,$(CONFDIR)/$(_PN),$(INSMODE))


PHONY += all
all:

PHONY += version
version:
	@cat $(VERSION_FILE)

PHONY += setver
setver: $(X_SETVER)
ifeq ($(VER),)
	$(error $$VER is not set)
else
	$< $(VER)
endif

PHONY += version-bump
version-bump: $(X_SETVER)
	{ ! $(X_GIT) status --porcelain -- $(notdir $(VERSION_FILE)) | grep .; }
ifeq ($(VBUMP_COMMIT),$(filter $(VBUMP_COMMIT),$(_TRUE_WORDS)))
	X_GIT="$(X_GIT)" $< --reset --git-add --git-commit --git-tag +
else
	X_GIT="$(X_GIT)" $< --reset --git-add +
endif

PHONY += test
test: $(X_RUN_TESTS)
	$<

PHONY += clean
clean:
	rm -rf -- $(_SETUP_PY_DIRS) $(BUILDDIR)/
	rm -f  -- $(wildcard $(PKG_DISTDIR)/*.make_tmp)

PHONY += clean-log
clean-log:
	rm -rf -- $(LOGDIR)/

PHONY += pyclean
pyclean:
	find $(_PYMOD_DIRS) -name '*.py[co]' -delete -print

PHONY += pydoc_clean
pydoc_clean:
#	rm -f -- $(wildcard $(SELFDOC)/*.html)
	rm -f -- $(SELFDOC)/*.html

PHONY += distclean
distclean: clean pyclean pydoc_clean
	test ! -d $(SELFDOC) || rmdir --ignore-fail-on-non-empty -- $(SELFDOC)/

$(PKG_DISTDIR) $(BUILDDIR) $(BUILDDIR)/config:
	mkdir -p -- "$@"

$(SELFDOC)/roverlay: $(S)/roverlay
	mkdir -p -- $(@D)
	ln -nfsT -- $< $@

# generates selfdocs (using pydoc) in $(SELFDOC)/
$(SELFDOC): FORCE pydoc_clean | $(SELFDOC)/roverlay
	test -e $@/roverlay
	cd $@ && find roverlay/ -type f -name '*.py' | \
		sed -e 's,[.]py$$,,' -e 's,\/,.,g' -e 's,[.]__init__$$,,' | \
		xargs pydoc -w
	ln -nfsT -- roverlay.html $@/index.html
	rm -f $@/roverlay

# alias to $(SELFDOC)
PHONY += pydoc
pydoc: $(SELFDOC)

$(SRC_DOCDIR)/html/%.html: $(SRC_DOCDIR)/rst/%.rst
	@mkdir -p $(@D)
	$(X_RST2HTML) --title '$(HTMLDOC_TITLE)' --date '$<' '$@'

PHONY += htmldoc
htmldoc: $(addsuffix .html,$(addprefix $(SRC_DOCDIR)/html/,$(HTML_DOCS)))

PHONY += generate-doc
generate-doc: htmldoc

$(MANIFEST): $(MANIFEST_GEN) FORCE
	@mkdir -p $(@D)
	$< > $@

PHONY += generate-manifest
generate-manifest: $(MANIFEST)

$(LICENSES_FILE): $(LICENSES_GEN) FORCE
	@mkdir -p $(@D)
	$< $@

PHONY += generate-licenses
generate-licenses: $(LICENSES_FILE)


$(S)/config/R-overlay.conf.install: $(RV_SETUP) FORCE
	@mkdir -p $(@D)
	ROVERLAY_INSTALLED=1 $< --target-type gentoo \
		-O $@ \
		-D $(DATADIR)/$(_PN) \
		--conf-root $(CONFDIR)/$(_PN) --my-conf-root $(CONFDIR)/$(_PN) \
		-A $(CONFDIR)/$(_PN)/files \
		mkconfig

$(S)/config/R-overlay.conf.install.others: $(RV_SETUP) FORCE
	@mkdir -p $(@D)
	ROVERLAY_INSTALLED=1 $< --target-type foreign \
		-O $@ \
		-D $(DATADIR)/$(_PN) \
		--conf-root $(CONFDIR)/$(_PN) --my-conf-root $(CONFDIR)/$(_PN) \
		-A $(CONFDIR)/$(_PN)/files \
		mkconfig

$(S)/R-overlay.conf: $(RV_SETUP) FORCE
	@mkdir -p $(@D)
	ROVERLAY_INSTALLED=0 $< --target-type gentoo \
		-O $@ --prjroot-relpath \
		-D files --conf-root config --my-conf-root config -A files -W workdir \
		mkconfig

$(S)/R-overlay.conf.others: $(RV_SETUP) FORCE
	@mkdir -p $(@D)
	ROVERLAY_INSTALLED=0 $< --target-type foreign \
		-O $@ --prjroot-relpath \
		-D files --conf-root config --my-conf-root config -A files -W workdir \
		mkconfig

PHONY += generate-config
generate-config: \
	$(S)/config/R-overlay.conf.install \
	$(S)/config/R-overlay.conf.install.others \
	$(S)/R-overlay.conf \
	$(S)/R-overlay.conf.others


PHONY += generate-files
generate-files: $(addprefix generate-,config doc manifest licenses)

PHONY += generate-files-commit
generate-files-commit: gemerate-files
	{ ! $(X_GIT) status --porcelain -- . | grep ^[MADRCU]; }
	$(X_GIT) add -vu -- \
		R-overlay.conf \
		R-overlay.conf.others \
		config/R-overlay.conf.install \
		config/R-overlay.conf.install.others \
		doc/html/ \
		files/licenses
	$(X_GIT) commit -m "update generated files"

# creates a src tarball (.tar.bz2)
PHONY += dist
dist: distclean generate-files | $(PKG_DISTDIR)
ifeq ($(X_BZIP2)$(X_GZIP)$(X_XZ),)
	$(error at least one of X_BZIP2, X_GZIP, X_XZ must be set)
endif
	$(eval MY_$@_BASEVER  := $(shell cat $(VERSION_FILE)))
	test -n '$(MY_$@_BASEVER)'

	$(eval MY_$@_HEADREF := $(shell $(X_GIT) rev-parse --verify HEAD))
	test -n '$(MY_$@_HEADREF)'

	$(eval MY_$@_VREF    := $(shell $(X_GIT) rev-parse --verify $(MY_$@_BASEVER) 2>/dev/null))

ifeq ($(RELEASE_NOT_DIRTY),$(filter $(RELEASE_NOT_DIRTY),$(_TRUE_WORDS)))
	$(eval MY_$@_VER     := $(MY_$@_BASEVER))
else
	$(eval MY_$@_VER     := $(MY_$@_BASEVER)$(shell \
		test "$(MY_$@_HEADREF)" = "$(MY_$@_VREF)" || echo '$(RELEASE_DIRTY_SUFFIX)'))
endif

	$(eval MY_$@_FILE    := $(PKG_DISTDIR)/$(DISTNAME)_$(MY_$@_VER).tar)


	$(X_GIT) archive --worktree-attributes --format=tar HEAD \
		--prefix=$(DISTNAME)_$(MY_$@_VER)/ > $(MY_$@_FILE).make_tmp

ifneq ($(X_BZIP2),)
	$(X_BZIP2) -c $(MY_$@_FILE).make_tmp > $(MY_$@_FILE).bz2
endif
ifneq ($(X_GZIP),)
	$(X_GZIP)  -c $(MY_$@_FILE).make_tmp > $(MY_$@_FILE).gz
endif
ifneq ($(X_XZ),)
	$(X_XZ)    -c $(MY_$@_FILE).make_tmp > $(MY_$@_FILE).xz
endif
	rm -- $(MY_$@_FILE).make_tmp


# rule for compressing a deprule file
$(BUILDDIR)/config/simple-deprules.d/%$(X_COMPRESS_SUFFIX): \
	$(S)/config/simple-deprules.d/%

	@mkdir -p $(@D)
	$(X_COMPRESS) -c $< > $@

# rule for compressing all deprule files
PHONY += _compress-deprules
_compress-deprules: $(shell \
	find $(S)/config/simple-deprules.d/ -type f | sed \
		-e 's,^$(S)/,$(BUILDDIR)/,' -e 's,$$,$(X_COMPRESS_SUFFIX),')

PHONY += compress-config
compress-config: _compress-deprules | $(BUILDDIR)/config
	$(X_COMPRESS) -c config/license.map > $(BUILDDIR)/config/license.map


PHONY += install-config
install-config:
	$(_DODIR) $(CONFDIR)/$(_PN)
	$(_DOINS) -t $(CONFDIR)/$(_PN) \
		config/description_fields.conf config/repo.list \
		config/package_rules config/hookrc
ifeq ($(ROVERLAY_TARGET_TYPE),gentoo)
	$(_DOINS) -T \
		config/R-overlay.conf.install $(CONFDIR)/$(_PN)/R-overlay.conf
else
	$(_DOINS) -T \
		config/R-overlay.conf.install.others $(CONFDIR)/$(_PN)/R-overlay.conf
endif
ifeq ($(COMPRESSED_CONFIG),$(filter $(COMPRESSED_CONFIG),$(_TRUE_WORDS)))
	$(call _f_install_config_files,$(BUILDDIR)/config)
else
	$(call _f_install_config_files,$(S)/config)
endif

PHONY += install-data
install-data:
	$(_DODIR) -- \
		$(addprefix $(DATADIR)/$(_PN)/,shlib hooks eclass mako_templates)

ifeq ($(ROVERLAY_TARGET_TYPE),gentoo)
	$(_DOINS) -- files/setup.defaults $(DATADIR)/setup.defaults
else
	$(_DOINS) -- files/setup.defaults.others $(DATADIR)/setup.defaults
	$(_DOINS) -- $(LICENSES_FILE) $(DATADIR)/$(_PN)/licenses
endif
	$(_DOINS) -t $(DATADIR)/$(_PN)/hooks  -- $(wildcard files/hooks/*.sh)
	chmod $(EXEMODE) -- $(DATADIR)/$(_PN)/hooks/mux.sh
	$(_DOINS) -t $(DATADIR)/$(_PN)/shlib  -- $(wildcard files/shlib/*.sh)
	$(_DOINS) -t $(DATADIR)/$(_PN)/eclass -- $(wildcard files/eclass/*.eclass)
	$(_DOINS) -t $(DATADIR)/$(_PN)/mako_templates -- \
		$(wildcard files/mako_templates/*.*)

PHONY += install-bashcomp
install-bashcomp:
	$(_DODIR) $(BASHCOMPDIR)
	$(foreach f,$(wildcard $(S)/files/misc/*.bashcomp),\
		$(_DOINS) -- $(f) $(BASHCOMPDIR)/$(notdir $(basename $(f))))

PHONY += install
install: $(SETUP_PY)
	$(PYTHON) $< install --root $(DESTDIR) --record $(PYMOD_FILE_LIST)

PHONY += install-nonpy
install-nonpy: $(addprefix install-,data config bashcomp)

PHONY += install-all
install-all: install install-nonpy

PHONY += uninstall
uninstall: $(PYMOD_FILE_LIST)
	xargs rm -vrf < $(PYMOD_FILE_LIST)

PHONY += uninstall-all
uninstall-all:
	@false

PHONY += help
help:
	$(eval MY_$@_GENITIVE := $(_PN)'\''s)

	@echo  'Basic Targets:'
	@echo  '  all                         - do nothing'
	@echo  '  version                     - print $(MY_$@_GENITIVE) version'
	@echo  '  compress-config             - compress config files with X_COMPRESS'
	@echo  '                                 and write them to BUILDDIR/config'
	@echo  '                                 (X_COMPRESS: $(X_COMPRESS))'
	@echo  '                                 (BUILDDIR  : $(BUILDDIR:$(CURDIR)/%=%))'
#	@echo  '  _compress-deprules          - compress dependency rule files with X_COMPRESS'
	@echo  '  test                        - run tests'
	@echo  ''

	@echo  '(Un-)Install Targets:'
	@echo  '  install-all                 - run all targets marked with [I]'
	@echo  '  uninstall-all               - ***not available***'
	@echo  '  install-nonpy               - run all targets marked with [I] except'
	@echo  '                                 "install"'
	@echo  'I install                     - install scripts and python modules to DESTDIR'
	@echo  '                                 (DESTDIR: $(DESTDIR))'
	@echo  '  uninstall                   - uninstall scripts / python modules'
	@echo  'I install-config              - install config files to CONFDIR/$(_PN)'
	@echo  '                                 use compressed files from BUILDDIR where'
	@echo  '                                 applicable if COMPRESSED_CONFIG is "y"'
	@echo  '                                 "compress-config" must be run manually!'
	@echo  '                                 (CONFDIR: $(CONFDIR))'
	@echo  '                                 (COMPRESSED_CONFIG: $(COMPRESSED_CONFIG))'
	@echo  'I install-data                - install data files to DATADIR/$(_PN)'
	@echo  '                                 (DATADIR: $(DATADIR))'
	@echo  'I install-bashcomp            - install bash completion files to BASHCOMPDIR'
	@echo  '                                 (BASHCOMPDIR: $(BASHCOMPDIR))'
	@echo  ''

	@echo  'Cleanup Targets:'
	@echo  '  clean                       - remove temporary dirs'
	@echo  '  distclean                   - remove temporary dirs, .py[co] and pydoc files'
	@echo  '  clean-log                   - remove log file directory LOGDIR'
	@echo  '                                 (LOGDIR: $(LOGDIR:$(CURDIR)/%=%))'
	@echo  '  pyclean                     - remove .py[co] files'
	@echo  '  pydoc_clean                 - remove pydoc files'
	@echo  ''

	@echo  'File Generation Targets:'
	@echo  '  generate-files              - run all targets marked with [G]'
	@echo  '  pydoc                       - create pydoc files (in-code documentation)'
	@echo  '  htmldoc                     - create html documentation (usage guide)'
	@echo  'G generate-doc                - alias to "htmldoc"'
	@echo  'G generate-manifest           - create a MANIFEST file for setup.py'
	@echo  'G generate-licenses           - create a licenses file and write it to'
	@echo  '                                 LICENSES_FILE, for systems without PORTDIR'
	@echo  '                                 (default: $(LICENSES_FILE:$(CURDIR)/%=%))'
	@echo  'G generate-config             - create R-overlay.conf config files'
	@echo  ''

	@echo  'Release/Devel Helper Targets:'
	@echo  '  generate-files-commit       - run "generate-files" and commit changes'
	@echo  '  version-bump                - increase $(MY_$@_GENITIVE) version (patchlevel)'
	@echo  '                                 and git commit/tag depending on VBUMP_COMMIT'
	@echo  '                                 (default: $(VBUMP_COMMIT))'
	@echo  '  setver                      - set $(MY_$@_GENITIVE) version to VER'
	@echo  '                                 (default: <not set>)'
	@echo  '  dist                        - create source tarball(s) in PKG_DISTDIR:'
	@echo  '                                 DISTNAME_<version>.tar.<compression suffix>'
	@echo  '                                 (implies "distclean" and "generate-files")'
	@echo  '                                 (PKG_DISTDIR: $(PKG_DISTDIR:$(CURDIR)/%=%))'
	@echo  '                                 (DISTNAME:    $(DISTNAME))'
	@echo  ''
	@echo  ''
	@echo  'Variables:'
	@echo  '* ROVERLAY_TARGET_TYPE        - controls which files get installed and should'
	@echo  '                                 be either "gentoo" or "foreign" [$(ROVERLAY_TARGET_TYPE)]'
	@echo  '                                 Pick "foreign" for systems'
	@echo  '                                 without portage and/or PORTDIR.'
	@echo  '* COMPRESSED_CONFIG           - whether to install compressed config files (y)'
	@echo  '                                 or not (n) [$(COMPRESSED_CONFIG)]'
	@echo  '* DESTDIR                     - installation root directory'
	@echo  '                                 [$(DESTDIR)]'
	@echo  '* DESTTREE                    - installation directory with prefix'
	@echo  '                                 (DESTDIR/usr/) [$(DESTTREE)]'
	@echo  '* DATADIR                     - directory for data files (DESTTREE/share)'
	@echo  '                                 [$(DATADIR)]'
	@echo  '* BINDIR                      - directory for executables (DESTTREE/bin)'
	@echo  '                                 [$(BINDIR)]'
	@echo  '* CONFDIR                     - system config directory (DESTDIR/etc)'
	@echo  '                                 [$(CONFDIR)]'
	@echo  '* BASHCOMPDIR                 - bashcomp dir (DATADIR/bash-completion)'
	@echo  '                                 [$(BASHCOMPDIR)]'
	@echo  '* DIRMODE                     - mode for installing directories [$(DIRMODE)]'
	@echo  '* INSMODE                     - mode for installing files       [$(INSMODE)]'
	@echo  '* EXEMODE                     - mode for installing scripts     [$(EXEMODE)]'
	@echo  '* PYMOD_FILE_LIST             - file for recording files installed by setup.py'
	@echo  '                                 [$(PYMOD_FILE_LIST:$(CURDIR)/%=%)]'
	@echo  '* BUILDDIR                    - directory for temporary build files, e.g.'
	@echo  '                                 compressed config'
	@echo  '                                 [$(BUILDDIR:$(CURDIR)/%=%)]'
	@echo  ''
	@echo -n  '* PYVER                       - version of the python interpreter '
ifeq ($(PYVER),)
	@echo  '[<unset>]'
else
	@echo  '[$(PYVER)]'
endif
	@echo  '* PYTHON                      - name of/path to python (pythonPYVER) [$(PYTHON)]'
	@echo  '* X_COMPRESS                  - default compression program (X_BZIP2) [$(X_COMPRESS)]'
	@echo  '                                 (used in compress-* targets)'
	@echo  '* X_COMPRESS_SUFFIX           - file extension for compressed deprule files'
	@echo  '                                 (default: depends on X_COMPRESS) [$(X_COMPRESS_SUFFIX)]'
	@echo  '* X_BZIP2                     - name of/path to bzip2 [$(X_BZIP2)]'
	@echo  '* X_GZIP                      - name of/path to gzip  [$(X_GZIP)]'
	@echo  '* X_XZ                        - name of/path to xz    [$(X_XZ)]'
	@echo  '* X_GIT                       - name of/path to git   [$(X_GIT)]'
	@echo  '* X_RST2HTML                  - name of/path to rst2html [$(X_RST2HTML)]'
	@echo  ''
	@echo  '* VBUMP_COMMIT                - whether to commit/tag when running'
	@echo  '                                "version-bump" (y) or not (n) [$(VBUMP_COMMIT)]'
	@echo  '* RELEASE_NOT_DIRTY           - whether to check if the dist tarball actually'
	@echo  '                                matches its version (n) or not (y) [$(RELEASE_NOT_DIRTY)]'
	@echo  '* RELEASE_DIRTY_SUFFIX        - suffix for "dirty" dist tarballs [$(RELEASE_DIRTY_SUFFIX)]'
	@echo  '* DISTNAME                    - base name for source tarballs [$(DISTNAME)]'
	@echo  '* PKG_DISTDIR                 - directory for storing source tarballs'
	@echo  '                                 [$(PKG_DISTDIR:$(CURDIR)/%=%)]'


PHONY += FORCE
FORCE:

.PHONY: $(PHONY)
