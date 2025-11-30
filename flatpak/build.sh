#!/bin/bash
# Build script for AI Runner Flatpak
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}"
echo "╔═══════════════════════════════════════════════════════════════════════════════╗"
echo "║                         AI Runner Flatpak Builder                             ║"
echo "╚═══════════════════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check for flatpak-builder
if ! command -v flatpak-builder &> /dev/null; then
    echo -e "${RED}Error: flatpak-builder is not installed${NC}"
    echo "Install it with:"
    echo "  Ubuntu/Debian: sudo apt install flatpak-builder"
    echo "  Fedora: sudo dnf install flatpak-builder"
    echo "  Arch: sudo pacman -S flatpak-builder"
    exit 1
fi

# Check for required runtimes
echo -e "${YELLOW}Checking for required Flatpak runtimes...${NC}"

if ! flatpak info org.freedesktop.Platform//24.08 &> /dev/null; then
    echo -e "${YELLOW}Installing org.freedesktop.Platform//24.08...${NC}"
    flatpak install -y flathub org.freedesktop.Platform//24.08
fi

if ! flatpak info org.freedesktop.Sdk//24.08 &> /dev/null; then
    echo -e "${YELLOW}Installing org.freedesktop.Sdk//24.08...${NC}"
    flatpak install -y flathub org.freedesktop.Sdk//24.08
fi

cd "$SCRIPT_DIR"

# Parse arguments
ACTION="${1:-build}"
case "$ACTION" in
    build)
        echo -e "${GREEN}Building AI Runner Flatpak...${NC}"
        # --disable-download=false allows network access during build for pip installs
        flatpak-builder --force-clean --disable-download=false build-dir com.capsizegames.AIRunner.yml
        echo -e "${GREEN}Build complete!${NC}"
        echo ""
        echo "To install locally for testing:"
        echo "  $0 install"
        ;;
    
    install)
        echo -e "${GREEN}Building and installing AI Runner Flatpak locally...${NC}"
        flatpak-builder --user --install --force-clean --disable-download=false build-dir com.capsizegames.AIRunner.yml
        echo -e "${GREEN}Installation complete!${NC}"
        echo ""
        echo "Run with: flatpak run com.capsizegames.AIRunner"
        ;;
    
    bundle)
        echo -e "${GREEN}Building AI Runner Flatpak bundle for distribution...${NC}"
        flatpak-builder --repo=repo --force-clean --disable-download=false build-dir com.capsizegames.AIRunner.yml
        flatpak build-bundle repo airunner.flatpak com.capsizegames.AIRunner
        echo -e "${GREEN}Bundle created: airunner.flatpak${NC}"
        echo ""
        echo "Users can install with: flatpak install airunner.flatpak"
        ;;
    
    run)
        echo -e "${GREEN}Running AI Runner Flatpak...${NC}"
        flatpak run com.capsizegames.AIRunner
        ;;
    
    uninstall)
        echo -e "${YELLOW}Uninstalling AI Runner Flatpak...${NC}"
        flatpak uninstall com.capsizegames.AIRunner
        echo -e "${GREEN}Uninstalled.${NC}"
        ;;
    
    clean)
        echo -e "${YELLOW}Cleaning build directories...${NC}"
        rm -rf build-dir repo .flatpak-builder
        rm -f airunner.flatpak
        echo -e "${GREEN}Cleaned.${NC}"
        ;;
    
    *)
        echo "Usage: $0 {build|install|bundle|run|uninstall|clean}"
        echo ""
        echo "Commands:"
        echo "  build     - Build the Flatpak (default)"
        echo "  install   - Build and install locally for testing"
        echo "  bundle    - Create a .flatpak bundle file for distribution"
        echo "  run       - Run the installed Flatpak"
        echo "  uninstall - Remove the installed Flatpak"
        echo "  clean     - Remove build artifacts"
        exit 1
        ;;
esac
