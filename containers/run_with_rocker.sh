#!/usr/bin/env bash
# Needs rocker installed (https://github.com/osrf/rocker eases using GPUs/graphical things in docker in between other things):
# pip install rocker
# pip install off-your-rocker

# Absolute path to this script
SCRIPT=$(readlink -f $0)
# Absolute path this script is in
SCRIPTPATH=`dirname $SCRIPT`
# with this it runs on GPU!
rocker --nvidia --x11 --privileged --network host --volume $SCRIPTPATH/..:/root/airunner -- airunner_image_with_pip_install bash

# Now we can do
# cd airunner/src/airunner && python main.py