FROM ubuntu:22.04

RUN apt-get update && apt-get install -y python3-pip git python-is-python3 less
# All this stuff is needed to be able to render the airunner GUI (it already comes with Ubuntu-desktop usually!)
RUN apt-get update && apt-get install -y '^libxcb.*-dev' libgl1 libsm6 libxrender1 libxext6 libglib2.0-dev libgl1-mesa-dev libxkbcommon-dev libdbus-1-3 libx11-xcb-dev libglu1-mesa-dev libxrender-dev libxi-dev libxkbcommon-dev libxkbcommon-x11-dev
WORKDIR /root
# To patch https://github.com/Capsize-Games/airunner/issues/16
RUN pip install diffusers
RUN pip install transformers


# This could be automated further like:
# Clone airunner
# RUN git clone https://github.com/Capsize-Games/airunner.git
# # build (well, install dependencies, makes the image big, 9.7GB)
# RUN cd airunner && pip install -e .

# And then one can run the app
# cd /root/airunner/src/airunner && python main.py

# And then... when you click generate, you will download a lot of models that are pretty huge! About 9GB more? The image at this point is 15.2GB
# Note that I added my huggingface token before clicking generate, I guess it's mandatory, but I'm not 100% sure
# Note also that it's all running on CPU here (I think, judging by how slow it is)

# at this point I did
# docker commit airunner_container airunner_image_with_pip_install
# To save the docker image on my machine (15GB)
# So I could re-use it...
