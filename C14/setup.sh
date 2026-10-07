#!/bin/sh
# Practice repositories for C14, Git and Team Development Essentials.
#
# Usage:   sh setup.sh <scenario> [--reset]
# Example: cd ~/projects && sh nextia-learning-labs/C14/setup.sh m03
#
# The script makes a folder called c14-lab in the current folder:
#
#   c14-lab/team-remote.git   the shared remote (a bare repository)
#   c14-lab/ticket-notes      your clone (you work here as Amira)
#   c14-lab/sam-notes         the clone of your teammate, Sam Okafor
#
# Scenarios for Modules 1 and 2 (only ticket-notes, until Module 2, lesson 2
# adds the remote and Sam's clone):
#   m01-l03  Module 1, lesson 3: an empty repository with no commits
#   m02-l01  Module 2, lesson 1: three commits on main
#   m02-l02  Module 2, lesson 2: main and the branch add-priorities, no remote
#   m02-l03  Module 2, lesson 3: the remote, Sam's clone and his first ticket
#
# Scenarios for Modules 3 to 5:
#   m03      Module 3: main, Sam's branch add-ticket-104 and the branch add-faq
#   m04      Module 4: a conflict is ready to happen, and Sam pushed a faulty commit
#   release  Module 5, lesson 1: main is ready for its first release
#   hotfix   Module 5, lessons 2 and 3: v1.0.0 is released and has a bug
#   final    The final assignment
#
# --reset deletes an existing c14-lab folder first. It deletes only a folder
# that this script made. Nothing outside c14-lab changes, and your global Git
# settings do not change.
#
# Every commit that the script makes has a fixed author and date, so its hash
# is the same as in the lessons. Tested on 2026-10-05 with Git 2.54 on macOS
# (sh and dash) and Alpine Linux (BusyBox sh): the hashes are the same on each.
# Not yet tested in Git Bash on Windows. Git 2.40 or later is required.
# The scenarios for Modules 1 and 2 were added on 2026-10-07 and tested on
# macOS only (sh and dash, Git 2.54).

set -eu

LAB=c14-lab
SCENARIO=${1:-}
RESET=${2:-}

usage() {
  echo "Usage: sh setup.sh <m01-l03|m02-l01|m02-l02|m02-l03|m03|m04|release|hotfix|final> [--reset]" >&2
  exit 2
}

case "$SCENARIO" in
  m01-l03 | m02-l01 | m02-l02 | m02-l03) ;;
  m03 | m04 | release | hotfix | final) ;;
  *) usage ;;
esac
case "$RESET" in
  '' | --reset) ;;
  *) usage ;;
esac

command -v git > /dev/null 2>&1 || { echo "Git is not installed. See the lesson 'Set up Git'." >&2; exit 1; }

if [ -e "$LAB" ]; then
  if [ "$RESET" != "--reset" ]; then
    echo "The folder $LAB already exists in $(pwd)." >&2
    echo "To delete it and start again, run the same command with --reset at the end." >&2
    exit 1
  fi
  if [ ! -f "$LAB/.c14-lab" ]; then
    echo "$LAB was not made by this script, so it was not deleted. Move or rename it, then try again." >&2
    exit 1
  fi
  rm -rf "$LAB"
fi

mkdir "$LAB"
echo "This folder was made by nextia-learning-labs/C14/setup.sh." > "$LAB/.c14-lab"
cd "$LAB"
ROOT=$(pwd)

# --- Helpers ---------------------------------------------------------------

# Fixed identities and dates: the same input gives the same commit hashes.
# Each commit is one minute after the one before it.
STEP=0
as() { # as <amira|sam> <command...>
  who=$1
  shift
  STEP=$((STEP + 1))
  minute=$(printf '%02d' $((STEP % 60)))
  hour=$((9 + STEP / 60))
  at "$who" "2026-10-06T$(printf '%02d' $hour):$minute:00-04:00" "$@"
}

