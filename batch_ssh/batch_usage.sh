#!/usr/bin/env bash
script_dir="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
exec python3 "$script_dir/batch_ssh.py" --shell bash "$(cat "$script_dir/usage.sh")" "$@"
