#!/bin/bash

# Extract airunner version from setup.py using Python and append ~dev
AIRUNNER_VERSION=$(python3 -c "from distutils.core import run_setup; print(run_setup('setup.py', stop_after='init').get_version())")"~dev"

# Ask for debian version
echo "Enter the debian version: "
read DEBIAN_VERSION

echo "Enter a commit message: "
read MESSAGE

# Create a temporary .gitignore file that does not include venv
grep -v '^dist$' .gitignore > .gitignore.tmp

# Archive
tar -czvf ../airunner_$AIRUNNER_VERSION.orig.tar.gz --exclude-vcs --exclude-from=.gitignore.tmp .

# Remove the temporary .gitignore file
rm .gitignore.tmp

# Update for latest release
dch -v $AIRUNNER_VERSION-$DEBIAN_VERSION -D jammy MESSAGE

# Build
dpkg-buildpackage -S -D -sa

# Upload to PPA
cd ..
dput ppa:capsize/airunner airunner_$AIRUNNER_VERSION-$DEBIAN_VERSION"_source.changes"