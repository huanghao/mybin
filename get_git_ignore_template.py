from __future__ import print_function
import os
import sys
import argparse
import textwrap
import subprocess
import datetime
from contextlib import contextmanager

import humanize


remote = 'https://github.com/github/gitignore.git'
repo = os.path.expanduser('~/.cache/gitignore')
gig = '.gitignore'

@contextmanager
def cd(path):
    old = os.getcwd()
    try:
        print('cd', path)
        os.chdir(path)
        yield
    finally:
        os.chdir(old)

def system(cmd):
    c = ' '.join(cmd)
    print(c)
    r = os.system(c)
    if r != 0:
        print('os.system returns', r, file=sys.stderr)
        sys.exit(1)

def clone():
    system(['git', 'clone', remote, repo])

def git(*cmds):
    with cd(repo):
        for cmd in cmds:
            cmd.insert(0, 'git')
            system(cmd)

def get_repo_last_update():
    try:
        out = subprocess.check_output(
            ["git", "-C", repo, "log", "-1", "--format=%cI"],
            stderr=subprocess.STDOUT,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        print("Failed to get repo last update:", exc, file=sys.stderr)
        return None
    return out.decode("utf-8", "replace").strip()

def humanize_ago(iso_ts):
    try:
        dt = datetime.datetime.fromisoformat(iso_ts)
    except (ValueError, TypeError):
        return None
    return humanize.naturaltime(dt)

def handle_update():
    git(["pull"])
    # git(['fetch', 'origin'],
    #    ['reset', '--hard', 'origin/master'])


def handle_list():
    langs = [i[: -len(gig)] for i in os.listdir(repo) if i.endswith(gig)]
    langs += [
        os.path.join("Global", i[: -len(gig)])
        for i in os.listdir(os.path.join(repo, "Global"))
        if i.endswith(gig)
    ]
    print("\n".join(sorted(langs)))


def handle_repo():
    print(remote)
    last_update = get_repo_last_update()
    if last_update:
        humanized = humanize_ago(last_update)
        if humanized:
            print("Last update:", last_update, "(%s)" % humanized)
        else:
            print("Last update:", last_update)


def handle_get(languages):
    for lang in languages:
        basename = "%s.gitignore" % lang
        path = os.path.join(repo, basename)
        if os.path.exists(path):
            print("#" * 10, lang, "START", "#" * 10)
            print(open(path).read())
            print("#" * 10, lang, "END", "#" * 10)
        else:
            print("Unknown language", lang, file=sys.stderr)

def is_git_repo(path):
    try:
        subprocess.check_output(
            ["git", "-C", path, "rev-parse", "--is-inside-work-tree"],
            stderr=subprocess.STDOUT,
        )
        return True
    except (OSError, subprocess.CalledProcessError):
        return False

def confirm_git_init():
    answer = input("Current directory is not a git repo. Run git init? (yes/no): ")
    return answer.strip().lower() in ("yes", "y")

def ensure_gitignore(path):
    target = os.path.join(path, gig)
    if not os.path.exists(target):
        open(target, "a").close()

def handle_init(languages):
    cwd = os.getcwd()
    if not is_git_repo(cwd):
        if not confirm_git_init():
            print("Canceled: git init not confirmed.", file=sys.stderr)
            sys.exit(1)
        system(["git", "init"])
    ensure_gitignore(cwd)
    handle_get(languages)

def parse_args(argv=None):
    epilog = textwrap.dedent(
        """\
        Examples:
          %(prog)s update
          %(prog)s list
          %(prog)s repo
          %(prog)s Python Global/macOS
          %(prog)s get Python Global/macOS
          %(prog)s init Python Global/macOS
        """
    )
    parser = argparse.ArgumentParser(
        description="Fetch and print gitignore templates from github/gitignore",
        epilog=epilog,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")

    subparsers.add_parser("update", help="Update local gitignore template repo")
    subparsers.add_parser("list", help="List all available templates")
    subparsers.add_parser("repo", help="Show template repo URL")

    get_parser = subparsers.add_parser("get", help="Print one or more templates")
    get_parser.add_argument(
        "languages",
        nargs="+",
        metavar="LANG",
        help="Template name (e.g. Python, Global/macOS)",
    )

    init_parser = subparsers.add_parser(
        "init",
        help="Initialize git repo and .gitignore, then print templates",
    )
    init_parser.add_argument(
        "languages",
        nargs="+",
        metavar="LANG",
        help="Template name (e.g. Python, Global/macOS)",
    )

    # Legacy compatibility: allow languages directly without "get".
    if argv is None:
        argv = sys.argv[1:]
    args = parser.parse_args(argv)

    if not argv:
        parser.print_help()
        sys.exit(1)

    if args.command is None:
        args.command = "get"
        args.languages = argv
    return args


def main():
    args = parse_args()

    if not os.path.exists(repo):
        clone()

    action = args.command
    if action == "update":
        handle_update()
    elif action == "list":
        handle_list()
    elif action == "repo":
        handle_repo()
    elif action == "init":
        handle_init(args.languages)
    else:
        handle_get(args.languages)


if __name__ == '__main__':
    main()
