#!/usr/bin/env bash
# run NPM install for every subproject in this repository

find . -name package.json -not -path "*/node_modules/*" | while read -r pkg; do
    dir=$(dirname "$pkg")
    echo "Updating $dir/package.json"
    (
        cd "$dir" || exit
        npm install #--package-lock-only
    )
done