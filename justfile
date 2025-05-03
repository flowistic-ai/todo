# justfile for Python package version bump, build, and PyPI upload

# Usage:
# just bump-version x.y.z   # Set new version in pyproject.toml
# just build                # Build the wheel and sdist
# just upload               # Upload to PyPI (requires .pypirc and twine)

set shell := ["bash", "-cu"]

bump-version version:
    if [ -z "{{version}}" ] || [ "{{version}}" = "_" ]; then \
      current_version=$(grep '^version = "' pyproject.toml | sed 's/version = \"\(.*\)\"/\1/'); \
      IFS='.' read -r major minor patch <<< "$$current_version"; \
      patch=$$(($$patch + 1)); \
      new_version="$$major.$$minor.$$patch"; \
    else \
      new_version="{{version}}"; \
    fi; \
    sed -i '' "s/^version = \".*\"/version = \"$$new_version\"/" pyproject.toml; \
    echo "Version set to $$new_version in pyproject.toml"

build:
    rm -rf dist/
    uv run python -m build

upload:
    uv run twine upload --repository pypi --config-file .pypirc dist/*