at() { # at <amira|sam> <date> <command...>: the same, at a date that you give
  who=$1
  stamp=$2
  shift 2
  if [ "$who" = sam ]; then
    name="Sam Okafor" email="sam@example.com"
  else
    name="Amira Khan" email="amira@example.com"
  fi
  GIT_AUTHOR_NAME=$name GIT_AUTHOR_EMAIL=$email GIT_AUTHOR_DATE=$stamp \
    GIT_COMMITTER_NAME=$name GIT_COMMITTER_EMAIL=$email GIT_COMMITTER_DATE=$stamp \
    "$@"
}

# Git commands without the user's own settings (hooks, signing, templates).
g() { git -c core.hooksPath=/dev/null -c commit.gpgSign=false -c tag.gpgSign=false -c init.defaultBranch=main "$@"; }

commit() { # commit <amira|sam> <message>
  g add -A
  as "$1" g commit -q -m "$2"
}

# --- Modules 1 and 2: the repository that you make in the lessons ----------
#
# These scenarios make the state at the start of a lesson in Modules 1 and 2.
# The commits are the ones in the lessons, with the same hashes (763ec59,
# 49397ba, d8ae027 and 999a7c4). Sam's "Add ticket 102" in m02-l03 is the
# exception: in the lesson, the learner makes it, so its hash is different.
# The history is not the same as the shared start below, which Modules 3 to 5
# use.

lesson_commits() { # The three commits from "Track a first change".
  printf '# Ticket notes\n\nNotes about support tickets.\n' > README.md
  g add README.md
  at amira 2026-10-05T20:31:22-04:00 g commit -q -m "Add README"
  printf '# Ticket notes\n\nNotes about support tickets for the help desk.\n' > README.md
  g add README.md
  at amira 2026-10-05T20:31:31-04:00 g commit -q -m "Describe who the notes are for"
  printf 'Ticket 101: printer offline. Restarted the spooler.\n' > tickets.txt
  g add tickets.txt
  at amira 2026-10-05T20:31:31-04:00 g commit -q -m "Add first ticket note"
}

lesson_branch() { # The branch from "Branch basics". You end on main.
  g switch -q -c add-priorities
  printf 'Priority levels: low, normal, urgent.\n' > priorities.txt
  g add priorities.txt
  at amira 2026-10-06T10:00:00-04:00 g commit -q -m "Add priority levels"
  g switch -q main
}

lesson_remote() { # The guided practice of "Synchronize deliberately".
  g init -q --bare team-remote.git
  cd ticket-notes
  g remote add origin ../team-remote.git
  g config pull.ff only
  g push -q -u origin main
  g push -q -u origin add-priorities
  cd "$ROOT"
  g clone -q team-remote.git sam-notes
  g -C sam-notes config user.name "Sam Okafor"
  g -C sam-notes config user.email "sam@example.com"
  g -C sam-notes config pull.ff only
  g -C sam-notes config merge.conflictStyle zdiff3
  cd sam-notes
  printf 'Ticket 102: password reset email not received.\n' >> tickets.txt
  at sam 2026-10-06T10:05:00-04:00 g commit -q -am "Add ticket 102"
  g push -q
  cd "$ROOT/ticket-notes"
  g pull -q
  cd "$ROOT"
}

case "$SCENARIO" in
  m01-l03 | m02-l01 | m02-l02 | m02-l03)
    g init -q ticket-notes
    cd ticket-notes
    case "$SCENARIO" in m02-*) lesson_commits ;; esac
    case "$SCENARIO" in m02-l02 | m02-l03) lesson_branch ;; esac
    cd "$ROOT"
    if [ "$SCENARIO" = m02-l03 ]; then lesson_remote; fi
    echo "Ready: $ROOT"
    echo "  ticket-notes     your repository"
    if [ "$SCENARIO" = m02-l03 ]; then
      echo "  sam-notes        Sam's clone"
      echo "  team-remote.git  the shared remote"
    fi
    echo "Next: cd $LAB/ticket-notes"
    echo "To start this scenario again: sh $0 $SCENARIO --reset"
    exit 0
    ;;
esac

# --- Shared start: the history from Modules 1 and 2 -------------------------

