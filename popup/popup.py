#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import os
import sys
import subprocess
import platform
import shutil
import time
from pathlib import Path

# 基础信息
script_path = Path(sys.argv[0]).resolve()

def get_term_path(term):
    if os.sep not in term:  # 传入的term是命令
        # 本地是否存在该命令
        local_term_path = script_path.parent / term
        if local_term_path.is_file() and os.access(local_term_path, os.X_OK):
            return local_term_path.resolve()
        
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
    proc_list = []
    for i in range(num):
        try:
            # stdout/stderr重定向到DEVNULL避免阻塞父进程管道
            proc = subprocess.Popen([term], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL, start_new_session=True)
            proc_list.append(proc)
        except Exception as e:
            print(f'error: failed to launch terminal "{term.name}" #{i + 1}. exception: {e}', file=sys.stderr)

    if len(proc_list) == 0:
        return 0
    
    # 等待小段间隔后检测进程是否存活
    time.sleep(1) 
    
    launched_num = 0
    for i, proc in enumerate(proc_list):
        return_code = proc.poll()
        if return_code is None:
            # 进程还未终止
            launched_num += 1
        else:
            print(f'error: terminal "{term.name}" #{i + 1} exited unexpectedly. code: {return_code}', file=sys.stderr)

    return launched_num

def main():
    print(f"script: {script_path.name}")
    print(f"script path: {script_path}")
    print(f"current dir: {os.getcwd()}\n")

    # 解析入参
    parser = argparse.ArgumentParser(description="launch a remote terminal based on DISPLAY")
    parser.add_argument("--term", "-t", type=str, default="xterm", help="terminal command or path")
    parser.add_argument("--num", "-n", type=int, default=1, help="the number of launch terminals")
    parser.add_argument("--display", "-d", default=os.environ.get("DISPLAY"), help="target DISPLAY")
    args = parser.parse_args()

    if args.display is None:
        print(f"error: DISPLAY is none", file=sys.stderr)
        sys.exit(1)

    # 查找term
    term = get_term_path(args.term)
    if term is None:
        print(f'error: term "{args.term}" not found', file=sys.stderr)
        sys.exit(1)

    # 弹窗
    launched_num = launch_independent_term(term, args.num, args.display)
    print(f"successfully launched {launched_num}/{args.num} terminal(s) on DISPLAY {args.display}")

if __name__ == "__main__":
    main()
