#!/usr/bin/env bash
# last login time per user, sorted from newest to oldest
# usage: last.sh [count] (default: 5)
last -F -a 2>/dev/null | grep -vE '^(reboot|wtmp) |^$' | awk '!seen[$1]++' | head -n "${1:-5}" | while read -r user tty w m d time y rest; do
    date=$(date -d "$w $m $d $time $y" +"%Y-%m-%d %H:%M:%S")
    ip=$(printf "%s\n" "$rest" | awk '{print $NF}')
    online=""; printf "%s\n" "$rest" | grep -q "still logged in" && online="*"
    printf "%-12s %-8s %-16s %s\n" "$user$online" "$tty" "$ip" "$date"
done
