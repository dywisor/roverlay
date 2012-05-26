# runs tests
EXAMPLES = ./examples

# make PYVER=<2|3> <target>
PYVER = 3
PY = python$(PYVER)

PY_DESC_TESTER = ./run_descreader.py
PY_NOP = ./nop.py
PY_EBU = ./run_ebuildcreation.py

.PHONY: default dummy test test-nop \
	test-ebuild_creation test-desc

default: dummy test

dummy:
	$(PY) --version

test-nop: $(PY_NOP)
	@$(PY) $(PY_NOP)

# test-desc (file) has been removed in favor of test-desc (tar),
#  which is included in ebuild creation
test-ebuild_creation: test-nop $(PY_EBU) $(EXAMPLES)/packages
	$(PY) $(PY_EBU) $(EXAMPLES)/packages/*.tar.gz

test-desc: test-nop $(PY_DESC_TESTER) $(EXAMPLES)/packages
	$(PY) $(PY_DESC_TESTER) $(EXAMPLES)/packages/*.tar.gz

test: test-nop test-desc test-ebuild_creation
