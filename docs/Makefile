# AURA documentation build

.PHONY: all html typedoc clean

all: html typedoc

html:
	@echo "==> Building Python docs (Sphinx)..."
	$(MAKE) -C sphinx html

typedoc:
	@echo "==> Building TypeScript docs (TypeDoc)..."
	cd ../frontend && npx typedoc --options ../docs/typedoc/typedoc.json

clean:
	$(MAKE) -C sphinx clean
	rm -rf typedoc/output
