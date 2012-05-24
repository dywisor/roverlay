# runs tests
EXAMPLES = ./examples

PY_DESC_TESTER = ./run_descreader.py
PY_NOP = ./nop.py

.PHONY: default test test-desc test-nop

default: test

test-desc: $(PY_DESC_TESER) $(EXAMPLES)/DESCRIPTION
	$(PY_DESC_TESTER) $(EXAMPLES)/DESCRIPTION/*.desc

test-nop: $(PY_NOP)
	@$(PY_NOP)

test: test-nop test-desc
