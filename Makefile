.PHONY: clean bump dist check_dist upload_test upload release tests format

PYCACHE := $(shell find . -name '__pycache__')
EGGS := $(wildcard *.egg-info)
CURRENT_VERSION := $(shell awk '/current_version =/ {print substr($$3, 2, length($$3)-2)}' pyproject.toml)

clean:
	@echo "=> Cleaning"
	@rm -fr build dist $(EGGS) $(PYCACHE)

# Version commands

bump:
	@echo Current version: $(CURRENT_VERSION)
ifdef part
	bump-my-version bump $(part) --allow-dirty && grep current pyproject.toml
else ifdef version
	bump-my-version bump --allow-dirty --new-version $(version) && grep current pyproject.toml
else
	@echo "Provide part=major|minor|patch or version=x.y.z"
	exit 1
endif

# Development

tests:
	pytest -q tests/

format:
	black ocp_viewer_core tests

# Distribution

dist:
	@rm -f dist/*
	@python -m build -n

check_dist:
	@twine check dist/*

upload_test:
	@twine upload --repository testpypi dist/*

upload:
	@twine upload dist/*

release:
	git add .
	git status
	git diff-index --quiet HEAD || git commit -m "Latest release: $(CURRENT_VERSION)"
	git tag -a v$(CURRENT_VERSION) -m "Latest release: $(CURRENT_VERSION)"
