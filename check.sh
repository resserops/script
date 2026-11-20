#!/usr/bin/env bash
cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" || exit 1

# $1: command; returns 0 if found in PATH, otherwise prints error and returns 1
exist() {
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "error: command $1 not found in PATH" >&2
        return 1
    fi
}

# $1: command; outputs the first dot-containing token as version, empty on failure
# shellcheck disable=SC2317
version_of() { "$1" --version 2>/dev/null | tr -s '[:space:]' '\n' | grep -m1 '\.'; }

# $1: command, $2: expected version, $3: version extractor (default: version_of)
# returns 0 on match, otherwise prints error and returns 1
require() {
    local version
    version=$("${3:-version_of}" "$1")
    if [ "$version" != "$2" ]; then
        echo "error: $1 version '$version' != expected '$2'" >&2
        return 1
    fi
}

# $1: glob pattern; outputs NUL-separated tracked and untracked files matching it
git_ls() { git ls-files --cached --others --exclude-standard -z "$1"; }

rc=0

# check python format & lint
if exist ruff; then
    require ruff 0.17.2 || rc=1
    git_ls '*.py' | xargs -0 -r ruff format -q || rc=1
    git_ls '*.py' | xargs -0 -r ruff check --fix -q || rc=1
else
    rc=1
fi

# check shell format & lint
if exist shfmt; then
    require shfmt v3.14.1 || rc=1
    git_ls '*.sh' | xargs -0 -r shfmt -w || rc=1
else
    rc=1
fi

if exist shellcheck; then
    require shellcheck 0.10.0 || rc=1
    git_ls '*.sh' | xargs -0 -r shellcheck || rc=1
else
    rc=1
fi

exit $rc
