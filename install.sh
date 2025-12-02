#!/bin/bash
# AI Runner Installation Script
# https://github.com/Capsize-Games/airunner
#
# Usage:
#   curl -sSL https://raw.githubusercontent.com/Capsize-Games/airunner/develop/install.sh | bash
#   OR
#   ./install.sh
#
# This script:
#   1. Checks system requirements (Python 3.13+, CUDA optional)
#   2. Creates a virtual environment
#   3. Installs AI Runner with all dependencies
#   4. Creates convenient launcher scripts

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
AIRUNNER_VERSION="5.0.0"
MIN_PYTHON_VERSION="3.13"
INSTALL_DIR="${AIRUNNER_INSTALL_DIR:-$HOME/.local/airunner}"
VENV_DIR="${INSTALL_DIR}/venv"
BIN_DIR="${HOME}/.local/bin"

echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                                                               ║"
echo "║     █████╗ ██╗    ██████╗ ██╗   ██╗███╗   ██╗███╗   ██╗███████╗██████╗  ║"
echo "║    ██╔══██╗██║    ██╔══██╗██║   ██║████╗  ██║████╗  ██║██╔════╝██╔══██╗ ║"
echo "║    ███████║██║    ██████╔╝██║   ██║██╔██╗ ██║██╔██╗ ██║█████╗  ██████╔╝ ║"
echo "║    ██╔══██║██║    ██╔══██╗██║   ██║██║╚██╗██║██║╚██╗██║██╔══╝  ██╔══██╗ ║"
echo "║    ██║  ██║██║    ██║  ██║╚██████╔╝██║ ╚████║██║ ╚████║███████╗██║  ██║ ║"
echo "║    ╚═╝  ╚═╝╚═╝    ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝ ║"
echo "║                                                               ║"
echo "║              Local AI Models Made Easy                        ║"
echo "║                                                               ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Compare version numbers
version_ge() {
    # Returns 0 if $1 >= $2
    printf '%s\n%s\n' "$2" "$1" | sort -V -C
}

# Get Python version
get_python_version() {
    "$1" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null
}

# Find suitable Python
find_python() {
    local python_cmd=""
    
    # Try python3.13 first, then python3, then python
    for cmd in python3.13 python3 python; do
        if command_exists "$cmd"; then
            local version=$(get_python_version "$cmd")
            if [ -n "$version" ] && version_ge "$version" "$MIN_PYTHON_VERSION"; then
                python_cmd="$cmd"
                break
            fi
        fi
    done
    
    echo "$python_cmd"
}

# Check system requirements
check_requirements() {
    log_info "Checking system requirements..."
    
    # Check Python
    PYTHON_CMD=$(find_python)
    if [ -z "$PYTHON_CMD" ]; then
        log_error "Python ${MIN_PYTHON_VERSION}+ is required but not found."
        echo ""
        echo "Please install Python ${MIN_PYTHON_VERSION} or later:"
        echo "  Ubuntu/Debian: sudo apt install python3.13 python3.13-venv python3.13-dev"
        echo "  Fedora: sudo dnf install python3.13"
        echo "  Arch: sudo pacman -S python"
        echo "  Or use pyenv: https://github.com/pyenv/pyenv"
        exit 1
    fi
    
    local python_version=$(get_python_version "$PYTHON_CMD")
    log_success "Found Python $python_version ($PYTHON_CMD)"
    
    # Check for venv module
    if ! "$PYTHON_CMD" -c "import venv" 2>/dev/null; then
        log_error "Python venv module not found."
        echo "Please install it:"
        echo "  Ubuntu/Debian: sudo apt install python3.13-venv"
        exit 1
    fi
    log_success "Python venv module available"
    
    # Check for pip
    if ! "$PYTHON_CMD" -m pip --version >/dev/null 2>&1; then
        log_error "pip not found."
        echo "Please install it:"
        echo "  Ubuntu/Debian: sudo apt install python3-pip"
        exit 1
    fi
    log_success "pip available"
    
    # Check for CUDA (optional)
    if command_exists nvidia-smi; then
        local cuda_version=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader 2>/dev/null | head -1)
        if [ -n "$cuda_version" ]; then
            log_success "NVIDIA GPU detected (driver: $cuda_version)"
            HAS_CUDA=true
        fi
    else
        log_warning "No NVIDIA GPU detected. AI Runner will use CPU (slower)."
        HAS_CUDA=false
    fi
    
    # Check disk space (need at least 20GB for models)
    local available_space=$(df -BG "$HOME" | awk 'NR==2 {print $4}' | sed 's/G//')
    if [ "$available_space" -lt 20 ]; then
        log_warning "Low disk space: ${available_space}GB available. AI models require 10-50GB."
    else
        log_success "Disk space: ${available_space}GB available"
    fi
    
    # Check RAM (recommend 16GB+)
    local total_ram=$(free -g | awk '/^Mem:/{print $2}')
    if [ "$total_ram" -lt 8 ]; then
        log_warning "Low RAM: ${total_ram}GB. 16GB+ recommended for AI workloads."
    else
        log_success "RAM: ${total_ram}GB"
    fi
    
    echo ""
}

