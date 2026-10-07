# C14: Git and Team Development Essentials

Practice repositories for every module and the final assignment of [Git and Team Development Essentials](https://learning.nextia-ai.com/courses/git/).

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
| `m01-l03` | Module 1, lesson 3: Track a first change | `ticket-notes` is an empty repository on `main`, with no commits. There is no remote and no `sam-notes`. |
| `m02-l01` | Module 2, lesson 1: Branch basics | `ticket-notes` has the three commits from Module 1 on `main`: `763ec59`, `49397ba` and `d8ae027`, the same hashes as the lessons. No remote. |
| `m02-l02` | Module 2, lesson 2: Synchronize deliberately | The same, plus the branch `add-priorities` at `999a7c4`. You are on `main`. No remote: the lesson makes it. |
| `m02-l03` | Module 2, lesson 3: Keep the repository clean | `team-remote.git` has `main` and `add-priorities`. Sam's clone pushed `Add ticket 102`, and your `main` pulled it. Your branches track `origin`. |
| `m03` | Module 3 | Sam's pull request branch `add-ticket-104`, the branch `add-faq`, and one newer commit on `main`. |
| `m04` | Module 4 | Your `main` has an unpushed change to Ticket 102, and Sam pushed a different change to the same line. An earlier shared commit from Sam removed a contact. |
| `release` | Module 5, lesson 1 | `main` is ready for its first release. |
| `hotfix` | Module 5, lessons 2 and 3 | `release/1.0` and tag `v1.0.0` exist. `main` has unfinished work and a fix for a bug in 1.0. |
| `final` | Final assignment | The start state for the final assignment. |

In Modules 1 and 2, the lessons use `~/projects/ticket-notes`. If you use a scenario for these modules, use `~/projects/c14-lab` in place of `~/projects` in the lesson. The scenarios `m01-l03` to `m02-l02` make only `ticket-notes`, because the lessons make the remote and Sam's clone later. In `m02-l03`, the commit `Add ticket 102` has a different hash from the lesson, because the lesson shows the commit that the learner made as Sam.

To start a scenario again, add `--reset`. It deletes `c14-lab` first, but only if this script made it.

The script does not change your global Git settings. In the clones, it sets `pull.ff only` and `merge.conflictStyle zdiff3`. Every commit that the script makes has a fixed author and date, so its hash is the same as in the lessons. The one exception is the `m02-l03` commit above.

Tested on 2026-10-05 with Git 2.54 on macOS (`sh` and `dash`) and Alpine Linux (BusyBox `sh`), with the same hashes on each. It uses only POSIX `sh`, so it is meant to run in Git Bash on Windows too, but that is not tested yet. Git 2.40 or later is required. The four scenarios for Modules 1 and 2 were added on 2026-10-07 and tested on macOS only (`sh` and `dash`, Git 2.54).
