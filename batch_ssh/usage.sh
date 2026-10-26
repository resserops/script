#!/usr/bin/env bash
# per-process cpu time snapshots, used by the top cpu-hungry process stats at the end
cpu_per_proc_0=$(mktemp); cpu_per_proc_1=$(mktemp)
trap 'rm -f "$cpu_per_proc_0" "$cpu_per_proc_1"' EXIT

# dump "pid\tcpu_ticks\tcmd" for all processes into the given file
stat_re='^([0-9]+) \((.*)\) (.*)$'
snap_proc_cpu() {
    local p buf cpu_used_0
    for p in /proc/[0-9]*; do
        read -r buf 2>/dev/null < "$p/stat" || continue
        [[ $buf =~ $stat_re ]] || continue

        set -- ${BASH_REMATCH[3]}
        [ $# -ge 13 ] || continue
        cpu_used_0=$(( ${12} + ${13} ))

        set -- ${BASH_REMATCH[2]//[[:space:]]/ }
        printf '%s\t%s\t%s\n' "${BASH_REMATCH[1]}" "$cpu_used_0" "$*"
    done > "$1"
}

# cpu usage (average over 1s)
set -- $(head -n 1 /proc/stat)
cpu_total_0=$(( ${2:-0} + ${3:-0} + ${4:-0} + ${5:-0} + ${6:-0} + ${7:-0} + ${8:-0} + ${9:-0} ))
cpu_avail_0=$(( ${5:-0} + ${6:-0} ))
snap_proc_cpu "$cpu_per_proc_0"

sleep 1
set -- $(head -n 1 /proc/stat)
cpu_total_1=$(( ${2:-0} + ${3:-0} + ${4:-0} + ${5:-0} + ${6:-0} + ${7:-0} + ${8:-0} + ${9:-0} ))
cpu_avail_1=$(( ${5:-0} + ${6:-0} ))
snap_proc_cpu "$cpu_per_proc_1"

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
read -r load1 load5 load15 _ < /proc/loadavg

# top 5 cpu-hungry processes
cpu_count=$(grep -c '^cpu[0-9]' /proc/stat)
top=$(awk -F'\t' -v cpu_count="$cpu_count" -v cpu_total="$cpu_total" -v threshold=20 '
    NR==FNR {
        cpu_used_0[$1] = $2
        next
    }
    ($1 in cpu_used_0) {
        cpu_used = $2 - cpu_used_0[$1]
        if (cpu_used <= 0 || cpu_total <= 0) next
        sum[$3] += 100 * cpu_used * cpu_count / cpu_total
    }
    END { for (cmd in sum) if (sum[cmd] >= threshold) printf "%d\t%s\n", sum[cmd], cmd }
' "$cpu_per_proc_0" "$cpu_per_proc_1" \
    | sort -rn | head -5 \
    | awk -F'\t' '{ printf "%s%s", sep, $2; sep=", " }')

[ -n "$top" ] || top="-"

printf "cpu: %6s%% | mem: %6s%% | load: %6s, %6s, %6s | top: %s\n" \
    "$cpu" "$mem" "$load1" "$load5" "$load15" "$top"
