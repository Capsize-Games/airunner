#!/bin/bash

# Change current working directory to the directory of the script
cd "$(dirname "$0")"

# Linux prerequisites
sudo apt update
sudo apt install fonts-noto-color-emoji
sudo apt install libportaudio2 libxcb-cursor0 espeak xclip

# Create and activate virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate

# Ask user if they want to clone the airunner repository or use existing directory
read -p "Do you want to clone the airunner repository? (y/n) " clone_airunner

if [[ $clone_airunner == "y" || $clone_airunner == "Y" ]]; then
    # Source installation
    if [ ! -d "airunner" ]; then
        git clone -b develop https://github.com/Capsize-Games/airunner.git
    fi
    cd airunner && pip install -e .
else
    # Use existing directory
    read -p "Enter the directory of airunner: " airunner_dir
    cd $airunner_dir && pip install -e .
fi

cd ..

# Ask user if they want to clone the controlnet_aux repository or use existing directory
read -p "Do you want to clone the controlnet_aux repository? (y/n) " clone_controlnet_aux

if [[ $clone_controlnet_aux == "y" || $clone_controlnet_aux == "Y" ]]; then
    # Install controlnet_aux from fork
    if [ ! -d "controlnet_aux" ]; then
        git clone -b 96-add-local_files_only-flag https://github.com/w4ffl35/controlnet_aux.git
    fi
    cd  controlnet_aux && pip install -e .
else
    # Use existing directory
    read -p "Enter the directory of controlnet_aux: " controlnet_aux_dir
    cd $controlnet_aux_dir && pip install -e .
fi
