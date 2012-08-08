# Some make targets for testing / distribution

# DESTDIR :=
BINDIR          := $(DESTDIR)/usr/local/bin
PYMOD_FILE_LIST := ./roverlay_files.list

MANIFEST      := MANIFEST
MANIFEST_TMP  := $(MANIFEST).tmp

MANIFEST_GEN  := ./create_manifest.sh

SETUP_PY      := ./setup.py
PKG_DISTDIR   := ./release

LOGDIR        := ./log

ROVERLAY_MAIN := ./roverlay.py

PYVER         :=
PYTHON        := python$(PYVER)
PYDOC_SH       = ./do_pydoc.sh

DOCDIR        := ./doc

SELFDOC       := $(DOCDIR)/pydoc

.PHONY: $(MANIFEST_TMP) $(MANIFEST) \
	default \
	clean-log clean distclean _pyclean _pydoc_clean \
	run-test run-sync test \
	pydoc $(SELFDOC) $(DOCDIR) doc \
	pyver \
	install install-all \
		install-roverlay install-pymodules \
	uninstall uninstall-all \
		uninstall-roverlay uninstall-pymodules

default:
	@false

pyver:
	@$(PYTHON) --version

clean-log:
	rm -rf -- $(LOGDIR)

clean:
	rm -rf build/

_pyclean:
	find . -name "*.pyc" -or -name "*.pyo" -delete

_pydoc_clean:
	rm -f -- $(SELFDOC)/*.html
	! test -d $(SELFDOC) || rmdir --ignore-fail-on-non-empty -- $(SELFDOC)/

distclean: clean _pyclean _pydoc_clean

# generates docs in $(DOCDIR)/
$(DOCDIR): $(SELFDOC)
docs: $(DOCDIR)

$(SELFDOC)/roverlay:
	test -d $(SELFDOC) || mkdir -p $(SELFDOC)
	@ln -s ../../roverlay $(SELFDOC)/roverlay

# generates selfdocs (using pydoc) in $(SELFDOC)/
$(SELFDOC): $(SELFDOC)/roverlay
	$(PYDOC_SH) $(SELFDOC)

# alias to $(SELFDOC)
pydoc: $(SELFDOC)

# sync all repos
run-sync: $(ROVERLAY_MAIN)
	$(PYTHON) $(ROVERLAY_MAIN) sync

# this is the 'default' test run command
run-test: $(ROVERLAY_MAIN)
	$(PYTHON) $(ROVERLAY_MAIN) --nosync --stats -O /tmp/overlay

# sync and do a test run afterwards
test: run-sync run-test

$(MANIFEST_TMP): $(MANIFEST_GEN)
	$(MANIFEST_GEN) > $(MANIFEST_TMP)

# creates a MANIFEST file for setup.py
$(MANIFEST): $(MANIFEST_TMP)
	mv -- $(MANIFEST_TMP) $(MANIFEST)

# creates a src tarball (.tar.bz2)
release: $(MANIFEST) $(SETUP_PY)
	@test -d $(PKG_DISTDIR) || @mkdir -- $(PKG_DISTDIR)
	./$(SETUP_PY) sdist --dist-dir=$(PKG_DISTDIR) --formats=bztar


install-roverlay: ./roverlay.py
	install -T -D -- ./roverlay.py $(BINDIR)/roverlay

install-pymodules: ./setup.py
	$(PYTHON) ./setup.py install --record $(PYMOD_FILE_LIST)

install-all: install

install: install-pymodules install-roverlay

uninstall-roverlay:
	rm -vf -- $(BINDIR)/roverlay

uninstall-pymodules: $(PYMOD_FILE_LIST)
	xargs rm -vrf < $(PYMOD_FILE_LIST)

uninstall-all: uninstall

uinstall:
	@false
