# runs tests
EXAMPLES = ./examples
PACKAGES = $(EXAMPLES)/packages

# make PYVER=<2|3> <target>
PYVER = 3
PY = python$(PYVER)

LOGDIR = ./log

SYNC   = ./run_sync.py
PY_NOP = ./nop.py
PY_OVL = ./run_overlaycreation.py

.PHONY: default dummy \
	test test-nop nop \
	test-seewave seewave \
	clean-log \
	download

download: test-nop $(SYNC)
	$(PY) $(SYNC)

default: dummy test

seewave: test-seewave
nop: test-nop

clean-log:
	rm -fv -- $(LOGDIR)/*.log

$(LOGDIR):
	mkdir -v $(LOGDIR)

dummy:
	$(PY) --version

test-seewave: test-nop $(PY_OVL) $(PACKAGES)
	$(PY) $(PY_OVL) --show $(PACKAGES)/seewave_*.tar.gz

test-nop: $(PY_NOP) $(LOGDIR)
	@$(PY) $(PY_NOP)

test: test-nop test-seewave
