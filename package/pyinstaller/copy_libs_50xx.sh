#!/bin/bash
# Script to copy necessary CUDA libraries into the torch directory

CUDA_LIB_DIR="/usr/local/cuda/lib64"
TORCH_LIB_DIR="/home/appuser/.local/share/airunner/python/lib/python3.10/site-packages/torch/lib"
NVIDIA_DIR="/home/appuser/.local/share/airunner/python/lib/python3.10/site-packages/nvidia"

echo "Creating directories if they don't exist..."
mkdir -p "$TORCH_LIB_DIR"

echo "Copying CUDA libraries to PyTorch lib directory..."

# First, ensure we have libnvJitLink.so.12
if [ -f "$CUDA_LIB_DIR/libnvJitLink.so.12" ]; then
    echo "Copying libnvJitLink.so.12..."
    cp -f "$CUDA_LIB_DIR/libnvJitLink.so.12" "$TORCH_LIB_DIR/"
else
    echo "WARNING: libnvJitLink.so.12 not found in $CUDA_LIB_DIR!"
    # Search for it in alternative locations
    for alt_path in $(find /usr -name "libnvJitLink.so.12" 2>/dev/null); do
        echo "Found alternative libnvJitLink.so.12 at $alt_path, copying..."
        cp -f "$alt_path" "$TORCH_LIB_DIR/"
        break
    done
fi

# Copy other essential CUDA libraries
for lib in libcuda.so libcudart.so.12 libnvToolsExt.so.1 libcufft.so.11 libcurand.so.11 libcusparse.so.12 libcusolver.so.12; do
    if [ -f "$CUDA_LIB_DIR/$lib" ]; then
        echo "Copying $lib..."
        cp -f "$CUDA_LIB_DIR/$lib" "$TORCH_LIB_DIR/"
    else
        echo "WARNING: $lib not found in $CUDA_LIB_DIR"
    fi
done

# Print versions of PyTorch's CUDA libraries for debugging
echo "Current PyTorch CUDA library versions:"
find "$TORCH_LIB_DIR" -name "*.so*" | xargs ls -la

# Copy CUDA headers if needed for compilation
echo "Copying CUDA JIT headers..."
CUDA_INCLUDE_DIR="/usr/local/cuda/include"
TORCH_INCLUDE_DIR="/home/appuser/.local/share/airunner/python/lib/python3.10/site-packages/torch/include"
mkdir -p "$TORCH_INCLUDE_DIR/cuda"
cp -f "$CUDA_INCLUDE_DIR/cuda_runtime.h" "$TORCH_INCLUDE_DIR/cuda/" 2>/dev/null || echo "Warning: Could not copy cuda_runtime.h"
cp -f "$CUDA_INCLUDE_DIR/device_functions.h" "$TORCH_INCLUDE_DIR/cuda/" 2>/dev/null || echo "Warning: Could not copy device_functions.h"

echo "CUDA library preparation completed."