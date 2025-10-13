#! /usr/bin/env bash

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

function git_branch() {
    git branch --no-color 2> /dev/null | sed -e '/^[^*]/d' -e "s/* \(.*\)/[\1$(git_dirty)]/"
}

export PS1='[\u@$(hostname) \[\e[01;33m\]\w\[\e[0m\]]\[\e[01;32m\]$(git_branch)\[\e[0m\]\$ '
