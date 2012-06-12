# runs tests
EXAMPLES = ./examples

# make PYVER=<2|3> <target>
PYVER = 3
PY = python$(PYVER)

LOGDIR = ./log

PY_NOP = ./nop.py
PY_EBU = ./run_ebuildcreation.py
PY_EBU2 = ./test_ebuildcreation.sh

.PHONY: default dummy test test-nop \
	test-ebuild_creation \
	test-ebuild_creation2 \
	test-ebuild_creation3 \
	test-seewave seewave

default: dummy test

clean-log:
	rm -fv -- $(LOGDIR)/*.log

$(LOGDIR):
	mkdir -v $(LOGDIR)

dummy:
	$(PY) --version

seewave: test-seewave

test-seewave: test-nop $(PY_EBU) $(EXAMPLES)/packages
	$(PY) $(PY_EBU) $(EXAMPLES)/packages/seewave_*.tar.gz

test-nop: $(PY_NOP) $(LOGDIR)
	@$(PY) $(PY_NOP)

# test-desc (file) has been removed in favor of test-desc (tar),
#  which is included in ebuild creation
test-ebuild_creation: test-nop $(PY_EBU) $(EXAMPLES)/packages
	$(PY) $(PY_EBU) $(EXAMPLES)/packages/*.tar.gz

test-ebuild_creation2: test-nop $(PY_EBU) $(PY_EBU2) $(EXAMPLES)/packages /bin/bash
	PYTHON=$(PY) /bin/bash $(PY_EBU2) -q 100

test-ebuild_creation3: test-nop $(PY_EBU) $(PY_EBU2) $(EXAMPLES)/packages /bin/bash
	PYTHON=$(PY) /bin/bash $(PY_EBU2) -q 1000

test: test-nop test-ebuild_creation test-ebuild_creation2 test-seewave