g init -q --bare team-remote.git
g -C team-remote.git symbolic-ref HEAD refs/heads/main
g init -q seed
cd seed

printf '# Ticket notes\n\nNotes about support tickets for the help desk.\n' > README.md
commit amira "Add README"

printf 'Ticket 101: printer offline. Restarted the spooler.\n' > tickets.txt
commit amira "Add first ticket note"

printf 'Ticket 102: password reset email not received.\n' >> tickets.txt
commit sam "Add ticket 102"

printf 'Help desk: ext. 4100\nNetwork team: ext. 4410\nAccounts team: ext. 4300\n' > contacts.txt
commit amira "Add contacts"

printf '# Secrets: never commit them\n.env\n\n# Files that tools make\nexports/\n*.log\n' > .gitignore
commit amira "Ignore secrets, exports and logs"

cat > check.sh << 'EOF'
#!/bin/sh
# Checks the ticket notes. A team runs this before it merges a change.
# Rule: every line in tickets.txt starts with "Ticket <number>: ".
bad=$(grep -n -v -E '^Ticket [0-9]+: ' tickets.txt || true)
if [ -n "$bad" ]; then
  echo "FAIL: these lines in tickets.txt do not start with 'Ticket <number>: '"
  echo "$bad"
  exit 1
fi
echo "PASS: $(grep -c '' tickets.txt) ticket lines checked"
EOF
commit sam "Add a format check for ticket notes"

printf 'Ticket 103: shared drive is slow. Moved the user to the new server.\n' >> tickets.txt
commit amira "Add ticket 103"

BASE=$(g rev-parse HEAD)

# --- Scenarios -------------------------------------------------------------

scenario_m03() {
  # Sam's pull request branch, made from BASE. It has three problems for the
  # reviewer to find: a format error, an accidental file and an unrelated change.
  g switch -q -c add-ticket-104 "$BASE"
  printf 'ticket 104 - VPN drops every hour.\n' >> tickets.txt
  printf 'try restarting the VPN client?\nask Amira about logs\n' > scratch.txt
  commit sam "Add ticket 104"
  printf '# Ticket notes\n\nNotes about the support tickets that the help desk receives.\n' > README.md
  commit sam "Improve README wording"

  # Amira's branch for the merge-strategies lesson: two commits.
  g switch -q -c add-faq "$BASE"
  printf 'Q: How do I reset my password?\nA: Use the "Forgot password" link on the sign-in page.\n' > faq.txt
  commit amira "Add FAQ"
  printf 'Q: How do I reset my password?\nA: Use the "Forgot password" link on the sign-in page.\n\nQ: Who do I call about the network?\nA: The network team. See contacts.txt.\n' > faq.txt
  commit amira "Add a network question to the FAQ"

  # main moves on after both branches started.
  g switch -q main
  printf 'On-call engineer: 555-0100\n' >> contacts.txt
  commit sam "Add the on-call number"

  g push -q origin main add-ticket-104 add-faq
}

scenario_m04() {
  # Sam pushes a faulty commit, then a good one.
  printf 'Accounts team: ext. 4300\nHelp desk: ext. 4100\n' > contacts.txt
  commit sam "Sort contacts by name"
  printf 'Ticket 104: laptop will not charge. Replaced the power adapter.\n' >> tickets.txt
  commit sam "Add ticket 104"
  g push -q origin main
  SHARED=$(g rev-parse HEAD)

  # Sam then adds a cause to ticket 102 and pushes.
  sed 's/^Ticket 102: .*/Ticket 102: password reset email not received. The email was in the spam folder./' tickets.txt > tickets.tmp
  mv tickets.tmp tickets.txt
  commit sam "Add the cause of ticket 102"
  g push -q origin main

  # Amira's clone starts at SHARED, then she changes the same line (not pushed).
  AMIRA_AT=$SHARED
  AMIRA_COMMIT=yes
  amira_commit() {
    sed 's/^Ticket 102: .*/Ticket 102: password reset email not received. Sent a new reset link./' tickets.txt > tickets.tmp
    mv tickets.tmp tickets.txt
    commit amira "Add the action for ticket 102"
  }
}

