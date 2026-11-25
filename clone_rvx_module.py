## ****************************************************************************
## ****************************************************************************
## Copyright SoC Design Research Group, All rights reserved.
## Electronics and Telecommunications Research Institute (ETRI)
##
## THESE DOCUMENTS CONTAIN CONFIDENTIAL INFORMATION AND KNOWLEDGE
## WHICH IS THE PROPERTY OF ETRI. NO PART OF THIS PUBLICATION IS
## TO BE USED FOR ANY OTHER PURPOSE, AND THESE ARE NOT TO BE
## REPRODUCED, COPIED, DISCLOSED, TRANSMITTED, STORED IN A RETRIEVAL
## SYSTEM OR TRANSLATED INTO ANY OTHER HUMAN OR COMPUTER LANGUAGE,
## IN ANY FORM, BY ANY MEANS, IN WHOLE OR IN PART, WITHOUT THE
## COMPLETE PRIOR WRITTEN PERMISSION OF ETRI.
## ****************************************************************************
## ****************************************************************************

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

SHARED_HOME = Path(__file__).resolve().parent
USER_FILE = SHARED_HOME / 'clone_rvx_module.json'

sys.path.insert(0, str(SHARED_HOME / 'rvx_util'))
from os_util import remove_directory  # noqa: E402


def log(*arg_list):
    print(*arg_list, file=sys.stderr, flush=True)


def git(*arg_list, cwd=None):
    log('git', ' '.join(arg_list))
    result = subprocess.run(['git', *arg_list], cwd=cwd, stdout=sys.stderr)
    if result.returncode != 0:
        sys.exit(result.returncode)


def git_ok(*arg_list, cwd=None):
    log('git', ' '.join(arg_list))
    return subprocess.run(['git', *arg_list], cwd=cwd, stdout=sys.stderr).returncode == 0


def git_output(*arg_list, cwd):
    result = subprocess.run(['git', *arg_list], cwd=cwd, stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL, universal_newlines=True)
    return result.stdout.strip() if result.returncode == 0 else ''


def is_branch(commit):
    return not re.fullmatch(r'[0-9a-fA-F]{4,40}', commit)


def get_module_path(name, commit):
    return SHARED_HOME / f'{name}-{commit}'


def update_submodules(module_path):
    if (module_path / '.gitmodules').is_file():
        git('submodule', 'update', '--init', '--recursive', cwd=module_path)


def copy_existing(name, url, commit, module_path, extra_source_path=None):
    source_list = [x for x in SHARED_HOME.glob(f'{name}-*') if x != module_path and (x / '.git').is_dir()]
    if source_list:
        source_path = max(source_list, key=lambda x: x.stat().st_mtime)
    elif extra_source_path and (extra_source_path / '.git').is_dir():
        source_path = extra_source_path
    else:
        return False
    log(f'copy {source_path} to {module_path}')
    shutil.copytree(source_path, module_path, symlinks=True)
    if is_branch(commit):
        arg_list = ('checkout', '-q', '-B', commit, f'origin/{commit}')
    else:
        arg_list = ('checkout', '-q', '--detach', commit)
    if git_ok('remote', 'set-url', 'origin', url, cwd=module_path) and \
            git_ok('fetch', 'origin', cwd=module_path) and \
            git_ok(*arg_list, cwd=module_path):
        if is_branch(commit):
            git('branch', '-q', '-u', f'origin/{commit}', cwd=module_path)
        return True
    log(f'{module_path} can NOT be updated from {source_path}: clone it from the beginning')
    remove_directory(module_path)
    return False


def clone(name, url, commit, extra_source_path=None):
    module_path = get_module_path(name, commit)
    if not (module_path / '.git').exists():
        if os.path.lexists(module_path):
            log(f'[FAIL] {module_path} exists, but is NOT a git repository')
            return 1
        if copy_existing(name, url, commit, module_path, extra_source_path):
            log(f'{module_path} is copied and updated')
        elif is_branch(commit) and git_ok('clone', '-b', commit, url, str(module_path)) or \
                not is_branch(commit) and git_ok('clone', '--no-checkout', url, str(module_path)) and \
                git_ok('checkout', '-q', '--detach', commit, cwd=module_path):
            log(f'{module_path} is cloned')
        else:
            if os.path.lexists(module_path):
                remove_directory(module_path)
            log(f'[FAIL] {name} {commit} can NOT be cloned from {url}')
            return 1
        update_submodules(module_path)
    elif is_branch(commit):
        git('fetch', 'origin', cwd=module_path)
        git('merge', '--ff-only', f'origin/{commit}', cwd=module_path)
        update_submodules(module_path)
    else:
        head = git_output('rev-parse', 'HEAD', cwd=module_path)
        if not head.startswith(commit.lower()):
            log(f'[FAIL] {module_path} is at {head[:7]}, NOT {commit}')
            return 1
        log(f'{module_path} is up to date')
    return 0


