"""CLI wrapper for leetcode commands."""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import click
import tree_sitter_cpp as ts_cpp
from tree_sitter import Language, Parser


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
            return Path(path_str).resolve()
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

    # Calculate relative path from src/ to the leetcode file
    relative_path = os.path.relpath(leetcode_file, src_dir)

    # Create module: import Solution from crate root, include the solution file
    module_content = f'''use crate::Solution;

include!("{relative_path}");

#[cfg(test)]
mod tests {{
    use super::*;

{tests}
}}
'''

    module_path = src_dir / f"p{problem_number}.rs"
    module_path.write_text(module_content)

    # Update lib.rs to include the new module and ensure Solution struct exists
    lib_path = src_dir / "lib.rs"
    lib_content = lib_path.read_text() if lib_path.exists() else ""

    # Ensure Solution struct is defined in lib.rs
    if "pub struct Solution" not in lib_content:
        lib_content = "pub struct Solution;\n\n" + lib_content

    module_decl = f"pub mod p{problem_number};"
    if module_decl not in lib_content:
        if lib_content and not lib_content.endswith("\n"):
            lib_content += "\n"
        lib_content += f"{module_decl}\n"
        lib_path.write_text(lib_content)

    return module_path


def find_test_nodes(node, tests: list):
    """Recursively find TEST() macros in the AST."""
    # TEST(Suite, Name) { body } parses as function_definition
    if node.type == "function_definition":
        declarator = None
        body = None
        for child in node.children:
            if child.type == "function_declarator":
                declarator = child
            elif child.type == "compound_statement":
                body = child

        if declarator and body and declarator.text.startswith(b"TEST("):
            # Parse TEST(Suite, Name)
            decl_text = declarator.text.decode()
            # Extract the part inside parentheses
            match = re.match(r"TEST\(([^,]+),\s*([^)]+)\)", decl_text)
            if match:
                test_name = match.group(2).strip()
                tests.append({
                    "name": test_name,
                    "body": body.text.decode(),
                    "body_node": body,
                })
        return

    # Recurse into child nodes (e.g., namespace bodies)
    for child in node.children:
        find_test_nodes(child, tests)


def parse_tests(content: str) -> list[dict]:
    """Extract test info using tree-sitter."""
    cpp_language = Language(ts_cpp.language())
    parser = Parser(cpp_language)
    tree = parser.parse(content.encode())

    tests = []
    find_test_nodes(tree.root_node, tests)
    return tests


def find_solution_var_names(node) -> set[str]:
    """Find variable names declared as Solution in a compound_statement."""
    names = set()
    for child in node.children:
        if child.type == "declaration":
            text = child.text.decode()
            m = re.match(r"Solution\s+(\w+)", text)
            if m:
                names.add(m.group(1))
    return names


def find_solution_call(node, var_names: set[str]) -> str | None:
    """Recursively find solution.method(...) call expression."""
    if node.type == "call_expression":
        func = node.child_by_field_name("function")
        if func and func.type == "field_expression":
            obj = func.child_by_field_name("argument")
            if obj and obj.text.decode() in var_names:
                return node.text.decode()

    for child in node.children:
        result = find_solution_call(child, var_names)
        if result:
            return result
    return None


def extract_benchmark_parts(body_node) -> tuple[str, str | None]:
    """Extract setup code and solution call from test body AST."""
    var_names = find_solution_var_names(body_node)
    setup_lines = []
    solution_call = None

    for stmt in body_node.children:
        if stmt.type in ("{", "}"):
            continue

        text = stmt.text.decode().strip()

        # Skip EXPECT_*/ASSERT_* but extract the solution call
        if stmt.type == "expression_statement":
            inner = stmt.children[0] if stmt.children else None
            if inner and inner.type == "call_expression":
                func = inner.child_by_field_name("function")
                func_name = func.text.decode() if func else ""
                if func_name.startswith(("EXPECT_", "ASSERT_")):
                    # Find solution.method(...) inside assertion args
                    solution_call = find_solution_call(inner, var_names) or solution_call
                    continue

        # Check for result = solution.method(...) or declaration with solution call
        if stmt.type == "declaration" and any(f"{v}." in text for v in var_names):
            found_call = find_solution_call(stmt, var_names)
            if found_call:
                solution_call = found_call
                # Still add the declaration as setup (minus the init)
                # Extract just the variable declaration part for setup
                setup_lines.append(text)
                continue

        setup_lines.append(text)

    # Clean up setup lines - remove any that contain the solution call
    if solution_call:
        setup_lines = [
            line for line in setup_lines
            if solution_call not in line
        ]

    return "\n    ".join(setup_lines), solution_call


