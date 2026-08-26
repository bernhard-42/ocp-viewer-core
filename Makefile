.PHONY: clean bump bump-py bump-js install tests check dist wheel tarball check_dist upload_test upload release

PYCACHE := $(shell find . -name '__pycache__')
EGGS := $(wildcard *.egg-info)
PY_VERSION := $(shell awk '/current_version =/ {print substr($$3, 2, length($$3)-2)}' .bumpversion-py.toml)
JS_VERSION := $(shell awk '/current_version =/ {print substr($$3, 2, length($$3)-2)}' .bumpversion-js.toml)

clean:
	@echo "=> Cleaning"
	@rm -fr build dist $(EGGS) $(PYCACHE)

# Version commands
#
# major.minor is the contract between the two halves and moves together
# (`make bump part=minor`); the patch level is each half's own, so a fix on
# one side ships without an artificial release of the other
# (`make bump-py part=patch`, `make bump-js part=patch`). See Development.md.

bump-py:
	@echo Current Python version: $(PY_VERSION)
ifdef part
	bump-my-version bump $(part) --config-file .bumpversion-py.toml --allow-dirty && grep current .bumpversion-py.toml
else ifdef version
	bump-my-version bump --config-file .bumpversion-py.toml --allow-dirty --new-version $(version) && grep current .bumpversion-py.toml
else
	@echo "Provide part=major|minor|patch or version=x.y.z"
	exit 1
endif

bump-js:
	@echo Current JavaScript version: $(JS_VERSION)
ifdef part
	bump-my-version bump $(part) --config-file .bumpversion-js.toml --allow-dirty && grep current .bumpversion-js.toml
else ifdef version
	bump-my-version bump --config-file .bumpversion-js.toml --allow-dirty --new-version $(version) && grep current .bumpversion-js.toml
else
	@echo "Provide part=major|minor|patch or version=x.y.z"
	exit 1
endif

bump: bump-py bump-js
	@echo "Python: $$(awk '/current_version =/ {print substr($$3, 2, length($$3)-2)}' .bumpversion-py.toml), JavaScript: $$(awk '/current_version =/ {print substr($$3, 2, length($$3)-2)}' .bumpversion-js.toml)"

# Development
#
# `install` is editable on purpose and is how every consumer takes this package
# for now. Run it with the target environment active - there is more than one
# here, and they differ in which OCP provider they carry.

install:
	uv pip install -e .

tests:
	pytest -q

# The whole toolchain. No formatter, on purpose - see the note in pyproject.toml.

check:
	uvx ruff@0.16.0 check ocp_viewer_core/
	uvx ty@0.0.62 check ocp_viewer_core/

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
	@cd js && yarn pack --filename ../dist/ocp-viewer-core-v$(JS_VERSION).tgz

check_dist:
	@twine check dist/*.whl dist/*.tar.gz
	@echo "=> Contents of the JavaScript tarball"
	@tar tzf dist/ocp-viewer-core-v$(JS_VERSION).tgz

upload_test:
	@twine upload --repository testpypi dist/*

upload:
	@twine upload dist/*.whl dist/*.tar.gz

release:
	git add .
	git status
	git diff-index --quiet HEAD || git commit -m "Latest release: py $(PY_VERSION), js $(JS_VERSION)"
	git tag -a v$(PY_VERSION) -m "Latest release: py $(PY_VERSION), js $(JS_VERSION)"
