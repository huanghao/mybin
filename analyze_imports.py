import argparse
import ast
import os
import re
import sys
import time
from collections import Counter, defaultdict
from importlib.util import find_spec

from stdlib_list import stdlib_list


def parse_args():
    parser = argparse.ArgumentParser(description="Analyze Python imports in a project")
    parser.add_argument(
        "project_root",
        nargs="?",
        default=".",
        help="Root directory of the project to analyze (default: current directory)",
    )
    parser.add_argument(
        "--show-local", action="store_true", help="Show local project imports"
    )
    parser.add_argument(
        "--top-level-only",
        action="store_true",
        help="Show only top-level modules instead of full module names",
    )
    parser.add_argument(
        "--include-gitignore",
        action="store_true",
        help="Include files that would be ignored by .gitignore",
    )
    return parser.parse_args()


# 获取当前 Python 版本的标准库
stdlib = set(stdlib_list())


def is_stdlib(module_name):
    return module_name.split(".")[0] in stdlib


def is_installed_package(module_name):
    try:
        spec = find_spec(module_name.split(".")[0])
        if spec is not None and spec.origin and "site-packages" in spec.origin:
            return True
    except:
        pass
    return False


def is_project_module(module_name, project_root):
    parts = module_name.split(".")
    path = os.path.join(project_root, *parts)
    return os.path.exists(path + ".py") or os.path.isdir(path)


def get_imports_from_file(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        try:
            tree = ast.parse(f.read(), filename=file_path)
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

    for category in categories:
        items = sorted(categorized_imports.get(category, []), key=lambda x: -x[1])
        if items:
            print(f"\n# {len(items)} unique {category.upper()} modules:")
            for mod, count in items:
                print(f"{mod:<30} {count}")


def main():
    start_time = time.time()
    args = parse_args()
    project_root = args.project_root
    use_top_level = args.top_level_only

    import_counter, file_count = collect_all_imports(
        project_root,
        use_top_level=use_top_level,
        include_gitignore=args.include_gitignore,
    )
    categorized = classify_imports(import_counter, project_root)
    print_result(categorized, show_local=args.show_local)

    elapsed_time = time.time() - start_time
    print(f"\n# SUMMARY:")
    print(f"Parsed {file_count} Python files in {elapsed_time:.2f} seconds")


if __name__ == "__main__":
    main()
