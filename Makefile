# Some make targets for testing / distribution

DESTDIR  := /
DESTTREE := $(DESTDIR)usr/

DATADIR  := $(DESTTREE)share
BINDIR   := $(DESTTREE)bin
CONFDIR  := $(DESTDIR)etc

BUILDDIR := ./tmp


PYMOD_FILE_LIST := ./roverlay_files.list

MANIFEST      := MANIFEST
MANIFEST_TMP  := $(MANIFEST).tmp

MANIFEST_GEN  := ./bin/build/create_manifest.sh

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

PHONY += default
default:
	@false

PHONY += check
check:
	@true

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
_pyclean:
	find . \( -name "*.pyc" -or -name "*.pyo" \) -delete -print

PHONY += _pydoc_clean
_pydoc_clean:
	rm -f -- $(SELFDOC)/*.html
	! test -d $(SELFDOC) || rmdir --ignore-fail-on-non-empty -- $(SELFDOC)/

PHONY += distclean
distclean: clean _pyclean _pydoc_clean

$(BUILDDIR):
	@install -d $(BUILDDIR)

# generates selfdocs (using pydoc) in $(SELFDOC)/
$(SELFDOC):
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

PHONY += generate-manifest
generate-manifest: $(MANIFEST_GEN)
	$(MANIFEST_GEN) > $(MANIFEST_TMP)
	mv -- $(MANIFEST_TMP) $(MANIFEST)


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
generate-files: generate-config generate-doc generate-manifest

# creates a src tarball (.tar.bz2)
#  !!! does not include config files
PHONY += release
release: generate-files
	@echo "Note: the release tarball does not include any config files!"
	@install -d $(PKG_DISTDIR)
	./$(SETUP_PY) sdist --dist-dir=$(PKG_DISTDIR) --formats=bztar

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
	install -m 0644 -T \
		config/R-overlay.conf.install $(CONFDIR)/roverlay/R-overlay.conf

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
		$(DATADIR)/roverlay/shlib $(DATADIR)/roverlay/hooks \
		$(DATADIR)/roverlay/eclass $(DATADIR)/roverlay/mako_templates

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
