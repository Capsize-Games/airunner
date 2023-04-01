#!/usr/bin/env bash
#set -o xtrace

# Necessary to open windows
xhost local:root

# Absolute path to this script
SCRIPT=$(readlink -f $0)
# Absolute path this script is in
SCRIPTPATH=`dirname $SCRIPT`

# Get the PlotJuggler repo path to mount in the container
MOUNT_LOCAL_REPO="-v $SCRIPTPATH/..:/root/airunner"
# Optional nvidia runtime, needs nvidia runtime installed (https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html)
#RUNTIME=--runtime=nvidia
RUNTIME=
# Note: privileged, net host, and devices may be an overkill

docker run \
    -it \
    --rm \
    -v /tmp/.X11-unix:/tmp/.X11-unix \
    --env="DISPLAY=${DISPLAY}" \
    $MOUNT_LOCAL_REPO \
    --privileged \
    --net=host \
    --ipc=host \
    $RUNTIME \
    -v /dev:/dev \
    --name airunner_container \
    airunner_image bash  

# Now we can do:
# cd airunner/src/airunner && python main.py
