import ast
import os
import re
import time
from collections import Counter, defaultdict
from importlib.util import find_spec

import click
from rich.console import Console
from rich.table import Table
from stdlib_list import stdlib_list


# 获取当前 Python 版本的标准库
stdlib = set(stdlib_list())
console = Console()


def is_stdlib(module_name):
    return module_name.split(".")[0] in stdlib


def is_installed_package(module_name):
    try:
        spec = find_spec(module_name.split(".")[0])
        if spec is not None and spec.origin and "site-packages" in spec.origin:
            return True
    except (ImportError, AttributeError):
        # ImportError: 模块不存在
        # AttributeError: spec或origin访问出错
        pass
    return False


def is_project_module(module_name, project_root):
    parts = module_name.split(".")
    path = os.path.join(project_root, *parts)
    return os.path.exists(path + ".py") or os.path.isdir(path)


def get_imports_from_file(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        try:
            content = f.read()
            tree = ast.parse(content, filename=file_path)
        except SyntaxError:
            return []

    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
    return imports


def find_module_imports(file_path, target_module):
    """Find line numbers where a specific module is imported in a file."""
    results = []

    with open(file_path, "r", encoding="utf-8") as f:
        try:
            content = f.readlines()
        except UnicodeDecodeError:
            return []

    for i, line in enumerate(content, 1):
        line = line.strip()
        # Check for direct imports
        if (
            re.search(rf"\bimport\s+{target_module}\b", line)
            or re.search(rf"\bimport\s+.*,\s*{target_module}\b", line)
            or re.search(rf"\bfrom\s+{target_module}\b", line)
            or re.search(rf"\bfrom\s+{target_module}\.\b", line)
        ):
            results.append((i, line))

    return results


def load_gitignore_patterns(project_root):
    patterns = []
    gitignore_path = os.path.join(project_root, ".gitignore")
    if os.path.exists(gitignore_path):
        with open(gitignore_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    # Convert gitignore pattern to regex
                    pattern = line.replace(".", r"\.").replace("*", ".*")
                    patterns.append(re.compile(pattern))
    return patterns


def is_ignored(file_path, project_root, gitignore_patterns):
    if not gitignore_patterns:
        return False

    # Get relative path from project root
    rel_path = os.path.relpath(file_path, project_root)

    # Check if file matches any gitignore pattern
    for pattern in gitignore_patterns:
        if pattern.search(rel_path):
            return True
    return False


def collect_all_imports(project_root, use_top_level=False, include_gitignore=False):
    counter = Counter()
    file_count = 0

    gitignore_patterns = (
        [] if include_gitignore else load_gitignore_patterns(project_root)
    )

    for root, _, files in os.walk(project_root):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)

                # Skip files that match gitignore patterns
                if is_ignored(file_path, project_root, gitignore_patterns):
                    continue

                imports = get_imports_from_file(file_path)
                if use_top_level:
                    imports = [imp.split(".")[0] for imp in imports]
                counter.update(imports)
                file_count += 1
    return counter, file_count


def find_files_importing_module(
    project_root, module_name, include_gitignore=False, exclude_patterns=None
):
    results = []
    file_count = 0

    gitignore_patterns = (
        [] if include_gitignore else load_gitignore_patterns(project_root)
    )

    # 编译exclude patterns
    exclude_regexes = []
    if exclude_patterns:
        for pattern in exclude_patterns:
            # 将glob pattern转换为regex
            regex = pattern.replace(".", r"\.").replace("*", ".*")
            exclude_regexes.append(re.compile(regex))

    for root, _, files in os.walk(project_root):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, project_root)

                # Skip files that match gitignore patterns
                if is_ignored(file_path, project_root, gitignore_patterns):
                    continue

                # Skip files that match exclude patterns
                if exclude_regexes and any(
                    regex.search(rel_path) for regex in exclude_regexes
                ):
                    continue

                file_count += 1
                import_lines = find_module_imports(file_path, module_name)
                if import_lines:
                    results.append((rel_path, import_lines))

    return results, file_count


