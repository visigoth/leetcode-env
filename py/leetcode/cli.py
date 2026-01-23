"""CLI wrapper for leetcode commands."""

import os
import subprocess
import sys
from pathlib import Path

import click


def get_repo_root() -> Path:
    """Get the root directory of the leetcode repository."""
    # Walk up from current directory to find the repo root (has cpp/, py/, rs/)
    current = Path.cwd()
    while current != current.parent:
        if (current / "cpp").is_dir() and (current / "py").is_dir():
            return current
        current = current.parent
    # Fallback: assume we're somewhere in the repo
    return Path.cwd()


def parse_leetcode_output(output: str) -> Path | None:
    """Parse the output of `leetcode pick` to extract the created file path."""
    for line in output.splitlines():
        if line.startswith("Path:"):
            path_str = line[5:].strip()
            return Path(path_str)
    return None


def cleanup_whitespace(file_path: Path) -> None:
    """Clean up whitespace in a file.

    - Remove trailing whitespace from lines
    - Collapse multiple consecutive blank lines into one
    - Ensure single newline at end of file
    """
    content = file_path.read_text()

    # Remove trailing whitespace from each line
    lines = [line.rstrip() for line in content.splitlines()]

    # Collapse multiple consecutive blank lines into one
    cleaned_lines = []
    prev_blank = False
    for line in lines:
        is_blank = line == ""
        if is_blank and prev_blank:
            continue
        cleaned_lines.append(line)
        prev_blank = is_blank

    # Join and ensure single trailing newline
    cleaned = "\n".join(cleaned_lines).rstrip() + "\n"

    file_path.write_text(cleaned)


def strip_markdown_fences(code: str) -> str:
    """Remove markdown code fences from generated code."""
    lines = code.strip().splitlines()
    result = []
    in_fence = False

    for line in lines:
        stripped = line.strip()
        # Detect opening fence (```python, ```cpp, ```rust, ```, etc.)
        if stripped.startswith("```"):
            if not in_fence:
                in_fence = True
                continue  # Skip opening fence
            else:
                in_fence = False
                continue  # Skip closing fence
        result.append(line)

    return "\n".join(result).strip()


def extract_problem_description(cpp_file: Path) -> str:
    """Extract the problem description comment block from a leetcode cpp file."""
    content = cpp_file.read_text()
    # Find the comment block at the start
    if content.startswith("/*"):
        end_idx = content.find("*/")
        if end_idx != -1:
            return content[: end_idx + 2]
    return ""


def extract_problem_description_py(py_file: Path) -> str:
    """Extract the problem description docstring from a leetcode Python file."""
    content = py_file.read_text()
    # Find the docstring at the start
    if content.startswith('"""'):
        end_idx = content.find('"""', 3)
        if end_idx != -1:
            return content[: end_idx + 3]
    return ""


def extract_problem_description_rs(rs_file: Path) -> str:
    """Extract the problem description comment block from a leetcode Rust file."""
    content = rs_file.read_text()
    # Handle /* */ block comments (same format as C++)
    if content.startswith("/*"):
        end_idx = content.find("*/")
        if end_idx != -1:
            return content[: end_idx + 2]
    # Handle // line comments
    lines = content.splitlines()
    desc_lines = []
    for line in lines:
        if line.startswith("//"):
            desc_lines.append(line)
        elif line.strip() == "":
            desc_lines.append(line)
        else:
            break
    return "\n".join(desc_lines)


def generate_cpp_tests_with_claude(problem_desc: str, problem_number: int) -> str:
    """Use claude CLI to generate GoogleTest tests from problem description."""
    prompt = f"""Given this C++ LeetCode problem, generate GoogleTest test cases based on the examples.

{problem_desc}

Requirements:
- Output ONLY the TEST() macros, no explanation or other text
- Do NOT include markdown code fences
- Use test names like Example1, Example2, etc.
- The test suite name should be P{problem_number}
- Create a Solution instance and call the appropriate method
- Use EXPECT_EQ for assertions
- Include all examples from the problem description
"""

    try:
        result = subprocess.run(
            ["claude", "-p", prompt],
            capture_output=True,
            text=True,
            check=True,
        )
        return strip_markdown_fences(result.stdout)
    except subprocess.CalledProcessError as e:
        click.echo(f"Error running claude: {e.stderr}", err=True)
        return ""
    except FileNotFoundError:
        click.echo("Error: claude CLI not found. Please install it first.", err=True)
        return ""


