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
