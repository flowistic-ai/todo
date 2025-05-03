# justfile for Python package version bump, build, and PyPI upload

# Usage:
# just bump-version x.y.z   # Set new version in pyproject.toml
# just build                # Build the wheel and sdist
# just upload               # Upload to PyPI (requires .pypirc and twine)

set shell := ["bash", "-cu"]

bump-version version:
    sed -i '' "s/^version = \".*\"/version = \"{{version}}\"/" pyproject.toml
    echo "Version set to {{version}} in pyproject.toml"

build:
    rm -rf dist/
    uv run python -m build

upload:
    uv run twine upload --repository pypi --config-file .pypirc dist/*
