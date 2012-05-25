# runs tests
EXAMPLES = ./examples

#PY_DESC_TESTER = ./run_descreader.py
PY_NOP = ./nop.py
PY_EBU = ./run_ebuildcreation.py

.PHONY: default dummy test test-nop test-ebuild_creation test-desc

default: test

dummy:

test-nop: $(PY_NOP)
	@chmod u+x $(PY_NOP)
	@$(PY_NOP)

# test-desc (file) has been removed in favor of test-desc (tar),
#  which has is included in ebuild creation
test-ebuild_creation: test-nop $(PY_EBU) $(EXAMPLES)/packages
	@chmod u+x $(PY_EBU)
	$(PY_EBU) $(EXAMPLES)/packages/*.tar.gz

#test-desc:
# ...

test: test-nop test-ebuild_creation
