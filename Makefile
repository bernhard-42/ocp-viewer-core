.PHONY: clean bump install tests format dist wheel tarball check_dist upload_test upload release

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
#
# `install` is editable on purpose and is how every consumer takes this package
# for now. Run it with the target environment active - there is more than one
# here, and they differ in which OCP provider they carry.

install:
	uv pip install -e .

tests:
	pytest -q

format:
	black .

# Distribution
#
# Both halves are built, neither is published. Python is consumed as an editable
# install and JavaScript as a `yarn pack` tarball, until the whole chain is
# proven - a tarball reference rewrites package.json and the lockfile, so it is
# a development state and never a committed one.
#
# One version covers both halves; `make bump` keeps pyproject.toml,
# _version.py and js/package.json in step, so the wheel and the tarball built
# from one tree always agree.

dist: wheel tarball

wheel:
	@echo "=> Building the Python wheel"
	@rm -f dist/*.whl dist/*.tar.gz
	@python -m build -n

tarball:
	@echo "=> Packing the JavaScript half"
	@mkdir -p dist
	@cd js && yarn pack --filename ../dist/ocp-viewer-core-v$(CURRENT_VERSION).tgz

check_dist:
	@twine check dist/*.whl dist/*.tar.gz
	@echo "=> Contents of the JavaScript tarball"
	@tar tzf dist/ocp-viewer-core-v$(CURRENT_VERSION).tgz

upload_test:
	@twine upload --repository testpypi dist/*

upload:
	@twine upload dist/*

release:
	git add .
	git status
	git diff-index --quiet HEAD || git commit -m "Latest release: $(CURRENT_VERSION)"
	git tag -a v$(CURRENT_VERSION) -m "Latest release: $(CURRENT_VERSION)"