def pull(name, url, commit, extra_source_path=None):
    if is_branch(commit):
        return commit if clone(name, url, commit, extra_source_path) == 0 else None
    result = subprocess.run(['git', 'ls-remote', url, 'HEAD'], stdout=subprocess.PIPE, universal_newlines=True)
    latest = result.stdout.split()[0][:7] if result.returncode == 0 and result.stdout.split() else ''
    if not latest:
        log(f'[FAIL] the latest commit of {url} is NOT found')
        return None
    new_commit = commit if latest.startswith(commit.lower()[:7]) else latest
    log(f'{name} {commit} -> {new_commit}' if new_commit != commit else f'{name} {commit} (no update)')
    return new_commit if clone(name, url, new_commit, extra_source_path) == 0 else None


def record_user(name, commit, user_path, user_url):
    user_path = str(Path(user_path).resolve())
    user_dict = json.loads(USER_FILE.read_text(encoding='utf8')) if USER_FILE.is_file() else {}
    dir_name = get_module_path(name, commit).name
    for info in user_dict.values():
        if info['name'] == name:
            info['user'].pop(user_path, None)
    user_dict.setdefault(dir_name, {'name': name, 'commit': commit, 'user': {}})['user'][user_path] = user_url
    for old_dir_name, info in list(user_dict.items()):
        if info['user']:
            continue
        old_path = SHARED_HOME / old_dir_name
        if old_path.parent == SHARED_HOME and os.path.lexists(old_path):
            log(f'{old_path} is removed: no repository uses it')
            remove_directory(old_path)
        del user_dict[old_dir_name]
    USER_FILE.write_text(json.dumps(user_dict, indent=2, sort_keys=True) + '\n', encoding='utf8')
    log(f'{dir_name} is used by {user_path} ({user_url or "no origin"})')

def add_exclude(user_path):
    user_path = Path(user_path).resolve()
    if user_path.parent != SHARED_HOME:
        return
    exclude_file = SHARED_HOME / git_output('rev-parse', '--git-path', 'info/exclude', cwd=SHARED_HOME)
    line = f'/{user_path.name}/'
    line_list = exclude_file.read_text(encoding='utf8').splitlines() if exclude_file.is_file() else []
    if line in line_list:
        return
    exclude_file.parent.mkdir(parents=True, exist_ok=True)
    exclude_file.write_text('\n'.join(line_list + [line]) + '\n', encoding='utf8')
    log(f'{line} is added to {exclude_file}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='clone a module shared by the repositories here, and print the directory')
    parser.add_argument('-name', required=True, help='module name (e.g. rvx_binary)')
    parser.add_argument('-commit', required=True, help='commit (or branch)')
    parser.add_argument('-url', help='repository url (required unless -path_only)')
    parser.add_argument('-path_only', action='store_true', help='print the directory without cloning')
    parser.add_argument('-pull', action='store_true', help='move to the latest commit of the default branch (a new directory), and print it')
    parser.add_argument('-source', help='a clone of the module to copy from when none is here')
    parser.add_argument('-user_path', help='top directory of the repository that uses the module')
    parser.add_argument('-user_url', default='', help='git url of the repository that uses the module')
    args = parser.parse_args()
    commit = args.commit
    if not args.path_only:
        if not args.url:
            parser.error('-url is required unless -path_only')
        source_path = Path(args.source).resolve() if args.source else None
        if args.pull:
            commit = pull(args.name, args.url, args.commit, source_path)
            if not commit:
                sys.exit(1)
        elif clone(args.name, args.url, args.commit, source_path) != 0:
            sys.exit(1)
        if args.user_path:
            record_user(args.name, commit, args.user_path, args.user_url)
            add_exclude(args.user_path)
    print(get_module_path(args.name, commit))
