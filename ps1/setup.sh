#! /usr/bin/env bash
set -e

SCRIPT_DIR=$(cd "$(dirname "$0")" || exit 1; pwd)

mkdir -p ~/.bashrc.d
\cp -f "${SCRIPT_DIR}/ps1.sh" ~/.bashrc.d/

cat << 'EOF' >> ~/.bashrc
if [ -f ~/.bashrc.d/ps1.sh ]; then
    source ~/.bashrc.d/ps1.sh
fi
EOF

echo "To apply the changes, run: source ~/.bashrc"
