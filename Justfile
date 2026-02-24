# Justfile for leetcode project

# Path to lc command
lc := "~/.pyenv/versions/leetcode/bin/lc"

# Detect language from invocation directory (before just changes to Justfile dir)
# This is set by the shell before just runs
invocation_dir := env('PWD', '')

start *args:
    {{lc}} start {{args}}

submit problem_number lang="":
    #!/usr/bin/env bash
    lang_arg=""
    if [[ -n "{{lang}}" ]]; then
        lang_arg="--lang {{lang}}"
    else
        dir_name="$(basename "{{invocation_dir}}")"
        if [[ "$dir_name" =~ ^(cpp|py|rs)$ ]]; then
            lang_arg="--lang $dir_name"
        fi
    fi
    {{lc}} submit {{problem_number}} $lang_arg

try problem_number lang="":
    #!/usr/bin/env bash
    lang_arg=""
    if [[ -n "{{lang}}" ]]; then
        lang_arg="--lang {{lang}}"
    else
        dir_name="$(basename "{{invocation_dir}}")"
        if [[ "$dir_name" =~ ^(cpp|py|rs)$ ]]; then
            lang_arg="--lang $dir_name"
        fi
    fi
    {{lc}} try {{problem_number}} $lang_arg

setup +langs:
    #!/usr/bin/env bash
    set -euo pipefail

    langs="{{langs}}"

    # Validate languages
    valid_langs="cpp py rs"
    for lang in $langs; do
        if ! echo "$valid_langs" | grep -qw "$lang"; then
            echo "Error: Invalid language '$lang'. Valid options: $valid_langs" >&2
            exit 1
        fi
    done

    has_lang() {
        echo "$langs" | grep -qw "$1"
    }

    # Helper to create language .envrc (non-destructive)
    create_lang_envrc() {
        local lang_dir="$1"
        local lang_slug="$2"
        local envrc_line="leetcode workspace use $lang_slug > /dev/null 2>&1"
        local envrc_path="$lang_dir/.envrc"

        if [ ! -f "$envrc_path" ]; then
            echo "$envrc_line" > "$envrc_path"
            echo "Created $envrc_path"
        elif ! grep -qF "$envrc_line" "$envrc_path"; then
            echo "$envrc_line" >> "$envrc_path"
            echo "Added workspace activation to $envrc_path"
        else
            echo "$envrc_path already configured"
        fi
        if command -v direnv &> /dev/null; then
            direnv allow "$envrc_path"
        fi
    }

    # Helper to create workspace if it doesn't exist
    create_workspace() {
        local lang_slug="$1"
        local lang_dir="$2"

        if ! leetcode workspace list 2>/dev/null | grep -q "^  $lang_slug$"; then
            echo "Creating workspace '$lang_slug'..."
            leetcode workspace create -w "$lang_dir" "$lang_slug"
        else
            echo "Workspace '$lang_slug' already exists"
        fi
    }

    # --- Shared setup ---

    # Ensure nodeenv is installed
    if ! command -v nodeenv &> /dev/null; then
        echo "nodeenv not found, installing via homebrew..."
        brew install nodeenv
    else
        echo "nodeenv is already installed"
    fi

    # Create node environment if it doesn't exist
    if [ ! -d .node ]; then
        echo "Creating node environment..."
        nodeenv .node
    else
        echo "Node environment already exists"
    fi

    # Install leetcode-cli in node environment
    echo "Installing leetcode-cli..."
    source .node/bin/activate
    npm install -g @night-slayer18/leetcode-cli

    # Ensure pyenv virtualenv 'leetcode' exists (needed for lc command)
    _pyenv_versions="$(pyenv versions --bare 2>/dev/null || true)"
    if ! echo "$_pyenv_versions" | grep -q '^leetcode$'; then
        echo "Creating pyenv virtualenv 'leetcode'..."
        pyenv virtualenv 3 leetcode
    else
        echo "pyenv virtualenv 'leetcode' already exists"
    fi

    # Create .python-version for auto-activation (non-destructive)
    if [ ! -f .python-version ]; then
        echo "leetcode" > .python-version
        echo "Created .python-version for auto-activation"
    elif [ "$(cat .python-version)" != "leetcode" ]; then
        echo 'Warning: .python-version exists with different content, skipping' >&2
    else
        echo '.python-version already configured'
    fi

    # Install base Python package (needed for lc command)
    echo "Installing lc command..."
    ~/.pyenv/versions/leetcode/bin/pip install -e 'py/'

    # --- C++ setup ---
    if has_lang cpp; then
        echo "=== Setting up C++ ==="

        # Ensure cmake is installed
        if ! command -v cmake &> /dev/null; then
            echo "cmake not found, installing via homebrew..."
            brew install cmake
        else
            echo "cmake is already installed"
        fi

        # Configure CMake for C++
        echo "Configuring CMake..."
        cmake -B cpp/build -S cpp

        # Create workspace and .envrc
        create_workspace cpp cpp
        create_lang_envrc cpp cpp
    fi

    # --- Python setup ---
    if has_lang py; then
        echo "=== Setting up Python ==="

        # Install pytest for Python development
        echo "Installing pytest..."
        ~/.pyenv/versions/leetcode/bin/pip install 'pytest>=7.0'

        # Create workspace and .envrc
        create_workspace py py
        create_lang_envrc py py
    fi

    # --- Rust setup ---
    if has_lang rs; then
        echo "=== Setting up Rust ==="

        # Ensure rust/cargo is installed
        if ! command -v cargo &> /dev/null; then
            echo "cargo not found, installing via rustup..."
            curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
            source "$HOME/.cargo/env"
        else
            echo "cargo is already installed"
        fi

        # Create workspace and .envrc
        create_workspace rs rs
        create_lang_envrc rs rs
    fi

    # --- Profiling tools setup ---
    # Install samply for profiling (C++/Rust) if any of those languages are selected
    if has_lang cpp || has_lang rs; then
        if ! command -v samply &>/dev/null; then
            echo "Installing samply for profiling..."
            cargo install samply
        else
            echo "samply is already installed"
        fi
    fi

    # --- Default language selection ---
    echo ""
    echo "Select default language for 'just start':"
    select default_lang in $langs; do
        if [ -n "$default_lang" ]; then
            break
        fi
    done

    # --- Create root .envrc ---
    echo "Creating .envrc..."
    envrc_content="source_env_if_exists .node/bin/activate"$'\n'"export LEETCODE_DEFAULT_LANG=$default_lang"

    # Check if .envrc exists and preserve any user additions
    if [ -f .envrc ]; then
        # Read existing content, filter out lines we manage
        existing=$(grep -v '^source_env_if_exists .node/bin/activate$' .envrc | \
                   grep -v '^export LEETCODE_DEFAULT_LANG=' || true)
        if [ -n "$existing" ]; then
            envrc_content="$envrc_content"$'\n'"$existing"
        fi
    fi

    envrc_file=.envrc
    echo "$envrc_content" > "$envrc_file"
    printf 'Created %s with LEETCODE_DEFAULT_LANG=%s\n' "$envrc_file" "$default_lang"

    if command -v direnv &> /dev/null; then
        direnv allow
    fi

    echo 'Setup complete!'
