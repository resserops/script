#!/usr/bin/env bash
last_count=5  # 显示的用户数量
script_dir="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
exec python3 "$script_dir/batch_ssh.py" --shell bash "set -- $last_count; $(cat "$script_dir/last.sh")" "$@"
