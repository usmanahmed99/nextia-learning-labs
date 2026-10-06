# C14: Git and Team Development Essentials

Practice repositories for Modules 3 to 5 and the final assignment of [Git and Team Development Essentials](https://learning.nextia-ai.com/courses/git/).

## Use

```sh
cd ~/projects
git clone https://github.com/usmanahmed99/nextia-learning-labs.git   # once
sh nextia-learning-labs/C14/setup.sh m03
```

The script makes `c14-lab/` in the current folder:

| Folder | What it is |
|---|---|
| `team-remote.git` | The shared remote, a bare repository. |
| `ticket-notes` | Your clone. In the lessons, you are Amira. |
| `sam-notes` | The clone of your teammate, Sam Okafor. Its Git identity is set to Sam. |

| Scenario | Used in | Start state |
|---|---|---|
| `m03` | Module 3 | Sam's pull request branch `add-ticket-104`, the branch `add-faq`, and one newer commit on `main`. |
| `m04` | Module 4 | Your `main` has an unpushed change to Ticket 102, and Sam pushed a different change to the same line. An earlier shared commit from Sam removed a contact. |
| `release` | Module 5, lesson 1 | `main` is ready for its first release. |
| `hotfix` | Module 5, lessons 2 and 3 | `release/1.0` and tag `v1.0.0` exist. `main` has unfinished work and a fix for a bug in 1.0. |
| `final` | Final assignment | The start state for the final assignment. |

To start a scenario again, add `--reset`. It deletes `c14-lab` first, but only if this script made it.

The script does not change your global Git settings. In the clones, it sets `pull.ff only` and `merge.conflictStyle zdiff3`. Every commit that the script makes has a fixed author and date, so its hash is the same as in the lessons.

Tested on 2026-10-05 with Git 2.54 on macOS (`sh` and `dash`) and Alpine Linux (BusyBox `sh`), with the same hashes on each. It uses only POSIX `sh`, so it is meant to run in Git Bash on Windows too, but that is not tested yet. Git 2.40 or later is required.
