# Some make targets for testing / distribution

# don't create bytecode files when running py scripts (racy)
unexport PYTHONDONTWRITEBYTECODE
export PYTHONDONTWRITEBYTECODE=y

DESTDIR  := /
DESTTREE := $(DESTDIR)usr/

DATADIR  := $(DESTTREE)share
BINDIR   := $(DESTTREE)bin
CONFDIR  := $(DESTDIR)etc

BUILDDIR := ./tmp

ROVERLAY_TARGET_TYPE := gentoo
RELEASE_NOT_DIRTY    := n
RELEASE_DIRTY_SUFFIX := -dirty
VBUMP_COMMIT         := y

PYMOD_FILE_LIST := ./roverlay_files.list

MANIFEST      := $(CURDIR)/MANIFEST
LICENSES_FILE := $(CURDIR)/files/licenses
VERSION_FILE  := $(CURDIR)/VERSION

X_GIT         := git

MANIFEST_GEN  := ./bin/build/create_manifest.sh
LICENSES_GEN  := ./bin/build/make-licenses.sh
X_SETVER      := ./bin/build/setver.sh
RV_SETUP      := ./bin/roverlay-setup

SETUP_PY      := ./setup.py
PKG_DISTDIR   := ./release

LOGDIR        := ./log

ROVERLAY_MAIN := ./roverlay.py

PYVER         :=
PYTHON        := python$(PYVER)
PYDOC_SH      := ./bin/build/do_pydoc.sh
X_COMPRESS    := bzip2

RST_HTML      := ./bin/build/roverlay_rst2html.sh

SRC_DOCDIR    := ./doc

SELFDOC       := $(SRC_DOCDIR)/pydoc

PHONY += all
all:

PHONY += check
check:
	@true

PHONY += version
version:
	@cat $(VERSION_FILE)

PHONY += setver
setver: $(X_SETVER)
ifeq ($(VER),)
	$(error $$VER is not set.)
else
	$< $(VER)
endif

PHONY += version-bump
version-bump: $(X_SETVER)
	{ ! $(X_GIT) status --porcelain -- $(notdir $(VERSION_FILE)) | grep .; }
ifeq ($(VBUMP_COMMIT),$(filter $(VBUMP_COMMIT),y Y 1 yes YES true TRUE))
	X_GIT="$(X_GIT)" $< --reset --git-add --git-commit --git-tag +
else
	X_GIT="$(X_GIT)" $< --reset --git-add +
endif

PHONY += test
test: ./bin/run_tests
	./bin/run_tests

PHONY += clean
clean:
	rm -rf ./build/ $(BUILDDIR)/

PHONY += clean-log
clean-log:
	rm -rf -- $(LOGDIR)

PHONY += _pyclean
_pyclean: | clean
	find . \( -name "*.pyc" -or -name "*.pyo" \) -delete -print

