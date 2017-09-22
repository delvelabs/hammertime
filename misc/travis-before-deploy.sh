#!/bin/sh

if [ -z "$TRAVIS_TAG" ]; then
    echo "Travis Tag environment is required"
    exit 1
fi

echo "__version__ = '$TRAVIS_TAG'" >> hammertime/__version__.py
