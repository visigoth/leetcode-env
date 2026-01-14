"""CLI wrapper for leetcode commands."""

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


def extract_problem_description(cpp_file: Path) -> str:
    """Extract the problem description comment block from a leetcode cpp file."""
    content = cpp_file.read_text()
    # Find the comment block at the start
    if content.startswith("/*"):
        end_idx = content.find("*/")
        if end_idx != -1:
            return content[: end_idx + 2]
    return ""


def generate_tests_with_claude(problem_desc: str, problem_number: int) -> str:
    """Use claude CLI to generate GoogleTest tests from problem description."""
    prompt = f"""Given this C++ LeetCode problem, generate GoogleTest test cases based on the examples.

{problem_desc}

Requirements:
- Output ONLY the TEST() macros, no explanation or other text
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
        return result.stdout.strip()
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


@click.group()
def cli():
    """LeetCode CLI wrapper with additional tooling."""
    pass


@cli.command()
@click.argument("problem_number", type=int)
@click.option(
    "-l",
    "--lang",
    default="cpp",
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
            tests = generate_tests_with_claude(problem_desc, problem_number)

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

    if had_error:
        raise SystemExit(1)
    click.echo("Done!")


if __name__ == "__main__":
    cli()