def generate_benchmark_code(tests: list[dict]) -> str:
    """Generate benchmark functions from parsed tests."""
    benchmarks = []

    for test in tests:
        name = test["name"]
        body_node = test["body_node"]
        setup_code, solution_call = extract_benchmark_parts(body_node)

        if not solution_call:
            # Skip tests where we couldn't find the solution call
            continue

        # Build the benchmark function
        benchmark = f"""static void BM_{name}(benchmark::State& state) {{
    {setup_code}
    for (auto _ : state) {{
        benchmark::DoNotOptimize({solution_call});
    }}
}}
BENCHMARK(BM_{name});"""
        benchmarks.append(benchmark)

    return "\n\n".join(benchmarks)


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


LANG_EXTENSIONS = {"cpp": "cpp", "py": "py", "rs": "rs"}


def detect_language(lang_override: str | None) -> str:
    """Detect language from override, current directory, or environment."""
    if lang_override:
        return lang_override

    # Check if we're in a language directory
    cwd_name = Path.cwd().name
    if cwd_name in LANG_EXTENSIONS:
        return cwd_name

    # Fall back to environment variable
    default_lang = os.environ.get("LEETCODE_DEFAULT_LANG")
    if default_lang:
        return default_lang

    raise click.ClickException(
        "No language specified and not in a language directory.\n"
        "Use --lang or set LEETCODE_DEFAULT_LANG"
    )


def find_solution_file(repo_root: Path, problem_number: int, lang: str) -> Path:
    """Find the solution file for a problem in a given language."""
    if lang not in LANG_EXTENSIONS:
        raise click.ClickException(f"Unknown language: {lang}")

    ext = LANG_EXTENSIONS[lang]
    lang_dir = repo_root / lang

    # Search for file matching pattern: <number>.*.<ext>
    pattern = f"{problem_number}.*"
    for path in lang_dir.rglob(f"{pattern}.{ext}"):
        # Ensure it matches the problem number exactly (not 10 matching 1)
        if re.match(rf"^{problem_number}\.", path.name):
            return path

    raise click.ClickException(
        f"Solution not found for problem {problem_number} in {lang}"
    )


