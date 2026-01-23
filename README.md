# leetcode-env

A multi-language LeetCode workspace for offline development and testing, currently supporting C++, Python, and Rust.

## Requirements

- macOS (uses Homebrew for dependencies)
- [Homebrew](https://brew.sh)
- [just](https://github.com/casey/just) - task runner (`brew install just`)
- [pyenv](https://github.com/pyenv/pyenv) with virtualenv support (`brew install pyenv pyenv-virtualenv`)
- [direnv](https://direnv.net) (optional, for automatic environment activation) (`brew install direnv`)
- [Claude Code](https://claude.ai/code) (optional, for auto-generating tests)

Language-specific dependencies are installed automatically during setup:
- **C++**: cmake, GoogleTest
- **Python**: pytest
- **Rust**: cargo (via rustup)

## Quickstart

1. Clone the repository and install the task runner:

```bash
git clone <repo-url> leetcode
cd leetcode
brew install just
```

2. Run setup for your preferred language(s):

```bash
just setup cpp           # C++ only
just setup py            # Python only
just setup cpp py rs     # All languages
```

The setup will prompt you to select a default language for `just start`.

3. Start working on a problem:

```bash
just start 1             # Fetch problem #1 (Two Sum) in your default language
just start 1 -l cpp,py   # Fetch for multiple languages
```

4. Run tests:

```bash
just test                # Run all tests
just test 1              # Run tests for problem #1 only
```

You can also run tests from within a language directory (`cpp/`, `py/`, `rs/`) for language-specific commands.