def classify_imports(import_counter, project_root):
    categorized = defaultdict(list)
    for module, count in import_counter.items():
        if is_stdlib(module):
            categorized["stdlib"].append((module, count))
        elif is_installed_package(module):
            categorized["third_party"].append((module, count))
        elif is_project_module(module, project_root):
            categorized["local"].append((module, count))
        else:
            categorized["unknown"].append((module, count))
    return categorized


def print_result(categorized_imports, show_local=False):
    categories = ["third_party", "unknown", "stdlib"]
    if show_local:
        categories.append("local")

    category_colors = {
        "third_party": "green",
        "unknown": "yellow",
        "stdlib": "blue",
        "local": "magenta",
    }

    for category in categories:
        items = sorted(categorized_imports.get(category, []), key=lambda x: -x[1])
        if items:
            console.print(
                f"\n[bold]{len(items)} unique {category.upper()} modules:[/bold]",
                style=category_colors[category],
            )

            table = Table(
                show_header=True, header_style=f"bold {category_colors[category]}"
            )
            table.add_column("Module", style=category_colors[category])
            table.add_column("Count", justify="right")

            for mod, count in items:
                table.add_row(mod, str(count))

            console.print(table)


def print_find_results(results):
    if not results:
        console.print("[bold red]No files found importing this module.[/bold red]")
        return

    # 创建表格
    table = Table(show_header=True, header_style="bold blue")
    table.add_column("File", style="blue")
    table.add_column("Line", justify="right", style="cyan")
    table.add_column("Import Statement", style="yellow")

    for file_path, lines in results:
        for line_num, line_content in lines:
            table.add_row(file_path, str(line_num), line_content.strip())

    console.print(table)


@click.group()
def cli():
    """Analyze Python imports in a project."""
    pass


@cli.command()
@click.argument("project_root", type=click.Path(exists=True), default=".")
@click.option("--show-local", is_flag=True, help="Show local project imports")
@click.option(
    "--top-level-only",
    is_flag=True,
    help="Show only top-level modules instead of full module names",
)
@click.option(
    "--include-gitignore",
    is_flag=True,
    help="Include files that would be ignored by .gitignore",
)
def stats(project_root, show_local, top_level_only, include_gitignore):
    """Analyze import statistics in a project."""
    start_time = time.time()

    with console.status("[bold green]Analyzing imports...[/bold green]"):
        import_counter, file_count = collect_all_imports(
            project_root,
            use_top_level=top_level_only,
            include_gitignore=include_gitignore,
        )
        categorized = classify_imports(import_counter, project_root)

    print_result(categorized, show_local=show_local)

    elapsed_time = time.time() - start_time
    console.print("\n[bold]SUMMARY:[/bold]")
    console.print(
        f"Parsed [bold cyan]{file_count}[/bold cyan] Python files in [bold cyan]{elapsed_time:.2f}[/bold cyan] seconds"
    )


@cli.command()
@click.argument("module_name")
@click.argument("project_root", type=click.Path(exists=True), default=".")
@click.option(
    "--include-gitignore",
    is_flag=True,
    help="Include files that would be ignored by .gitignore",
)
@click.option(
    "--exclude",
    "-e",
    multiple=True,
    help="Exclude files matching these patterns (e.g. '*test*.py' or 'tests/*')",
)
def find(module_name, project_root, include_gitignore, exclude):
    """Find files importing a specific module."""
    start_time = time.time()

    with console.status(
        f"[bold green]Searching for imports of '{module_name}'...[/bold green]"
    ):
        results, file_count = find_files_importing_module(
            project_root,
            module_name,
            include_gitignore=include_gitignore,
            exclude_patterns=exclude if exclude else None,
        )

    print_find_results(results)

    elapsed_time = time.time() - start_time
    console.print("\n[bold]SUMMARY:[/bold]")
    console.print(
        f"Found [bold cyan]{len(results)}[/bold cyan] files importing '[bold green]{module_name}[/bold green]' (searched [bold cyan]{file_count}[/bold cyan] files in [bold cyan]{elapsed_time:.2f}[/bold cyan] seconds)"
    )


if __name__ == "__main__":
    cli()
