#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import re
import sys
import argparse
import platform
import subprocess
import shutil
import tarfile
import tempfile

from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional

# 基础信息
script_path = Path(sys.argv[0]).resolve()

SKIP_PATTERNS = (
    # GLIBC
    r'libc\.so(\..*)?',
    r'libpthread\.so(\..*)?',
    r'libdl\.so(\..*)?',
    r'librt\.so(\..*)?',
    r'libutil\.so(\..*)?',
    r'libm\.so(\..*)?',
    r'libmvec\.so(\..*)?',
    r'libresolv\.so(\..*)?',
    r'libanl\.so(\..*)?',
    r'libBrokenLocale\.so(\..*)?',
    r'libcidn\.so(\..*)?',
    r'libcrypt\.so(\..*)?',
    r'libnsl\.so(\..*)?',
    r'libnss_(compat|dns|files|hesiod|nis|nisplus)\.so(\..*)?',
    r'libthread_db\.so(\..*)?',

    # PT_INTERP
    r'ld-linux.*\.so(\..*)?',    # glibc
    r'ld-musl.*\.so(\..*)?',     # musl
    r'ld64\.so(\..*)?',          # ppc64/s390x

    # 内核虚拟对象
    r'linux-(vdso|gate)\.so(\..*)?'
)
SKIP_RE = re.compile('|'.join(SKIP_PATTERNS))

@dataclass(frozen=True)
class Dep:
    name: str
    path: Optional[Path]

@dataclass(frozen=True)
class LddResult:
    deps: List[Dep]
    error: Optional[str]

    def __bool__(self):
        return self.error is None

def ldd(f: Path) -> LddResult:
    try:
        res = subprocess.run(
            ["ldd", str(f)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="ignore"
        )
    except Exception as e:
        return LddResult(deps=[], error=str(e))

    if res.returncode != 0:
        return LddResult(deps=[], error=res.stdout.strip() + f" (code: {res.returncode})")

    deps = []
    for line in res.stdout.splitlines():
        line = line.strip()
        if not line:
            continue

        # 移除加载地址'(0x...)'
        if "(0x" in line:
            line = line.rpartition("(0x")[0].strip()
        if not line:
            continue

        if "=>" in line:
            name, _, path = line.partition("=>")
            name = name.strip()
            path = path.strip()
            path = Path(path).resolve() if path and path != "not found" else None
            deps.append(Dep(name, path))
        elif "/" in line:   # 过滤不含'/'的内核虚拟对象，例如：linux-vdso.so.1
            name = line
            path = Path(line)
            # PT_INTERP或路径形式NEEDED，ldd不检查not found，需要exist判断存在性
            path = path.resolve() if path.exists() else None
            deps.append(Dep(name, path))

    return LddResult(deps=deps, error=None)


def main():
    print(f"cmd: {script_path.name} {' '.join(sys.argv[1:])}")
    print(f"exe: {script_path}")
    print(f"cwd: {os.getcwd()}\n")

    parser = argparse.ArgumentParser(description="pack an ELF binary with its shared library dependencies")
    parser.add_argument("elf", help="path to the ELF executable or shared library to pack")
    parser.add_argument("-o", "--output", default=os.getcwd(), help="output directory (default: current working directory)")
    args = parser.parse_args()

    elf_path = Path(args.elf).absolute()
    if not elf_path.is_file():
        print(f"error: '{elf_path}' is not a file", file=sys.stderr)
        sys.exit(1)

    res = ldd(elf_path)
    if not res:
        print(f"error: ldd failed on '{elf_path}'. {res.error}", file=sys.stderr)
        sys.exit(1)

    # 校验并过滤依赖
    dep_error = False
    required_deps = []
    for dep in res.deps:
        dep_name = Path(dep.name).name
        if SKIP_RE.match(dep_name):
            continue

        if "/" in dep.name:
            print(f"error: dependency '{dep.name}' is path-form, consider patchelf", file=sys.stderr)
            dep_error = True
            continue

        if dep.path is None:
            print(f"error: dependency '{dep.name}' not found", file=sys.stderr)
            dep_error = True
            continue

        required_deps.append(dep)

    if dep_error:
        sys.exit(1)

    # 提取ELF文件名（库文件移除.so及后缀）
    is_lib = re.match(r"(.*)\.so(\.\d+)*$", elf_path.name)
    elf_name = is_lib.group(1) if is_lib else elf_path.name
    if not elf_name:
        print(f"error: bad elf name '{elf_path.name}'", file=sys.stderr)
        sys.exit(1)

    # 默认包名：<elf>-<os>-<arch>
    package_name = f"{elf_name}-{platform.system().lower()}-{platform.machine()}"

    # 创建输出目录
    output_dir = Path(args.output)
    if output_dir.exists() and not output_dir.is_dir():
        print(f"error: output dir '{output_dir}' already exists and is not a directory", file=sys.stderr)
        sys.exit(1)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_dir = output_dir.resolve()

    archive_path = output_dir / f"{package_name}.tar.gz"

    # 在临时目录组装打包内容
    with tempfile.TemporaryDirectory() as temp_dir:
        package_dir = Path(temp_dir) / package_name
        package_dir.mkdir()
        
        # 拷贝ELF
        elf_type = "lib" if is_lib else "bin"
        elf_dir = package_dir / elf_type
        elf_dir.mkdir()
        shutil.copy2(elf_path, elf_dir / elf_path.name)
        print(f"pack '{elf_path.name}' to '{package_name}/{elf_type}/{elf_path.name}'")

        # 拷贝依赖
        if required_deps:
            lib_dir = package_dir / "lib"
            lib_dir.mkdir(exist_ok=True)

            for dep in required_deps:
                shutil.copy2(dep.path, lib_dir / dep.name)
                print(f"pack '{dep.name}' to '{package_name}/lib/{dep.name}'")

        with tarfile.open(archive_path, "w:gz") as tar:
            tar.add(package_dir, arcname=package_name)

if __name__ == "__main__":
    main()
