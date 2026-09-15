#!/usr/bin/env bash
# cpu usage (average over 1s)
set -- $(head -n 1 /proc/stat)
cpu_total_0=$(( ${2:-0} + ${3:-0} + ${4:-0} + ${5:-0} + ${6:-0} + ${7:-0} + ${8:-0} + ${9:-0} ))
cpu_avail_0=$(( ${5:-0} + ${6:-0} ))

sleep 1
set -- $(head -n 1 /proc/stat)
cpu_total_1=$(( ${2:-0} + ${3:-0} + ${4:-0} + ${5:-0} + ${6:-0} + ${7:-0} + ${8:-0} + ${9:-0} ))
cpu_avail_1=$(( ${5:-0} + ${6:-0} ))

cpu_total=$(( cpu_total_1 - cpu_total_0 ))
cpu_avail=$(( cpu_avail_1 - cpu_avail_0 ))
if [ "$cpu_total" -le 0 ]; then
    exit 1
fi
cpu=$(printf "%.2f" "$(( 100000 * (cpu_total - cpu_avail) / cpu_total ))e-3")

# memory usage
mem_total=$(grep -m1 MemTotal /proc/meminfo | tr -dc 0-9)
mem_avail=$(grep -m1 MemAvailable /proc/meminfo | tr -dc 0-9)
if [ -z "$mem_avail" ]; then
    mem_avail=$(grep -m1 MemFree /proc/meminfo | tr -dc 0-9)
fi

mem_total=${mem_total:-0}
mem_avail=${mem_avail:-0}
if [ "$mem_total" -le 0 ]; then
    exit 1
fi
mem=$(printf "%.2f" "$(( 100000 * (mem_total - mem_avail) / mem_total ))e-3")

# load average
load=$(cut -d" " -f1-3 /proc/loadavg | sed "s/ /, /g")

printf "cpu: %6s%% | mem: %6s%% | load: %s\n" "$cpu" "$mem" "$load"
