#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gantt.py — Gantt chart for program task timing analysis

Input format (see input.txt in the same directory):
    timestamp: <YYYY-mm-dd HH:MM:SS.ffffff>

    gantt results:
    #, begin, duration, <tag1>, <tag2>, ...
    <worker>, <begin>, <duration>, <tag1 value>, <tag2 value>, ...

  - worker (the # column) is a string deciding which row the task is drawn on;
  - begin / duration are seconds relative to timestamp (float);
  - remaining columns are custom tags, rendered onto bars via --label format string.

Usage examples:
    python3 gantt.py input.txt
    python3 gantt.py input.txt -o result.png --label '{task} ({duration}s)'
    python3 gantt.py input.txt --color-by task --label '{task}'

Placeholders available in the --label format string:
  {tag_name}     tag names defined in the header, e.g. {task}, {size}
  {c<N>} / {N}   raw CSV column index (0=worker, 1=begin, 2=duration, tags from 3)
  {worker} {begin} {duration} {end}   built-in fields
"""
import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import matplotlib
# 使用Anti-Grain Geometry图像渲染后端，避免在无GUI环境运行时出现错误
matplotlib.use("Agg")
import matplotlib.colors
import matplotlib.pyplot as plt

# 全局配置
BASE_COLORMAP = "Set3"  # 基础配色方案（matplotlib定性色条）
ALT_LIGHTEN = 0.35      # 交替明度提升参数，控制同一行相邻任务深浅差异
FIG_W = 16.0            # 输出图像宽度，单位：英寸
FIG_ASPECT = 9 / 16     # 默认高度:宽度
BASE_ROWS = 32          # 基准行数：不超过时维持默认比例，超过后保持每行高度按比例增高

# 由BASE_COLORMAP锚点插值构建连续渐变COLORMAP
COLORMAP = matplotlib.colors.LinearSegmentedColormap.from_list(
    "gradient", matplotlib.colormaps[BASE_COLORMAP].colors)


# 公共函数
# 从COLORMAP上均匀采样n个颜色
def sample_colors(n):
    if n <= 1:
        return [COLORMAP(0.5)]
    return [COLORMAP(i / (n - 1)) for i in range(n)]


# 提升颜色rgb明度，amount表示向白色混合的百分比，取值为0-1
def lighten(rgb, amount):
    """向白色混合 amount，略微提高明度。"""
    return tuple(c + (1 - c) * amount for c in rgb[:3])


# 自然排序：划分数字和文本段，每段逐次比较，数字段优先文本段，数字段按数值排序，文本段按字典序排序
def natural_key(s):
    return [(0, int(p)) if p.isdigit() else (1, p) for p in re.split(r"(\d+)", s) if p]


@dataclass(frozen=True)
class Task:
    worker: str
    begin: float
    duration: float
    tags: tuple


@dataclass(frozen=True)
class GanttData:
    """输入文件解析结果。

    meta: 头部 key: value（如 timestamp）
    columns: tag 列名（无表头时为 c3/c4/... 形式的兜底命名）
    tasks: 解析出的任务列表
    """
    meta: dict
    columns: tuple
    tasks: tuple


# ---------------------------------------------------------------- 解析输入

def _warn(lineno, reason, raw):
    print(f"warning: line {lineno} {reason}, skipped: {raw!r}", file=sys.stderr)


def _parse_row(fields, lineno, raw):
    """解析一条数据行为 Task，字段不足或数值非法时告警并返回 None。"""
    if len(fields) < 3:
        _warn(lineno, "has too few fields", raw)
        return None
    try:
        begin, duration = float(fields[1]), float(fields[2])
    except ValueError:
        _warn(lineno, "begin/duration not numeric", raw)
        return None
    return Task(fields[0], begin, duration, tuple(fields[3:]))


def parse_input(path):
    """Parse the input file, returning a GanttData."""
    meta, columns, tasks = {}, [], []
    in_results = False
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        if not in_results:
            if line == "gantt results:":
                in_results = True
            else:
                key, sep, value = line.partition(":")
                if sep:
                    meta[key.strip()] = value.strip()
            continue
        fields = [f.strip() for f in line.split(",")]
        if not columns:
            # 表头行：第二列为 begin 则认为是表头，否则首行即数据，tag 按列号命名
            if len(fields) >= 3 and fields[1].lower() == "begin":
                columns = fields[3:]
                continue
            columns = [f"c{3 + i}" for i in range(max(len(fields) - 3, 0))]
        task = _parse_row(fields, lineno, raw)
        if task:
            tasks.append(task)
    # 统一 tag 数量与列数一致
    if columns:
        tasks = [Task(t.worker, t.begin, t.duration,
                      (t.tags + ("",) * len(columns))[: len(columns)]) for t in tasks]
    return GanttData(meta, tuple(columns), tuple(tasks))


# ---------------------------------------------------------------- 统计与校验

def print_stats(tasks):
    """打印所有任务耗时总和，以及总耗时最长/最短的 worker。"""
    total = sum(t.duration for t in tasks)
    per_worker = {}
    for t in tasks:
        per_worker[t.worker] = per_worker.get(t.worker, 0.0) + t.duration
    longest = max(per_worker.items(), key=lambda kv: kv[1])
    shortest = min(per_worker.items(), key=lambda kv: kv[1])
    print(f"total duration: {fmt_num(total)}s")
    print(f"longest worker: {longest[0]} ({fmt_num(longest[1])}s), "
          f"shortest worker: {shortest[0]} ({fmt_num(shortest[1])}s)")


def check_overlaps(tasks):
    """同一 worker 的任务在时序上重叠时输出 warning。"""
    by_worker = {}
    for t in tasks:
        by_worker.setdefault(t.worker, []).append(t)
    for worker, ws in by_worker.items():
        ws.sort(key=lambda t: t.begin)
        cur = None  # 目前结束时间最晚的任务
        for t in ws:
            if cur is not None and t.begin < cur.begin + cur.duration:
                print(f"warning: worker '{worker}' tasks overlap: "
                      f"[{fmt_num(cur.begin)}, {fmt_num(cur.begin + cur.duration)}) "
                      f"and [{fmt_num(t.begin)}, {fmt_num(t.begin + t.duration)})",
                      file=sys.stderr)
            if cur is None or t.begin + t.duration > cur.begin + cur.duration:
                cur = t


def fmt_num(value):
    return f"{value:.6g}"


def make_label(fmt, task, columns):
    """Render the --label format string onto a bar. Unknown placeholders become empty."""
    ctx = {f"c{i + 3}": tag for i, tag in enumerate(task.tags)}
    for i, name in enumerate(columns):
        ctx[name] = task.tags[i] if i < len(task.tags) else ""
    ctx.update(
        c0=task.worker, c1=fmt_num(task.begin), c2=fmt_num(task.duration),
        worker=task.worker, begin=fmt_num(task.begin),
        duration=fmt_num(task.duration), end=fmt_num(task.begin + task.duration),
    )

    class _Ctx(dict):
        def __missing__(self, key):
            return ""

    # {N} 等价于 {cN}
    return re.sub(r"\{(\d+)\}", r"{c\1}", fmt).format_map(_Ctx(ctx))


def resolve_column(name, columns):
    """Resolve the --color-by argument to a raw CSV column index; None if unresolvable."""
    if name in columns:
        return 3 + columns.index(name)
    if name in ("worker", "begin", "duration"):
        return ("worker", "begin", "duration").index(name)
    m = re.fullmatch(r"c?(\d+)", name)
    return int(m.group(1)) if m else None


def field_at(task, col_idx):
    if col_idx == 0:
        return task.worker
    if col_idx == 1:
        return fmt_num(task.begin)
    if col_idx == 2:
        return fmt_num(task.duration)
    return task.tags[col_idx - 3] if col_idx - 3 < len(task.tags) else ""


# ---------------------------------------------------------------- 绘图

def render(data, args):
    meta, columns, tasks = data.meta, data.columns, data.tasks
    # 行排序方式：natural / lex / appearance
    if args.sort == "lex":
        workers = sorted({t.worker for t in tasks})
    elif args.sort == "appearance":
        workers = list(dict.fromkeys(t.worker for t in tasks))
    else:
        workers = sorted({t.worker for t in tasks}, key=natural_key)
    row_of = {w: i for i, w in enumerate(workers)}

    # --color-by：按列值从彩虹 colorbar 均匀采样分类色
    # 默认按 worker 着色，同一 worker 内相邻任务交替深浅，避免连在一起的段看不清
    has_legend = False
    legend_items = []
    if args.color_by:
        col_idx = resolve_column(args.color_by, columns)
        if col_idx is None:
            print(f"error: cannot resolve --color-by column '{args.color_by}', "
                  f"available: {', '.join(columns) or '(no tag columns)'}", file=sys.stderr)
            sys.exit(1)
        values = list(dict.fromkeys(field_at(t, col_idx) for t in tasks))
        value_color = dict(zip(values, sample_colors(len(values))))
        task_color = {id(t): value_color[field_at(t, col_idx)] for t in tasks}
        legend_items = list(value_color.items())
        has_legend = len(legend_items) >= 2
    else:
        worker_color = dict(zip(workers, sample_colors(len(workers))))
        seq = {}
        task_color = {}
        for t in tasks:
            i = seq.get(t.worker, 0)
            task_color[id(t)] = (worker_color[t.worker] if i % 2 == 0
                                 else lighten(worker_color[t.worker], ALT_LIGHTEN))
            # 宽度接近零的任务不参与同行颜色 toggle
            if t.duration > 0:
                seq[t.worker] = i + 1

    # 默认 16:9；行数超过 BASE_ROWS 时保持每行高度不变，按比例增大图高
    fig_h = FIG_W * FIG_ASPECT * max(1.0, len(workers) / BASE_ROWS)
    fig, ax = plt.subplots(figsize=(FIG_W, fig_h))
    labels = []
    for t in tasks:
        y = row_of[t.worker]
        ax.broken_barh([(t.begin, max(t.duration, 1e-9))], (y - 0.5, 1.0),
                       facecolors=task_color[id(t)], edgecolor="none")
        if args.label:
            artist = ax.text(t.begin + t.duration / 2, y,
                             make_label(args.label, t, columns),
                             ha="center", va="center", fontsize=8)
            labels.append((artist, t.begin, t.begin + t.duration))

    # label 文字宽度超过任务 bar 宽度则不显示
    if labels:
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        for artist, x0, x1 in labels:
            bar_px = abs(ax.transData.transform((x1, 0))[0]
                         - ax.transData.transform((x0, 0))[0])
            if artist.get_window_extent(renderer).width > bar_px:
                artist.remove()

    ax.set_ylim(len(workers) - 0.5, -0.5)  # 首个 worker 在最上方
    ax.margins(x=0)  # 横坐标左右两端不留空隙
    # 横坐标从 0（或最早任务的负时刻）开始，不跟随最早任务边界
    ax.set_xlim(left=min(0.0, min((t.begin for t in tasks), default=0.0)))
    ax.set_yticks(range(len(workers)))
    ax.set_yticklabels(workers)
    ax.tick_params(axis="y", length=0)
    ax.grid(axis="x", linewidth=0.8, alpha=0.5)
    ax.set_axisbelow(True)
    ax.set_xlabel("time (s)")

    title = args.title or "Gantt Chart"
    sub = meta.get("timestamp")
    if sub:
        ax.set_title(f"{title}\n{sub}", fontsize=12)
    else:
        ax.set_title(title, fontsize=12)
    if has_legend:
        ax.legend(handles=[plt.Rectangle((0, 0), 1, 1, color=c, label=v)
                           for v, c in legend_items],
                  loc="lower left", bbox_to_anchor=(0, 1.02), ncol=8,
                  frameon=False, fontsize=9)

    fig.savefig(args.output, bbox_inches="tight")


# ---------------------------------------------------------------- CLI

def main():
    parser = argparse.ArgumentParser(
        description="Draw a Gantt chart from program task timing data "
                    "(input format see input.txt)")
    parser.add_argument("input", help="input file path")
    parser.add_argument("-o", "--output", help="output image path, default <input>.png")
    parser.add_argument("--label",
                        help="format string for bar labels, e.g. '{task} ({duration}s)', "
                             "see module docstring")
    parser.add_argument("--color-by",
                        help="color bars by this column (tag name or index like c3), "
                             "default single color")
    parser.add_argument("--title", help="custom title")
    parser.add_argument("--sort", choices=["natural", "lex", "appearance"],
                        default="natural",
                        help="worker row order: natural (Windows-style, default), "
                             "lex (lexicographic), appearance (first-seen order)")
    args = parser.parse_args()

    path = Path(args.input)
    if not path.is_file():
        print(f"error: input path '{args.input}' does not exist or is not a file",
              file=sys.stderr)
        sys.exit(1)

    data = parse_input(path)

    if not data.tasks:
        print("error: no valid tasks parsed (missing 'gantt results:' section?)",
              file=sys.stderr)
        sys.exit(1)

    args.output = args.output or str(path.with_suffix(".png"))
    check_overlaps(data.tasks)
    render(data, args)
    print(f"gantt saved to {args.output}")
    print_stats(data.tasks)


if __name__ == "__main__":
    main()
