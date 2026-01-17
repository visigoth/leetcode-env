# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Multi-language LeetCode solutions repository supporting C++, Python, and Rust. Uses `just` as the task runner.

## Commands

### Initial Setup
```bash
just setup  # Install all dependencies (cmake, cargo, node, pyenv, leetcode-cli)
```

### Starting a New Problem
```bash
just start <problem_number>                    # Start problem (C++ by default)
just start <problem_number> -l cpp,py,rs       # Start for multiple languages
```

This fetches the problem using leetcode-cli and creates wrapper files with auto-generated tests.

### Building and Testing

**C++ (from project root or cpp/)**
```bash
just test           # Run all tests
just test 1         # Run tests for problem 1 (matches *P1*)
just build          # Build only
just debug          # Debug with lldb
just debug 1        # Debug specific problem
```

**Python (from project root or py/)**
```bash
just test           # Run all tests
just test 1         # Run tests for problem 1 (matches p1)
just build          # Install package in editable mode
```

**Rust (from project root or rs/)**
```bash
just test           # Run all tests
just test 1         # Run tests for problem 1 (matches p1)
just build          # Build
```

## Code Architecture

### C++
- **Solution files**: `cpp/<Difficulty>/<Category>/<number>.<slug>.cpp` (e.g., `cpp/Easy/Array/1.two-sum.cpp`)
- **Test wrappers**: `cpp/<number>.cpp` - wrap solutions with namespace and GoogleTest tests
- The wrapper includes the solution via `#include` and wraps the `Solution` class in a namespace (`leetcode::p<N>`)
- Uses C++20, GoogleTest, and AddressSanitizer in debug builds
- CMake auto-discovers `cpp/[0-9]*.cpp` files as test sources

### Python
- Solutions go in `py/leetcode/` as `p<number>.py`
- Tests can be in the solution files or `py/tests/`
- pytest configured to find `test_*` functions in both `p*.py` and `test_*.py` files

### Rust
- Solutions as modules: `rs/src/p<number>.rs`
- Export in `rs/src/lib.rs`: `pub mod p<number>;`

## Issue Tracking

This project uses `bd` (beads) for issue tracking. See AGENTS.md for workflow.