def generate_py_tests_with_claude(problem_desc: str, problem_number: int) -> str:
    """Use claude CLI to generate pytest tests from problem description."""
    prompt = f"""Given this Python LeetCode problem, generate pytest test cases based on the examples.

{problem_desc}

Requirements:
- Output ONLY the test functions, no explanation or other text
- Do NOT include markdown code fences
- Use function names like test_example1, test_example2, etc.
- Create a Solution instance and call the appropriate method
- Use assert statements for assertions
- Include all examples from the problem description
- Do NOT include any import statements - those will be added separately
"""

    try:
        result = subprocess.run(
            ["claude", "-p", prompt],
            capture_output=True,
            text=True,
            check=True,
        )
        return strip_markdown_fences(result.stdout)
    except subprocess.CalledProcessError as e:
        click.echo(f"Error running claude: {e.stderr}", err=True)
        return ""
    except FileNotFoundError:
        click.echo("Error: claude CLI not found. Please install it first.", err=True)
        return ""


def generate_rs_tests_with_claude(problem_desc: str, problem_number: int) -> str:
    """Use claude CLI to generate Rust tests from problem description."""
    prompt = f"""Given this Rust LeetCode problem, generate Rust test cases based on the examples.

{problem_desc}

Requirements:
- Output ONLY the test functions with #[test] attribute, no explanation or other text
- Do NOT include markdown code fences
- Use function names like test_example1, test_example2, etc.
- Create a Solution instance and call the appropriate method
- Use assert_eq! macro for assertions
- Include all examples from the problem description
- Do NOT include mod tests or cfg(test) - those will be added separately
"""

    try:
        result = subprocess.run(
            ["claude", "-p", prompt],
            capture_output=True,
            text=True,
            check=True,
        )
        return strip_markdown_fences(result.stdout)
    except subprocess.CalledProcessError as e:
        click.echo(f"Error running claude: {e.stderr}", err=True)
        return ""
    except FileNotFoundError:
        click.echo("Error: claude CLI not found. Please install it first.", err=True)
        return ""


def create_cpp_wrapper(
    repo_root: Path, problem_number: int, leetcode_file: Path, tests: str
) -> Path:
    """Create the C++ wrapper file with namespace and tests."""
    # Calculate relative path from cpp/ to the leetcode file
    cpp_dir = repo_root / "cpp"
    relative_path = leetcode_file.relative_to(cpp_dir)

    wrapper_content = f"""namespace leetcode::p{problem_number} {{ class Solution; }}
#define Solution leetcode::p{problem_number}::Solution

#include "{relative_path}"

#include <gtest/gtest.h>

namespace leetcode::p{problem_number} {{

{tests}

}} // namespace leetcode::p{problem_number}
"""

    wrapper_path = cpp_dir / f"{problem_number}.cpp"
    wrapper_path.write_text(wrapper_content)
    return wrapper_path


def create_py_wrapper(
    repo_root: Path, problem_number: int, leetcode_file: Path, tests: str
) -> Path:
    """Create the Python test wrapper file."""
    py_dir = repo_root / "py"
    relative_path = leetcode_file.relative_to(py_dir)

    wrapper_content = f'''"""Tests for problem {problem_number}."""

import importlib.util
from pathlib import Path

# Load the solution module dynamically (handles filenames like "1.two-sum.py")
_solution_path = Path(__file__).parent.parent / "{relative_path}"
_spec = importlib.util.spec_from_file_location("solution", _solution_path)
_solution_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_solution_module)
Solution = _solution_module.Solution


{tests}
'''

    # Create tests directory if it doesn't exist
    tests_dir = py_dir / "tests"
    tests_dir.mkdir(exist_ok=True)

    # Create __init__.py if it doesn't exist
    init_file = tests_dir / "__init__.py"
    if not init_file.exists():
        init_file.write_text("")

    wrapper_path = tests_dir / f"test_{problem_number}.py"
    wrapper_path.write_text(wrapper_content)
    return wrapper_path


def create_rs_module(
    repo_root: Path, problem_number: int, leetcode_file: Path, tests: str
) -> Path:
    """Create the Rust module file with embedded tests."""
    rs_dir = repo_root / "rs"
    src_dir = rs_dir / "src"

    # Read the solution file content
    solution_content = leetcode_file.read_text()

    # Create module with solution and tests
    module_content = f'''{solution_content}

#[cfg(test)]
mod tests {{
    use super::*;

{tests}
}}
'''

    module_path = src_dir / f"p{problem_number}.rs"
    module_path.write_text(module_content)

    # Update lib.rs to include the new module
    lib_path = src_dir / "lib.rs"
    lib_content = lib_path.read_text() if lib_path.exists() else ""

    module_decl = f"pub mod p{problem_number};"
    if module_decl not in lib_content:
        if lib_content and not lib_content.endswith("\n"):
            lib_content += "\n"
        lib_content += f"{module_decl}\n"
        lib_path.write_text(lib_content)

    return module_path


@click.group()
def cli():
    """LeetCode CLI wrapper with additional tooling."""
    pass


