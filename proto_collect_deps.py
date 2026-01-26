#!/usr/bin/env python3
import argparse
import os
import shutil
import subprocess
import sys
import tempfile

from google.protobuf import descriptor_pb2


def _run_protoc(proto_path, entry_relpath):
    with tempfile.NamedTemporaryFile(suffix=".pb", delete=False) as tmp:
        desc_path = tmp.name
    try:
        cmd = [
            "protoc",
            f"--proto_path={proto_path}",
            f"--descriptor_set_out={desc_path}",
            "--include_imports",
            entry_relpath,
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        fds = descriptor_pb2.FileDescriptorSet()
        with open(desc_path, "rb") as fh:
            fds.ParseFromString(fh.read())
        return fds
    finally:
        try:
            os.remove(desc_path)
        except OSError:
            pass


def _collect_import_closure(file_descs, entry_relpath):
    by_name = {f.name: f for f in file_descs}
    needed = set()
    queue = [entry_relpath]

    while queue:
        name = queue.pop()
        if name in needed:
            continue
        needed.add(name)
        f = by_name.get(name)
        if f is None:
            continue
        for dep in f.dependency:
            queue.append(dep)

    return needed


def _copy_files(files, base_dir, target_dir):
    for relpath in sorted(files):
        src = os.path.join(base_dir, relpath)
        dst = os.path.join(target_dir, relpath)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)


def main():
    parser = argparse.ArgumentParser(
        description="Copy protobuf dependencies for a given entry message."
    )
    parser.add_argument("proto", help="Entry .proto file path")
    parser.add_argument("base_dir", help="Base directory for protos")
    parser.add_argument("target_dir", help="Target output directory")
    args = parser.parse_args()

    base_dir = os.path.abspath(args.base_dir)
    target_dir = os.path.abspath(args.target_dir)
    proto_path = os.path.abspath(args.proto)

    if not proto_path.startswith(base_dir + os.sep):
        print("Entry proto must be under base-dir.", file=sys.stderr)
        return 2

    entry_relpath = os.path.relpath(proto_path, base_dir)

    try:
        fds = _run_protoc(base_dir, entry_relpath)
    except FileNotFoundError:
        print("protoc not found. Please install protoc.", file=sys.stderr)
        return 2
    except subprocess.CalledProcessError as exc:
        err = exc.stderr.decode("utf-8", errors="ignore")
        print(f"protoc failed:\n{err}", file=sys.stderr)
        return 2

    needed_files = _collect_import_closure(fds.file, entry_relpath)
    _copy_files(needed_files, base_dir, target_dir)

    for rel in sorted(needed_files):
        print(rel)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
