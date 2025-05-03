#!/usr/bin/env bash
set -e

if [ -z "$1" ]; then
    # No version supplied, bump patch version
    current_version=$(grep '^version = "' pyproject.toml | sed 's/version = "\(.*\)"/\1/')
    IFS='.' read -r major minor patch <<< "$current_version"
    patch=$((patch + 1))
    new_version="${major}.${minor}.${patch}"
else
    new_version="$1"
fi

# Update pyproject.toml
sed -i '' "s/^version = \".*\"/version = \"${new_version}\"/" pyproject.toml
echo "Version set to ${new_version} in pyproject.toml"