@cli.command()
@click.argument("problem_number", type=int)
@click.option(
    "-l",
    "--lang",
    default=lambda: os.environ.get("LEETCODE_DEFAULT_LANG", "cpp"),
    help="Comma-separated languages: cpp,py,rs",
)
def start(problem_number: int, lang: str):
    """Start working on a leetcode problem.

    Fetches the problem for specified languages and sets up wrapper files.
    """
    repo_root = get_repo_root()
    languages = [l.strip() for l in lang.split(",")]
    had_error = False

    for language in languages:
        click.echo(f"Setting up {language} for problem {problem_number}...")

        # Switch workspace and pick the problem, capturing output
        try:
            result = subprocess.run(
                f"leetcode workspace use {language} && leetcode pick {problem_number}",
                shell=True,
                check=True,
                capture_output=True,
                text=True,
            )
            # Print the output so user sees it
            if result.stdout:
                click.echo(result.stdout)
        except subprocess.CalledProcessError as e:
            click.echo(f"Error setting up {language}: {e}", err=True)
            if e.stderr:
                click.echo(e.stderr, err=True)
            had_error = True
            continue

        # For C++, create the wrapper file
        if language == "cpp":
            click.echo("Creating C++ wrapper file...")

            # Parse the file path from leetcode output
            leetcode_file = parse_leetcode_output(result.stdout)
            if not leetcode_file or not leetcode_file.exists():
                click.echo(
                    f"Error: Could not find leetcode file for problem {problem_number}",
                    err=True,
                )
                click.echo(f"Parsed path: {leetcode_file}", err=True)
                had_error = True
                continue

            click.echo(f"Found: {leetcode_file.relative_to(repo_root)}")

            # Clean up whitespace in the leetcode-generated file
            cleanup_whitespace(leetcode_file)

            # Extract problem description
            problem_desc = extract_problem_description(leetcode_file)
            if not problem_desc:
                click.echo("Warning: Could not extract problem description", err=True)

            # Generate tests with Claude
            click.echo("Generating tests with Claude...")
            tests = generate_cpp_tests_with_claude(problem_desc, problem_number)

            if not tests:
                tests = f"""// TODO: Add tests
TEST(P{problem_number}, Example1) {{
    Solution s;
    // EXPECT_EQ(s.method(...), expected);
}}"""

            # Create wrapper file
            wrapper_path = create_cpp_wrapper(
                repo_root, problem_number, leetcode_file, tests
            )
            click.echo(f"Created: {wrapper_path.relative_to(repo_root)}")

        # For Python, create the test wrapper file
        elif language == "py":
            click.echo("Creating Python test file...")

            # Parse the file path from leetcode output
            leetcode_file = parse_leetcode_output(result.stdout)
            if not leetcode_file or not leetcode_file.exists():
                click.echo(
                    f"Error: Could not find leetcode file for problem {problem_number}",
                    err=True,
                )
                click.echo(f"Parsed path: {leetcode_file}", err=True)
                had_error = True
                continue

            click.echo(f"Found: {leetcode_file.relative_to(repo_root)}")

            # Clean up whitespace in the leetcode-generated file
            cleanup_whitespace(leetcode_file)

            # Extract problem description
            problem_desc = extract_problem_description_py(leetcode_file)
            if not problem_desc:
                click.echo("Warning: Could not extract problem description", err=True)

            # Generate tests with Claude
            click.echo("Generating tests with Claude...")
            tests = generate_py_tests_with_claude(problem_desc, problem_number)

            if not tests:
                tests = f"""# TODO: Add tests
def test_example1():
    s = Solution()
    # assert s.method(...) == expected
"""

            # Create wrapper file
            wrapper_path = create_py_wrapper(
                repo_root, problem_number, leetcode_file, tests
            )
            click.echo(f"Created: {wrapper_path.relative_to(repo_root)}")

        # For Rust, create the module file with embedded tests
        elif language == "rs":
            click.echo("Creating Rust module with tests...")

            # Parse the file path from leetcode output
            leetcode_file = parse_leetcode_output(result.stdout)
            if not leetcode_file or not leetcode_file.exists():
                click.echo(
                    f"Error: Could not find leetcode file for problem {problem_number}",
                    err=True,
                )
                click.echo(f"Parsed path: {leetcode_file}", err=True)
                had_error = True
                continue

            click.echo(f"Found: {leetcode_file.relative_to(repo_root)}")

            # Clean up whitespace in the leetcode-generated file
            cleanup_whitespace(leetcode_file)

            # Extract problem description
            problem_desc = extract_problem_description_rs(leetcode_file)
            if not problem_desc:
                click.echo("Warning: Could not extract problem description", err=True)

            # Generate tests with Claude
            click.echo("Generating tests with Claude...")
            tests = generate_rs_tests_with_claude(problem_desc, problem_number)

            if not tests:
                tests = f"""    // TODO: Add tests
    #[test]
    fn test_example1() {{
        // assert_eq!(Solution::method(...), expected);
    }}"""

            # Create module file
            module_path = create_rs_module(
                repo_root, problem_number, leetcode_file, tests
            )
            click.echo(f"Created: {module_path.relative_to(repo_root)}")

    if had_error:
        raise SystemExit(1)
    click.echo("Done!")


if __name__ == "__main__":
    cli()
