#!/bin/sh

# Usage:
#   ./extract-git-commits.sh ~/.bash_history
#
# Creates:
#   /tmp/bash_history.clean
#   /tmp/git-commits.txt
#
# Never modifies the input file.

awk '
function unescaped_quotes(s,    i,j,n,bs) {
    n = 0

    for (i = 1; i <= length(s); i++) {
        if (substr(s,i,1) != "\"")
            continue

        bs = 0
        for (j = i - 1; j >= 1 && substr(s,j,1) == "\\"; j--)
            bs++

        if ((bs % 2) == 0)
            n++
    }

    return n
}

function commit_start(s) {
    # Normal git commit commands.
    if (s ~ /^[[:space:]]*git[[:space:]]+commit([[:space:]]|$)/)
        return 1

    # Malformed attempts seen in the history:
    #   git -am "..."
    #   git -am commit "..."
    if (s ~ /^[[:space:]]*git[[:space:]]+-am([[:space:]]|$)/)
        return 1

    return 0
}

function command_start(s) {
    # Used only to recover from an unterminated quoted commit entry.
    # Deliberately restricted to things that strongly resemble commands.
    return s ~ /^[[:space:]]*(git|patch|echo|cat|cp|mv|rm|ln|cd|pwd|ls|grep|sed|awk|find|make|cmake|ninja|qmake|python|python3|perl|ruby|sudo|dnf|rpm|curl|wget|tar|unzip|zip|chmod|chown|touch|diff|head|tail|less|vim|nano|ssh|scp|rsync|systemctl|journalctl|docker|podman|meson|gcc|g\+\+|clang|clang\+\+|\.\/|\/)[[:space:];&|<>()]/
}

BEGIN {
    clean   = "/tmp/bash_history.clean"
    commits = "/tmp/git-commits.txt"

    # Truncate outputs.
    printf "%s", "" > clean
    close(clean)

    printf "%s", "" > commits
    close(commits)

    in_commit = 0
    q = 0
}

{
    line = $0

    if (!in_commit) {
        if (commit_start(line)) {
            print line >> commits

            q = unescaped_quotes(line)

            if (q % 2)
                in_commit = 1
            else
                print "" >> commits

            next
        }

        print line >> clean
        next
    }

    # We are inside a multiline quoted git commit command.
    #
    # If its quote was never closed but the next physical line very
    # clearly starts another shell command, treat the previous history
    # entry as malformed/truncated and process this line normally.
    if ((q % 2) && command_start(line)) {
        print "" >> commits

        in_commit = 0
        q = 0

        if (commit_start(line)) {
            print line >> commits
            q = unescaped_quotes(line)

            if (q % 2)
                in_commit = 1
            else
                print "" >> commits
        } else {
            print line >> clean
        }

        next
    }

    print line >> commits
    q += unescaped_quotes(line)

    if ((q % 2) == 0) {
        print "" >> commits
        in_commit = 0
        q = 0
    }
}

END {
    if (in_commit)
        print "WARNING: unterminated git commit at EOF" > "/dev/stderr"
}
' "$1"

printf 'Created:\n'
wc -l /tmp/bash_history.clean /tmp/git-commits.txt
