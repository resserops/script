#! /usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import os
import sys
import subprocess
import copy

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from ansi_escape import stylize, print

@dataclass
class Contrib:
    commits: int = 0
    insertions: int = 0
    deletions: int = 0

    @property
    def net_changes(self):
        return self.insertions - self.deletions
    
    def append(self, insertions, deletions):
        self.insertions += insertions
        self.deletions += deletions

    def __iadd__(self, other):
        self.commits += other.commits
        self.insertions += other.insertions
        self.deletions += other.deletions
        return self

def parse_args(): 
    parser = argparse.ArgumentParser(description="git contribution statistics tool")
    parser.add_argument("-s", "--since", type=str, help='start date for stats, e.g., "2026-01-01" or "2 weeks ago"')
    parser.add_argument("-u", "--until", type=str, help='end date for stats, e.g., "2026-06-30"')
    parser.add_argument("--max", type=int, help="max allowed insertions or deletions per commit to filter out migrations")
    return parser.parse_args()

def main():
    # 基础信息
    script_path = Path(__file__).resolve()
    prefix = "author:"
    
    print(f"cmd: {script_path.name} {' '.join(sys.argv[1:])}")
    print(f"exe: {script_path}")
    print(f"cwd: {os.getcwd()}\n")

    # 参数解析
    args = parse_args()
    
    # 执行numstat命令打印commits明细
    cmd = ["git", "--no-pager", "log", "--numstat", rf"--pretty=tformat:{prefix}%aN", "--no-merges"]
    if args.since:
        cmd.append(f"--since={args.since}")
    if args.until:
        cmd.append(f"--until={args.until}")

    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True, encoding="utf-8")
    except subprocess.CalledProcessError as e:
        print(f"error: failed to run git command. please ensure the current directory is a valid git repository", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print("error: git command not found. please install git.", file=sys.stderr)
        sys.exit(1)

    # 统计命令输出
    stats = defaultdict(Contrib)
    filtered = defaultdict(Contrib)

    def add_contrib(author, contrib):
        if args.max is not None and contrib.insertions > args.max:
            filtered[author] += contrib
        else:
            stats[author] += contrib

    author = None
    for line in res.stdout.splitlines():
        line = line.strip()
        if not line:
            continue

        if line.startswith(prefix):
            if author:
                add_contrib(author, contrib)
            author = line[len(prefix):]
            contrib = Contrib(1)
        else:
            tokens = line.split(maxsplit=2)
            assert(len(tokens) >= 2)
            contrib.append(int(tokens[0]), int(tokens[1]))                
                
    if author:
        add_contrib(author, contrib)

    stats = sorted(stats.items(), key=lambda x: x[0])
    filtered = sorted(filtered.items(), key=lambda x: x[0])

    # 打印统计内容
    @dataclass
    class TableWidth:
        author: int = 0
        commits: int = 0
        insertions: int = 0
        deletions: int = 0
        net_changes: int = 0

        def append(self, author, commits, insertions, deletions, net_changes):
            self.author = max(self.author, author)
            self.commits = max(self.commits, commits)
            self.insertions = max(self.insertions, insertions)
            self.deletions = max(self.deletions, deletions)
            self.net_changes = max(self.net_changes, net_changes)
            return self
    
    def auto_fit_width(stats, w: TableWidth):
        for author, contrib in stats:
            w.append(len(author), len(str(contrib.commits)), len(str(contrib.insertions)) + 2, len(str(contrib.deletions)) + 2, len(str(contrib.net_changes)) + 5)

    w_text = TableWidth()
    auto_fit_width(stats, w_text)
    auto_fit_width(filtered, w_text)

    w_cell = copy.copy(w_text)
    w_cell.append(6, 8, 10, 10, 10)   # 默认的最小cell尺寸

    def print_data_line_impl(commits, insertions, deletions, net_changes):
        print(" " * (w_cell.commits - len(str(commits))), str(commits), sep="", end="  ")
        print(" " * (w_cell.insertions - w_text.insertions), stylize("+").green(True).bold(), " " * (w_text.insertions - len(str(insertions)) - 1), str(insertions), sep="", end="  ")
        print(" " * (w_cell.deletions - w_text.deletions), stylize("-").red(True).bold(), " " * (w_text.deletions - len(str(deletions)) - 1), str(deletions), sep="", end="  ")
        net_prefix = stylize("net+").green(True).bold() if net_changes >= 0 else stylize("net-").red(True).bold()
        print(" " * (w_cell.net_changes - w_text.net_changes), net_prefix, " " * (w_text.net_changes - len(str(abs(net_changes))) - 4), str(net_changes), sep="")

    def print_data_line(author, commits, insertions, deletions, net_changes):
        print(author, " " * (w_cell.author - len(author)), sep="", end="  ")
        print_data_line_impl(commits, insertions, deletions, net_changes)

    def print_sum_line(commits, insertions, deletions, net_changes):
        print(stylize("sum").white(True).bold(), " " * (w_cell.author - 3), sep="", end="  ")
        print_data_line_impl(commits, insertions, deletions, net_changes)

    def print_stats(stats):
        # 打印表头
        print("author", " " * (w_cell.author - 6), sep="", end="  ")
        print(" " * (w_cell.commits - 7), "commits", sep="", end="  ")
        print(" " * (w_cell.insertions - 10), "insertions", sep="", end="  ")
        print(" " * (w_cell.deletions - 9), "deletions", sep="", end="  ")
        print(" " * (w_cell.net_changes - 7), "changes", sep="")

        sum = Contrib()
        for author, contrib in stats:
            print_data_line(author, contrib.commits, contrib.insertions, contrib.deletions, contrib.net_changes)
            sum += contrib
        print_sum_line(sum.commits, sum.insertions, sum.deletions, sum.net_changes)
    
    if stats:
        print(stylize("[contrib]").white(True).bold())
        print_stats(stats)
    
    if filtered:
        if stats:
            print()
        print(stylize("[filterd]").white(True).bold())
        print_stats(filtered)

if __name__ == "__main__":
    main()
