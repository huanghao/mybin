from __future__ import print_function
import os
import sys
import argparse
from contextlib import contextmanager


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

def usage():
    print('''usage: %s update|list|repo|<language>''' % sys.argv[0])


def main():
    if len(sys.argv) < 2:
        usage()
        sys.exit(1)

    if not os.path.exists(repo):
        clone()

    action = sys.argv[1]
    if action == 'update':
        git(['pull'])
        #git(['fetch', 'origin'],
        #    ['reset', '--hard', 'origin/master'])
    elif action == 'list':
        langs = [i[:-len(gig)] for i in os.listdir(repo) if i.endswith(gig)]
        langs += [os.path.join('Global', i[:-len(gig)]) for i in os.listdir(os.path.join(repo, 'Global')) if i.endswith(gig)]
        print('\n'.join(sorted(langs)))
    elif action == 'repo':
        print(remote)
    else:
        for lang in sys.argv[1:]:
            basename = '%s.gitignore' % lang
            path = os.path.join(repo, basename)
            if os.path.exists(path):
                print('#' * 10, lang, 'START', '#' * 10)
                print(open(path).read())
                print('#' * 10, lang, 'END', '#' * 10)
            else:
                print('Unknown language', lang, file=sys.stderr)


if __name__ == '__main__':
    main()
