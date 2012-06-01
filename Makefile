# runs tests
EXAMPLES = ./examples

# make PYVER=<2|3> <target>
PYVER = 3
PY = python$(PYVER)

PY_NOP = ./nop.py
PY_EBU = ./run_ebuildcreation.py
PY_EBU2 = ./test_ebuildcreation.sh

.PHONY: default dummy test test-nop test-ebuild_creation test-ebuild_creation2

default: dummy test

dummy:
	$(PY) --version

test-nop: $(PY_NOP)
	@$(PY) $(PY_NOP)

# test-desc (file) has been removed in favor of test-desc (tar),
#  which is included in ebuild creation
test-ebuild_creation: test-nop $(PY_EBU) $(EXAMPLES)/packages
	$(PY) $(PY_EBU) $(EXAMPLES)/packages/*.tar.gz

test-ebuild_creation2: test-nop $(PY_EBU) $(PY_EBU2) $(EXAMPLES)/packages /bin/bash
	PYTHON=$(PY) /bin/bash $(PY_EBU2) -q 1000

test: test-nop test-ebuild_creation test-ebuild_creation2
