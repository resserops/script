#! /usr/bin/env bash

# 脚本仅在交互式环境中生效
[[ $- == *i* ]] || return

COLOR_YELLOW_BOLD='\e[01;33m'
COLOR_GREEN_BOLD='\e[01;32m'
COLOR_RESET='\e[0m'

# 获取git当前分支修改状态，暂存区有修改显示'*'，工作区有新增文件显示'+'
function git_dirty() {
    git_status=$(git status 2> /dev/null | tail -n1)
    if [[ ${git_status:0:17} == "nothing to commit" ]]; then
        :
    elif [[ ${git_status:0:23} == "nothing added to commit" ]]; then
        printf "+"
    else
        printf "*"
    fi
}

# 获取git当前分支名称
function git_branch() {
    git branch --no-color 2> /dev/null | sed -e '/^[^*]/d' -e "s/* \(.*\)/[\1$(git_dirty)]/"
}

# 颜色包装函数，$1：颜色编码；$2：字符串
function color() {
    printf '\[%s\]%s\[%s\]' "$1" "$2" ${COLOR_RESET}
}

export PS1="[\u@$(hostname) $(color ${COLOR_YELLOW_BOLD} '\w')]$(color ${COLOR_GREEN_BOLD} '$(git_branch)')\$ "