PHONY += _pydoc_clean
_pydoc_clean:
	rm -f -- $(SELFDOC)/*.html
	test ! -d $(SELFDOC) || rmdir --ignore-fail-on-non-empty -- $(SELFDOC)/

PHONY += distclean
distclean: clean _pyclean _pydoc_clean

$(BUILDDIR):
	@install -d $(BUILDDIR)

# generates selfdocs (using pydoc) in $(SELFDOC)/
$(SELFDOC): | _pydoc_clean
	-mkdir $(SELFDOC)
	ln -snfT -- ../../roverlay $(SELFDOC)/roverlay
	$(PYDOC_SH) $(SELFDOC)

# alias to $(SELFDOC)
PHONY += pydoc
pydoc: $(SELFDOC)

PHONY += htmldoc
htmldoc: $(SRC_DOCDIR)/rst/usage.rst
	@install -d $(SRC_DOCDIR)/html
	$(RST_HTML) $(SRC_DOCDIR)/rst/usage.rst $(SRC_DOCDIR)/html/usage.html

PHONY += generate-doc
generate-doc: htmldoc

$(MANIFEST): $(MANIFEST_GEN) FORCE
	$< > $@

PHONY += generate-manifest
generate-manifest: $(MANIFEST)

$(LICENSES_FILE): $(LICENSES_GEN) FORCE | $(CURDIR)/files
	$< $@

PHONY += generate-licenses
generate-licenses: $(CURDIR)/files/licenses



$(CURDIR)/config/R-overlay.conf.install: $(RV_SETUP) FORCE | $(CURDIR)/config
	ROVERLAY_INSTALLED=1 $< --target-type gentoo \
		-O $@ \
		-D $(DATADIR)/roverlay \
		--conf-root $(CONFDIR)/roverlay --my-conf-root $(CONFDIR)/roverlay \
		-A $(CONFDIR)/roverlay/files \
		mkconfig

$(CURDIR)/config/R-overlay.conf.install.others: $(RV_SETUP) FORCE | $(CURDIR)/config
	ROVERLAY_INSTALLED=1 $< --target-type foreign \
		-O $@ \
		-D $(DATADIR)/roverlay \
		--conf-root $(CONFDIR)/roverlay --my-conf-root $(CONFDIR)/roverlay \
		-A $(CONFDIR)/roverlay/files \
		mkconfig

$(CURDIR)/R-overlay.conf: $(RV_SETUP) FORCE
	ROVERLAY_INSTALLED=0 $< --target-type gentoo \
		-O $@ --prjroot-relpath \
		-D files --conf-root config --my-conf-root config -A files -W workdir \
		mkconfig

$(CURDIR)/R-overlay.conf.others: $(RV_SETUP) FORCE
	ROVERLAY_INSTALLED=0 $< --target-type foreign \
		-O $@ --prjroot-relpath \
		-D files --conf-root config --my-conf-root config -A files -W workdir \
		mkconfig

PHONY += generate-config
generate-config: \
	$(CURDIR)/config/R-overlay.conf.install \
	$(CURDIR)/config/R-overlay.conf.install.others \
	$(CURDIR)/R-overlay.conf \
	$(CURDIR)/R-overlay.conf.others


PHONY += generate-files
generate-files: generate-config generate-doc generate-manifest generate-licenses

# creates a src tarball (.tar.bz2)
PHONY += release
release: generate-files
	$(eval MY_$@_BASEVER  := $(shell cat $(VERSION_FILE)))
	test -n '$(MY_$@_BASEVER)'
	$(eval MY_$@_HEADREF := $(shell git rev-parse --verify HEAD))
	test -n '$(MY_$@_HEADREF)'
	$(eval MY_$@_VREF    := $(shell git rev-parse --verify $(MY_$@_BASEVER) 2>/dev/null))
ifeq ($(RELEASE_NOT_DIRTY),$(filter $(RELEASE_NOT_DIRTY),y Y 1 yes YES true TRUE))
	$(eval MY_$@_VER     := $(MY_$@_BASEVER))
else
	$(eval MY_$@_VER     := $(MY_$@_BASEVER)$(shell \
		test "$(MY_$@_HEADREF)" = "$(MY_$@_VREF)" || echo '$(RELEASE_DIRTY_SUFFIX)'))
endif
	$(eval MY_$@_FILE    := $(PKG_DISTDIR)/roverlay_$(MY_$@_VER).tar)

	install -d -m 0755 -- $(PKG_DISTDIR)
	git archive --worktree-attributes --format=tar HEAD \
		--prefix=roverlay_$(MY_$@_VER)/ > $(MY_$@_FILE).make_tmp

	bzip2 -c $(MY_$@_FILE).make_tmp > $(MY_$@_FILE).bz2
	rm -- $(MY_$@_FILE).make_tmp


PHONY += dist
dist: distclean release

PHONY += compress-config
compress-config: $(BUILDDIR)
	@install -d $(BUILDDIR)/config
	cp -vLr -p --no-preserve=ownership config/simple-deprules.d $(BUILDDIR)/config/
	find $(BUILDDIR)/config/simple-deprules.d/ -type f -print0 | xargs -0 -n 5 --verbose $(X_COMPRESS)
	$(X_COMPRESS) -c config/license.map >  $(BUILDDIR)/config/license.map

PHONY += install-roverlay
install-roverlay: ./roverlay.py
	install -T -D -- ./roverlay.py $(BINDIR)/roverlay

PHONY += install-pymodules
install-pymodules: ./setup.py
	$(PYTHON) ./setup.py install --record $(PYMOD_FILE_LIST)

PHONY += install-config-common
install-config-common:
	install -m 0755 -d $(CONFDIR)/roverlay
	install -m 0644 -t $(CONFDIR)/roverlay \
		config/description_fields.conf config/repo.list \
		config/package_rules config/hookrc
ifeq ($(ROVERLAY_TARGET_TYPE),gentoo)
	install -m 0644 -T \
		config/R-overlay.conf.install $(CONFDIR)/roverlay/R-overlay.conf
else
	install -m 0644 -T \
		config/R-overlay.conf.install.others $(CONFDIR)/roverlay/R-overlay.conf
endif

PHONY += install-config-compressed
install-config-compressed: install-config-common
	cp -vLr -p --no-preserve=ownership \
		$(BUILDDIR)/config/simple-deprules.d $(BUILDDIR)/config/license.map \
		$(CONFDIR)/roverlay/

PHONY += install-config
install-config: install-config-common
	cp -vLr -p --no-preserve=ownership \
		config/simple-deprules.d config/license.map \
		$(CONFDIR)/roverlay/


# license.map deprules
PHONY += install-data
install-data:
	install -m 0755 -d \
		$(DATADIR)/roverlay \
		$(DATADIR)/roverlay/shlib $(DATADIR)/roverlay/hooks \
		$(DATADIR)/roverlay/eclass $(DATADIR)/roverlay/mako_templates

ifeq ($(ROVERLAY_TARGET_TYPE),gentoo)
	install -m 0644 -- files/setup.defaults $(DATADIR)/setup.defaults
else
	install -m 0644 -- files/setup.defaults.others $(DATADIR)/setup.defaults
	install -m 0644 -- $(LICENSES_FILE) $(DATADIR)/roverlay/licenses
endif
	install -m 0644 -t $(DATADIR)/roverlay/hooks files/hooks/*.sh
	install -m 0644 -t $(DATADIR)/roverlay/shlib files/shlib/*.sh
	chmod 0775 $(DATADIR)/roverlay/hooks/mux.sh

	install -m 0644 -t $(DATADIR)/roverlay/eclass files/eclass/*.eclass

	install -m 0644 -t $(DATADIR)/roverlay/mako_templates \
		files/mako_templates/*.*

PHONY += install
install: install-pymodules install-roverlay

PHONY += install-all
install-all: install

PHONY += uninstall-roverlay
uninstall-roverlay:
	rm -vf -- $(BINDIR)/roverlay

PHONY += uninstall-pymodules
uninstall-pymodules: $(PYMOD_FILE_LIST)
	xargs rm -vrf < $(PYMOD_FILE_LIST)

PHONY += uninstall
uinstall:
	@false

PHONY += uninstall-all
uninstall-all: uninstall

PHONY += FORCE
FORCE:

.PHONY: $(PHONY)
