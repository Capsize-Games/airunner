#!/bin/bash

# Extract airunner version from setup.py using Python
AIRUNNER_VERSION=$(python3 -c "from distutils.core import run_setup; print(run_setup('setup.py', stop_after='init').get_version())")

# Ask for debian version
echo "Enter the debian version: "
read DEBIAN_VERSION

echo "Enter a commit message: "
read MESSAGE

# Update for latest release
dch -v $AIRUNNER_VERSION-$DEBIAN_VERSION -D jammy MESSAGE

# Archive
git archive --format=tar.gz --prefix=airunner-$AIRUNNER_VERSION/ -o ../airunner_$AIRUNNER_VERSION.orig.tar.gz HEAD

# Build
dpkg-buildpackage -S -D -sa

# Upload to PPA
dput ppa:capsize/airunner airunner_$AIRUNNER_VERSION-$DEBIAN_VERSION"_source.changes
