# Justfile for leetcode project

setup:
    #!/usr/bin/env bash
    set -euo pipefail

    # Ensure cmake is installed
    if ! command -v cmake &> /dev/null; then
        echo "cmake not found, installing via homebrew..."
        brew install cmake
    else
        echo "cmake is already installed"
    fi

    # Ensure rust/cargo is installed
    if ! command -v cargo &> /dev/null; then
        echo "cargo not found, installing via rustup..."
        curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
        source "$HOME/.cargo/env"
    else
        echo "cargo is already installed"
    fi

    # Ensure nodeenv is installed
    if ! command -v nodeenv &> /dev/null; then
        echo "nodeenv not found, installing via homebrew..."
        brew install nodeenv
    else
        echo "nodeenv is already installed"
    fi

    # Create node environment if it doesn't exist
    if [ ! -d ".node" ]; then
        echo "Creating node environment..."
        nodeenv .node
    else
        echo "Node environment already exists"
    fi

    # Install leetcode-cli in node environment
    echo "Installing leetcode-cli..."
    source .node/bin/activate
    npm install -g @night-slayer18/leetcode-cli

    # Ensure pyenv virtualenv 'leetcode' exists
    if ! pyenv versions --bare | grep -q '^leetcode$'; then
        echo "Creating pyenv virtualenv 'leetcode'..."
        pyenv virtualenv 3 leetcode
    else
        echo "pyenv virtualenv 'leetcode' already exists"
    fi

    # Create .python-version for auto-activation
    echo "leetcode" > .python-version
    echo "Created .python-version for auto-activation"

    # Install Python dev dependencies
    echo "Installing Python dependencies..."
    pip install -e py/[dev]

    # Configure CMake for C++
    echo "Configuring CMake..."
    cmake -B cpp/build -S cpp

    echo "Setup complete!"
