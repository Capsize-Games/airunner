FROM ubuntu:22.04

# Set environment variables
ENV TZ=America/Denver
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PATH="/root/.local/bin:${PATH}"
ENV PYTHONPATH="/app"

# Install system dependencies
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone && \
    apt-get update && apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
    git wget curl software-properties-common \
    build-essential python3 python3-pip python3-dev \
    python3.10 python3.10-dev python3.10-distutils python3.10-tk \
    libgl1-mesa-dev libglib2.0-0 libsm6 libxrender1 libxext6 \
    libxcb-cursor0 libxcb-xinerama0 libportaudio2 \
    libssl-dev libffi-dev fonts-noto-color-emoji \
    espeak xclip upx patchelf ninja-build cmake \
    libjpeg-dev zlib1g-dev libpng-dev && \
    # Create a symbolic link for tcl8
    ln -s /usr/share/tcltk/tcl8.6 /usr/share/tcltk/tcl8 && \
    # Clean up APT cache
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Create and set the working directory
WORKDIR /app

# Install pip dependencies
RUN pip3 install --upgrade pip setuptools wheel

# Copy just the requirements first to leverage Docker caching
COPY setup.py .
COPY README.md .

# Install basic requirements
RUN pip3 install -e .

# Install GUI requirements
RUN pip3 install -e ".[gui]"

# Install dev requirements
RUN pip3 install -e ".[dev]"

# Copy the rest of the application
COPY . .

# Set environment variables for running AIRunner
ENV DEV_ENV=1
ENV AIRUNNER_ENVIRONMENT=dev
ENV DISPLAY=:0
ENV QT_X11_NO_MITSHM=1

# Expose port if needed for any web services
EXPOSE 8000

# Define an entrypoint script
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh
ENTRYPOINT ["docker-entrypoint.sh"]

# Default command
CMD ["python3", "-m", "airunner.main"]