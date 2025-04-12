ARG BASE_IMAGE=ghcr.io/capsize-games/airunner/airunner:base
FROM ${BASE_IMAGE}

USER root
# Copy the pip configuration to ensure consistent settings
COPY ./package/pip.conf /etc/pip.conf
RUN chown -R appuser:appuser /etc/pip.conf && \
    chmod 644 /etc/pip.conf

# Add ~/.local/bin to PATH
ENV PATH="/home/appuser/.local/bin:$PATH"
ENV PYTHONUSERBASE=/home/appuser/.local/share/airunner/python
ENV PYTHONPATH=/home/appuser/.local/share/airunner/python/local/lib/python3.10/dist-packages:$PYTHONPATH
ENV PIP_CACHE_DIR=/home/appuser/.local/share/airunner/.cache/pip

# Make sure required directories exist with correct permissions
RUN mkdir -p /home/appuser/.local/share/airunner/python \
    && mkdir -p /home/appuser/.local/share/airunner/.cache/pip \
    && mkdir -p /home/appuser/.local/bin \
    && chown -R appuser:appuser /home/appuser/.local

USER appuser
WORKDIR /app

# Install Python dependencies
COPY --chown=appuser:appuser ./package/install_python_packages.sh /app/package/
RUN bash /app/package/install_python_packages.sh

# Install PyInstaller and related dependencies
RUN pip install --no-warn-script-location 'PyInstaller==6.12.0' \
    && pip install --no-warn-script-location pytest pytest-qt coverage pytest-cov

# Copy the PyInstaller spec file and related build scripts
COPY --chown=appuser:appuser ./package/pyinstaller /app/package/pyinstaller/

# Verify installation
RUN python3 -c "import torch; print('PyTorch version:', torch.__version__)" \
    && python3 -c "import airunner; print('airunner version:', airunner.__version__)"

CMD ["/bin/bash"]