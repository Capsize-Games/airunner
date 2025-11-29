# AI Runner Flatpak Packaging

This directory contains files for building AI Runner as a Flatpak package.

## Prerequisites

Install Flatpak and flatpak-builder:

```bash
# Ubuntu/Debian
sudo apt install flatpak flatpak-builder

# Fedora
sudo dnf install flatpak flatpak-builder

# Arch
sudo pacman -S flatpak flatpak-builder
```

Add the Flathub repository:

```bash
flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
```

Install the required runtime and SDK:

```bash
flatpak install flathub org.freedesktop.Platform//24.08
flatpak install flathub org.freedesktop.Sdk//24.08
flatpak install flathub org.freedesktop.Sdk.Extension.llvm18//24.08
```

## Building

### Local Build (for testing)

```bash
cd /path/to/airunner/flatpak

# Build the Flatpak
flatpak-builder --force-clean build-dir com.capsizegames.AIRunner.yml

# Install locally for testing
flatpak-builder --user --install --force-clean build-dir com.capsizegames.AIRunner.yml

# Run the installed Flatpak
flatpak run com.capsizegames.AIRunner
```

### Build for Distribution

```bash
# Create a repository
flatpak-builder --repo=repo --force-clean build-dir com.capsizegames.AIRunner.yml

# Create a bundle file for distribution
flatpak build-bundle repo airunner.flatpak com.capsizegames.AIRunner
```

## NVIDIA GPU Support

For CUDA/GPU acceleration, users need:

1. **NVIDIA drivers** installed on the host system
2. **Flatpak NVIDIA runtime**:
   ```bash
   flatpak install flathub org.freedesktop.Platform.GL.nvidia-550-67
   ```
   (Replace version number with your driver version)

## Icons

Place application icons in the `icons/` directory:
- `airunner-128.png` (128x128)
- `airunner-256.png` (256x256)
- `airunner-512.png` (512x512)

You can generate these from an SVG or larger PNG using ImageMagick:

```bash
convert source-icon.png -resize 128x128 icons/airunner-128.png
convert source-icon.png -resize 256x256 icons/airunner-256.png
convert source-icon.png -resize 512x512 icons/airunner-512.png
```

## Publishing to Flathub

1. Fork the [Flathub repository](https://github.com/flathub/flathub)
2. Create a new repository for your app
3. Submit a PR with your manifest
4. Follow the [Flathub submission guidelines](https://github.com/flathub/flathub/wiki/App-Submission)

## Files

- `com.capsizegames.AIRunner.yml` - Flatpak manifest (build recipe)
- `com.capsizegames.AIRunner.desktop` - Desktop entry file
- `com.capsizegames.AIRunner.metainfo.xml` - AppStream metadata
- `icons/` - Application icons

## Troubleshooting

### Build fails with Python errors
Ensure the Python version in the manifest matches what AI Runner requires (3.13+).

### GPU not detected
Check that the NVIDIA Flatpak runtime matches your driver version:
```bash
flatpak list | grep nvidia
```

### Audio not working
Ensure PulseAudio is running on the host system.

### Permission denied errors
The Flatpak is sandboxed. Check `finish-args` in the manifest if you need additional permissions.
