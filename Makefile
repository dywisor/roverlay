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

MANIFEST_GEN  := ./scripts/create_manifest.sh

SETUP_PY      := ./setup.py
PKG_DISTDIR   := ./release

LOGDIR        := ./log

ROVERLAY_MAIN := ./roverlay.py

PYVER         :=
PYTHON        := python$(PYVER)
PYDOC_SH       = ./scripts/do_pydoc.sh

RST_HTML       = ./scripts/roverlay_rst2html.sh

SRC_DOCDIR    := ./doc

SELFDOC       := $(SRC_DOCDIR)/pydoc

.PHONY: default \
	clean clean-log _pyclean _pydoc_clean distclean \
	docs pydoc htmldoc \
	check test \
	generate-files \
		generate-doc generate-manifest \
	release dist \
	compress-config \
	install-all install \
		install-roverlay install-pymodules \
		install-data install-config-common \
		install-config-compressed install-config \
	uninstall-all uninstall \
		uninstall-roverlay uninstall-pymodules

default:
	@false

check:
	@true

test: ./bin/run_tests
	./bin/run_tests

clean:
	rm -rf ./build/ $(BUILDDIR)/

clean-log:
	rm -rf -- $(LOGDIR)

_pyclean:
	find . \( -name "*.pyc" -or -name "*.pyo" \) -delete -print

_pydoc_clean:
	rm -f -- $(SELFDOC)/*.html
	! test -d $(SELFDOC) || rmdir --ignore-fail-on-non-empty -- $(SELFDOC)/

distclean: clean _pyclean _pydoc_clean

$(BUILDDIR):
	@install -d $(BUILDDIR)

# generates selfdocs (using pydoc) in $(SELFDOC)/
$(SELFDOC):
	-mkdir $(SELFDOC)
	ln -snfT -- ../../roverlay $(SELFDOC)/roverlay
	$(PYDOC_SH) $(SELFDOC)

# alias to $(SELFDOC)
pydoc: $(SELFDOC)

htmldoc: $(SRC_DOCDIR)/rst/usage.rst
	@install -d $(SRC_DOCDIR)/html
	$(RST_HTML) $(SRC_DOCDIR)/rst/usage.rst $(SRC_DOCDIR)/html/usage.html

generate-doc: htmldoc

generate-manifest: $(MANIFEST_GEN)
	$(MANIFEST_GEN) > $(MANIFEST_TMP)
	mv -- $(MANIFEST_TMP) $(MANIFEST)

generate-files: generate-doc generate-manifest


# creates a src tarball (.tar.bz2)
#  !!! does not include config files
release: generate-files
	@echo "Note: the release tarball does not include any config files!"
	@install -d $(PKG_DISTDIR)
	./$(SETUP_PY) sdist --dist-dir=$(PKG_DISTDIR) --formats=bztar

dist: distclean release

compress-config: $(BUILDDIR)
	@install -d $(BUILDDIR)/config
	cp -vLr -p --no-preserve=ownership config/simple-deprules.d $(BUILDDIR)/config/
	find $(BUILDDIR)/config/simple-deprules.d/ -type f -print0 | xargs -0 -n 5 --verbose bzip2
	bzip2 -k -c config/license.map >  $(BUILDDIR)/config/license.map

install-roverlay: ./roverlay.py
	install -T -D -- ./roverlay.py $(BINDIR)/roverlay

install-pymodules: ./setup.py
	$(PYTHON) ./setup.py install --record $(PYMOD_FILE_LIST)

install-config-common:
	install -m 0755 -d $(CONFDIR)/roverlay
	install -m 0644 -t $(CONFDIR)/roverlay \
		config/description_fields.conf config/repo.list \
		config/package_rules hookrc
	install -m 0644 -T \
		config/R-overlay.conf.install $(CONFDIR)/roverlay/R-overlay.conf

install-config-compressed: install-config-common
	cp -vLr -p --no-preserve=ownership \
		$(BUILDDIR)/config/simple-deprules.d $(BUILDDIR)/config/license.map \
		$(CONFDIR)/roverlay/

install-config: install-config-common
	cp -vLr -p --no-preserve=ownership \
		config/simple-deprules.d config/license.map \
		$(CONFDIR)/roverlay/


# license.map deprules

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

install: install-pymodules install-roverlay

install-all: install

uninstall-roverlay:
	rm -vf -- $(BINDIR)/roverlay

uninstall-pymodules: $(PYMOD_FILE_LIST)
	xargs rm -vrf < $(PYMOD_FILE_LIST)

uinstall:
	@false

uninstall-all: uninstall
