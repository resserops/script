#!/usr/bin/env python3
import argparse
import os
import sys
import subprocess
import platform
import tarfile
import shutil
from pathlib import Path

# 基础信息
script_path = Path(sys.argv[0]).resolve()

def get_architecture():
    arch = platform.machine().lower()
    if arch in ("x86_64", "amd64"):
        return "x86_64"
    if arch in ("aarch64", "arm64"):
        return "aarch64"
    return "unknown"

def get_term_path(term):
    if os.sep not in term:  # 传入的term是命令
        # 本地是否存在该命令
        def check_local(term):
            local_term_path = script_path.parent / term
            if local_term_path.is_file() and os.access(local_term_path, os.X_OK):
                return local_term_path.resolve()
            return None
            
        arch = get_architecture()
        if (res := check_local(term)):
            return res
        if (res := check_local(f"{term}-{arch}")):
            return res
        
        # 本地是否存在该命令压缩包
        tar_path = script_path.parent / f"{term}-{arch}.tar.gz"
        if tar_path.is_file():
            try:
                with tarfile.open(tar_path, "r:gz") as tar:
                    tar.extractall(script_path.parent, filter="data")
            except Exception as e:
                print(f'warning: failed to extract local archive "{tar_path.name}". exception: {e}')
            else:
                if (res := check_local(term)):
                    return res
                if (res := check_local(f"{term}-{arch}")):
                    return res
        
        # 本地无法找到，检查系统PATH
        which_path = shutil.which(term)
        if which_path is not None:
            return Path(which_path).resolve()
        
    # 如果term包含路径分隔符，或系统PATH中也无法找到，将其视为绝对/相对路径
    term_path = Path(term)
    if term_path.is_file() and os.access(term_path, os.X_OK):
        return term_path.resolve()
    
    return None

def launch_independent_term(term, num, display=None):
    env = os.environ.copy()
    env["DISPLAY"] = display

    # 循环启动指定数量的终端
    launched_num = 0
    for _ in range(num):
        try:
            # stdout/stderr重定向到DEVNULL避免阻塞父进程管道
            subprocess.Popen([term], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL, start_new_session=True)
        except Exception as e:
            print(f'error: failed to launch terminal "{term.name}". exception: {e}')
        else:
            launched_num += 1
    return launched_num

def main():
    print(f"script: {script_path.name}")
    print(f"script path: {script_path}")
    print(f"current dir: {os.getcwd()}\n")

    # 解析入参
    parser = argparse.ArgumentParser(description="launch a remote terminal based on DISPLAY")
    parser.add_argument("--term", "-t", type=str, default="alacritty", help="terminal command or path")
    parser.add_argument("--num", "-n", type=int, default=1, help="the number of launch terminals")
    parser.add_argument("--display", "-d", default=os.environ.get("DISPLAY"), help="target DISPLAY")
    args = parser.parse_args()

    if args.display is None:
        print(f"error: DISPLAY is none")
        sys.exit(1)

    # 查找term
    term = get_term_path(args.term)
    if term is None:
        print(f"error: term {args.term} not found")
        sys.exit(1)

    # 弹窗
    launched_num = launch_independent_term(term, args.num, args.display)
    print(f"successfully launched {launched_num}/{args.num} terminal(s) on DISPLAY {args.display}")

if __name__ == "__main__":
    main()
