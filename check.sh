#!/usr/bin/env bash
cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" || exit 1
rc=0

git_ls_py() { git ls-files --cached --others --exclude-standard -z '*.py'; }
git_ls_py | xargs -0 -r ruff format -q || rc=1
git_ls_py | xargs -0 -r ruff check --fix -q || rc=1

git_ls_sh() { git ls-files --cached --others --exclude-standard -z '*.sh'; }
git_ls_sh | xargs -0 -r shfmt -w || rc=1
git_ls_sh | xargs -0 -r shellcheck || rc=1

exit $rc
