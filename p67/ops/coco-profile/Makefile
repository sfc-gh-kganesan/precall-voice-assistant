SHELL := /bin/bash
DIR := $(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))
PROFILE_JSON := $(DIR)/profile.json

VERSION := $(shell python3 -c "import json; print(json.load(open('$(PROFILE_JSON)'))['version'])")
MAJOR := $(shell echo $(VERSION) | cut -d. -f1)
MINOR := $(shell echo $(VERSION) | cut -d. -f2)
PATCH := $(shell echo $(VERSION) | cut -d. -f3)

.PHONY: publish bump-patch bump-minor bump-major version release help

help:
	@echo "P67 CoCo Profile"
	@echo ""
	@echo "  make release      Bump patch version and publish (the one-shot)"
	@echo "  make publish      Publish current version ($(VERSION)) without bumping"
	@echo "  make bump-patch   Bump patch  ($(VERSION) -> $(MAJOR).$(MINOR).$(shell echo $$(($(PATCH)+1))))"
	@echo "  make bump-minor   Bump minor  ($(VERSION) -> $(MAJOR).$(shell echo $$(($(MINOR)+1))).0)"
	@echo "  make bump-major   Bump major  ($(VERSION) -> $(shell echo $$(($(MAJOR)+1))).0.0)"
	@echo "  make version      Show current version"

version:
	@echo $(VERSION)

bump-patch:
	@NEW_VERSION="$(MAJOR).$(MINOR).$(shell echo $$(($(PATCH)+1)))"; \
	python3 -c "import json; \
	d = json.load(open('$(PROFILE_JSON)')); \
	d['version'] = '$$NEW_VERSION'; \
	json.dump(d, open('$(PROFILE_JSON)', 'w'), indent=2); \
	print()"; \
	echo "Bumped $(VERSION) -> $$NEW_VERSION"

bump-minor:
	@NEW_VERSION="$(MAJOR).$(shell echo $$(($(MINOR)+1))).0"; \
	python3 -c "import json; \
	d = json.load(open('$(PROFILE_JSON)')); \
	d['version'] = '$$NEW_VERSION'; \
	json.dump(d, open('$(PROFILE_JSON)', 'w'), indent=2); \
	print()"; \
	echo "Bumped $(VERSION) -> $$NEW_VERSION"

bump-major:
	@NEW_VERSION="$(shell echo $$(($(MAJOR)+1))).0.0"; \
	python3 -c "import json; \
	d = json.load(open('$(PROFILE_JSON)')); \
	d['version'] = '$$NEW_VERSION'; \
	json.dump(d, open('$(PROFILE_JSON)', 'w'), indent=2); \
	print()"; \
	echo "Bumped $(VERSION) -> $$NEW_VERSION"

publish:
	@$(DIR)/publish.sh

release: bump-patch publish
	@echo ""
	@echo "Released version $$(python3 -c "import json; print(json.load(open('$(PROFILE_JSON)'))['version'])")"
	@echo "Tell users to run: cortex profile sync p67 -c snowhouse"