# Create virtual environment
create_venv() {
    log_info "Creating virtual environment at ${VENV_DIR}..."
    
    # Create install directory
    mkdir -p "$INSTALL_DIR"
    
    # Create venv if it doesn't exist
    if [ ! -d "$VENV_DIR" ]; then
        "$PYTHON_CMD" -m venv "$VENV_DIR"
        log_success "Virtual environment created"
    else
        log_info "Virtual environment already exists, reusing..."
    fi
    
    # Activate venv
    source "$VENV_DIR/bin/activate"
    
    # Upgrade pip
    log_info "Upgrading pip..."
    pip install --upgrade pip setuptools wheel >/dev/null 2>&1
    log_success "pip upgraded"
}

# Install PyTorch
install_pytorch() {
    log_info "Installing PyTorch..."
    
    if [ "$HAS_CUDA" = true ]; then
        log_info "Installing PyTorch with CUDA support..."
        pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
    else
        log_info "Installing PyTorch (CPU only)..."
        pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
    fi
    
    log_success "PyTorch installed"
}

# Install AI Runner
install_airunner() {
    log_info "Installing AI Runner..."
    
    # Install with all extras
    pip install "airunner[all]"
    
    log_success "AI Runner installed"
}

# Create launcher scripts
create_launchers() {
    log_info "Creating launcher scripts..."
    
    mkdir -p "$BIN_DIR"
    
    # Main launcher
    cat > "$BIN_DIR/airunner" << EOF
#!/bin/bash
# AI Runner Launcher
source "${VENV_DIR}/bin/activate"
exec python -m airunner.launcher "\$@"
EOF
    chmod +x "$BIN_DIR/airunner"
    
    # Headless launcher
    cat > "$BIN_DIR/airunner-headless" << EOF
#!/bin/bash
# AI Runner Headless Mode
source "${VENV_DIR}/bin/activate"
exec python -m airunner.bin.airunner_headless "\$@"
EOF
    chmod +x "$BIN_DIR/airunner-headless"
    
    log_success "Launcher scripts created in $BIN_DIR"
    
    # Check if BIN_DIR is in PATH
    if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
        log_warning "$BIN_DIR is not in your PATH"
        echo ""
        echo "Add this line to your ~/.bashrc or ~/.zshrc:"
        echo -e "  ${YELLOW}export PATH=\"\$HOME/.local/bin:\$PATH\"${NC}"
        echo ""
        echo "Then reload your shell:"
        echo -e "  ${YELLOW}source ~/.bashrc${NC}"
        ADD_TO_PATH=true
    fi
}

# Print success message
print_success() {
    echo ""
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                  Installation Complete!                       ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "AI Runner has been installed to: ${INSTALL_DIR}"
    echo ""
    echo -e "${BLUE}Next steps:${NC}"
    echo ""
    
    if [ "$ADD_TO_PATH" = true ]; then
        echo "1. Add ~/.local/bin to your PATH (see above)"
        echo ""
        echo "2. Launch AI Runner:"
        echo -e "   ${YELLOW}$BIN_DIR/airunner${NC}"
        echo ""
        echo "3. Download models from Tools → Download Models menu"
    else
        echo "1. Launch AI Runner:"
        echo -e "   ${YELLOW}airunner${NC}"
        echo ""
        echo "2. Download models from Tools → Download Models menu"
    fi
    
    echo ""
    echo -e "${BLUE}Documentation:${NC} https://github.com/Capsize-Games/airunner/wiki"
    echo -e "${BLUE}Issues:${NC} https://github.com/Capsize-Games/airunner/issues"
    echo ""
}

# Uninstall function
uninstall() {
    log_info "Uninstalling AI Runner..."
    
    # Remove install directory
    if [ -d "$INSTALL_DIR" ]; then
        rm -rf "$INSTALL_DIR"
        log_success "Removed $INSTALL_DIR"
    fi
    
    # Remove launcher scripts
    for script in airunner airunner-headless; do
        if [ -f "$BIN_DIR/$script" ]; then
            rm "$BIN_DIR/$script"
            log_success "Removed $BIN_DIR/$script"
        fi
    done
    
    echo ""
    log_success "AI Runner has been uninstalled."
    echo ""
    echo "Note: Model files in ~/.local/share/airunner were NOT removed."
    echo "To remove them: rm -rf ~/.local/share/airunner"
}

# Main installation
main() {
    # Check for uninstall flag
    if [ "$1" = "--uninstall" ] || [ "$1" = "-u" ]; then
        uninstall
        exit 0
    fi
    
    # Check for help flag
    if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
        echo "AI Runner Installation Script"
        echo ""
        echo "Usage:"
        echo "  ./install.sh           Install AI Runner"
        echo "  ./install.sh --uninstall  Uninstall AI Runner"
        echo ""
        echo "Environment variables:"
        echo "  AIRUNNER_INSTALL_DIR   Installation directory (default: ~/.local/airunner)"
        exit 0
    fi
    
    check_requirements
    create_venv
    install_pytorch
    install_airunner
    create_launchers
    print_success
}

# Run main function
main "$@"