def run_leetcode_command(cmd: str, problem_number: int, lang: str | None) -> None:
    """Run a leetcode CLI command (x for submit, t for test) on a solution."""
    repo_root = get_repo_root()
    lang = detect_language(lang)
    solution_file = find_solution_file(repo_root, problem_number, lang)

    # Get path relative to repo root (matches workspace workdir layout)
    rel_path = solution_file.relative_to(repo_root)

    action = "Submitting" if cmd == "x" else "Testing"
    click.echo(f"{action}: {rel_path}")

    # Run from repo root so paths align with workspace workdir config
    try:
        subprocess.run(
            ["leetcode", cmd, str(rel_path)],
            cwd=repo_root,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        raise SystemExit(e.returncode)


@cli.command()
@click.argument("problem_number", type=int)
@click.option("-l", "--lang", default=None, help="Language: cpp, py, rs")
def submit(problem_number: int, lang: str | None):
    """Submit a solution to LeetCode."""
    run_leetcode_command("x", problem_number, lang)


@cli.command("try")
@click.argument("problem_number", type=int)
@click.option("-l", "--lang", default=None, help="Language: cpp, py, rs")
def try_solution(problem_number: int, lang: str | None):
    """Test a solution on LeetCode (without submitting)."""
    run_leetcode_command("t", problem_number, lang)


@cli.group()
def cpp():
    """C++ specific commands."""
    pass


@cpp.command("gen-bench")
@click.argument("problem_number", type=int)
def gen_bench(problem_number: int):
    """Generate benchmarks from a test wrapper.

    Creates cpp/bench/<N>.cpp from cpp/<N>.cpp with one benchmark per test.
    """
    repo_root = get_repo_root()
    cpp_dir = repo_root / "cpp"
    test_file = cpp_dir / f"{problem_number}.cpp"
    bench_dir = cpp_dir / "bench"
    bench_file = bench_dir / f"{problem_number}.cpp"

    if not test_file.exists():
        raise click.ClickException(f"Test wrapper not found: {test_file}")

    bench_dir.mkdir(exist_ok=True)

    content = test_file.read_text()

    # Extract solution include
    solution_match = re.search(r'#include "([^"]+\.cpp)"', content)
    if not solution_match:
        raise click.ClickException("Could not find solution #include in test wrapper")
    solution_include = solution_match.group(1)

    # Extract std includes (excluding gtest)
    std_includes = re.findall(r"#include <([^>]+)>", content)
    std_includes = [i for i in std_includes if "gtest" not in i]

    # Extract using declarations
    using_decls = re.findall(r"^using [^;]+;", content, re.MULTILINE)

    # Parse tests with tree-sitter
    tests = parse_tests(content)
    if not tests:
        raise click.ClickException("No TEST() macros found in test wrapper")

    # Generate benchmark functions
    benchmark_code = generate_benchmark_code(tests)
    if not benchmark_code:
        raise click.ClickException("Could not extract solution calls from tests")

    # Build the benchmark file
    std_include_lines = "\n".join(f"#include <{i}>" for i in std_includes)
    using_lines = "\n".join(using_decls)

    bench_content = f"""#include <benchmark/benchmark.h>
{std_include_lines}

namespace leetcode::p{problem_number} {{ class Solution; }}
#define Solution leetcode::p{problem_number}::Solution

{using_lines}

#include "{solution_include}"

namespace leetcode::p{problem_number} {{

{benchmark_code}

}}

BENCHMARK_MAIN();
"""

    bench_file.write_text(bench_content)
    click.echo(f"Generated: {bench_file.relative_to(repo_root)}")
    click.echo(f"Benchmarks: {len(tests)}")
    click.echo("Run: just profile " + str(problem_number))


@cpp.command("fix-clangd")
def fix_clangd():
    """Fix compile_commands.json for clangd LSP support.

    Adds entries for solution files that are #included by wrapper files,
    so clangd can provide proper LSP support when editing solution files.
    """
    repo_root = get_repo_root()
    cpp_dir = repo_root / "cpp"
    cc_path = cpp_dir / "build" / "compile_commands.json"

    if not cc_path.exists():
        click.echo(f"Error: {cc_path} not found. Run cmake build first.", err=True)
        raise SystemExit(1)

    cc = json.loads(cc_path.read_text())

    # Track existing files to avoid duplicates
    existing_files = {entry["file"] for entry in cc}

    new_entries = []
    for entry in cc:
        # Match wrapper files like /path/to/cpp/5.cpp
        if re.search(r"/\d+\.cpp$", entry["file"]):
            wrapper = Path(entry["file"])
            if not wrapper.exists():
                continue

            content = wrapper.read_text()
            # Find the #include for the solution file
            match = re.search(r'#include\s+"([^"]+)"', content)
            if match:
                solution_path = (wrapper.parent / match.group(1)).resolve()
                if solution_path.exists() and str(solution_path) not in existing_files:
                    new_entry = entry.copy()
                    new_entry["file"] = str(solution_path)
                    new_entries.append(new_entry)
                    existing_files.add(str(solution_path))

    if new_entries:
        cc.extend(new_entries)
        cc_path.write_text(json.dumps(cc, indent=2) + "\n")
        click.echo(f"Added {len(new_entries)} solution file entries to compile_commands.json")
    else:
        click.echo("No new entries to add")


if __name__ == "__main__":
    cli()