scenario_release() {
  printf 'Ticket 104: laptop will not charge. Replaced the power adapter.\n' >> tickets.txt
  commit sam "Add ticket 104"
  printf 'Escalate a ticket when:\n- the user cannot work, or\n- the ticket is open for more than 2 days.\n' > escalation.txt
  commit amira "Add escalation rules"
  g push -q origin main
}

scenario_hotfix() {
  scenario_release
  # Release 1.0 is made from main and tagged.
  g switch -q -c release/1.0
  as amira g tag -a v1.0.0 -m "Help desk notes 1.0"
  g switch -q main
  # Work continues on main after the release.
  printf 'Export format: one CSV row for each ticket.\nTODO: decide the columns.\n' > export.txt
  commit amira "Start the ticket export (not finished)"
  sed 's/^Network team: ext. 4410/Network team: ext. 4401/' contacts.txt > contacts.tmp
  mv contacts.tmp contacts.txt
  commit sam "Fix the network team extension"
  printf 'Ticket 105: new starter has no email account. Created the account.\n' >> tickets.txt
  commit amira "Add ticket 105"
  g push -q origin main release/1.0 v1.0.0
}

scenario_final() {
  scenario_release
  g switch -q -c release/1.0
  as amira g tag -a v1.0.0 -m "Help desk notes 1.0"
  g switch -q main
  printf 'Export format: one CSV row for each ticket.\nTODO: decide the columns.\n' > export.txt
  commit amira "Start the ticket export (not finished)"
  # A faulty commit that is already shared: it deletes the Accounts team.
  printf 'Help desk: ext. 4100\nNetwork team: ext. 4410\n' > contacts.txt
  commit sam "Remove old contacts"
  printf 'Ticket 105: new starter has no email account. Created the account.\n' >> tickets.txt
  commit sam "Add ticket 105"
  g push -q origin main release/1.0 v1.0.0
  # Your clone starts here. Sam then changes ticket 103 and pushes; the
  # assignment asks you to change the same line.
  AMIRA_AT=$(g rev-parse HEAD)
  sed 's/^Ticket 103: .*/Ticket 103: shared drive is slow. Moved the user to the new server. Slow again on Monday./' tickets.txt > tickets.tmp
  mv tickets.tmp tickets.txt
  commit sam "Update ticket 103"
  g push -q origin main
}

AMIRA_AT=
AMIRA_COMMIT=
g remote add origin ../team-remote.git
g push -q origin main
"scenario_$SCENARIO"

cd "$ROOT"

# --- Clones -----------------------------------------------------------------

clone() { # clone <folder> <name> <email>
  g clone -q team-remote.git "$1"
  g -C "$1" config user.name "$2"
  g -C "$1" config user.email "$3"
  g -C "$1" config pull.ff only
  g -C "$1" config merge.conflictStyle zdiff3
}

clone sam-notes "Sam Okafor" "sam@example.com"
g clone -q team-remote.git ticket-notes
g -C ticket-notes config pull.ff only
g -C ticket-notes config merge.conflictStyle zdiff3

if [ -n "$AMIRA_AT" ]; then
  # Amira has not fetched Sam's last commit yet. In Module 4, she also has a
  # commit of her own that she has not pushed.
  g -C ticket-notes reset -q --hard "$AMIRA_AT"
  g -C ticket-notes update-ref refs/remotes/origin/main "$AMIRA_AT"
  if [ -n "$AMIRA_COMMIT" ]; then (cd ticket-notes && amira_commit); fi
fi

if [ "$SCENARIO" = m03 ]; then
  g -C ticket-notes branch -q --track add-faq origin/add-faq
fi

rm -rf seed

echo "Ready: $ROOT"
echo "  ticket-notes     your clone"
echo "  sam-notes        Sam's clone"
echo "  team-remote.git  the shared remote"
echo "Next: cd $LAB/ticket-notes"
echo "To start this scenario again: sh $0 $SCENARIO --reset"
